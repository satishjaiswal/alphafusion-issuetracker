#!/usr/bin/env python3
"""
Main Flask Application for Issue Tracker
"""

import os
import sys
import logging
import uuid
from pathlib import Path
from datetime import timedelta

# Configure centralized logging before importing Flask
try:
    from alphafusion.utils.logging_config import setup_logging, get_logger
    setup_logging(application="issuetracker", include_console=True)
    logger = get_logger(__name__)
except ImportError:
    # Fallback if alphafusion-core not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from flask import Flask, request, g
    from apps.web.extensions import csrf, talisman, limiter
    from apps.web.routes import register_routes
    from apps.web.auth import ensure_default_admin
    
    logger.info("All Flask dependencies imported successfully")
except ImportError as e:
    logger.error(f"Failed to import Flask dependencies: {e}", exc_info=True)
    print(f"FATAL ERROR: Failed to import required modules: {e}", file=sys.stderr)
    sys.stderr.flush()
    raise


def create_app(queue_consumer=None, cache_client=None, firebase_provider=None, redis_provider=None):
    """
    Create and configure Flask application.
    
    Args:
        queue_consumer: Optional QueueConsumer instance. If None, creates default from factory.
        cache_client: Optional CacheClient instance. If None, creates default from factory.
        firebase_provider: Optional FirebaseHelperProvider instance. If None, creates default.
        redis_provider: Optional RedisHelperProvider instance. If None, creates default.
    
    Returns:
        Configured Flask application
    """
    # Get application directory for templates and static files
    app_dir = Path(__file__).parent
    templates_dir = app_dir / 'templates'
    static_dir = app_dir / 'static'
    
    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir)
    )
    
    # 1. Configure App
    configure_app(app)
    
    # 2. Initialize Extensions
    init_extensions(app)
    
    # 3. Initialize Providers (Provider Pattern for DI)
    # Use provided providers or create defaults
    if firebase_provider is None or redis_provider is None:
        init_providers(app, cache_client=cache_client)
        # Get providers from app context if they were created
        if firebase_provider is None:
            firebase_provider = getattr(app, 'firebase_helper_provider', None)
        if redis_provider is None:
            redis_provider = getattr(app, 'redis_helper_provider', None)
    else:
        # Store provided providers in app context
        app.firebase_helper_provider = firebase_provider
        app.redis_helper_provider = redis_provider
        logger.info("Using provided Firebase and Redis providers")
    
    # 3.5. Ensure default admin user exists (after providers are initialized)
    # This must happen after providers are ready so FirebaseClient can initialize properly
    with app.app_context():
        try:
            ensure_default_admin()
        except Exception as e:
            logger.debug(f"Default admin creation skipped: {e}")
    
    # 4. Register Blueprints
    register_blueprints(app)
    
    # 5. Register Error Handlers
    register_error_handlers(app)
    
    # 6. Start Kafka consumer for issues (with injected dependencies)
    try:
        from apps.web.kafka_consumer import start_consumer
        start_consumer(
            queue_consumer=queue_consumer,
            cache_client=cache_client,
            firebase_provider=firebase_provider,
            redis_provider=redis_provider
        )
        logger.info("Kafka consumer started for issue tracking")
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumer: {e}. Issue tracking may not work.")
    
    return app


def configure_app(app):
    """Configure Flask application"""
    # Secret Key - MUST be loaded from SecureConfigLoader
    try:
        from alphafusion.config.config_helper import get_config_value
        
        secret_key = get_config_value("app/issuetracker/secret_key")
        
        if not secret_key:
            # Fallback for development
            secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-issuetracker")
            logger.warning("Using fallback secret key. Configure it in SecureConfigLoader at path 'app/issuetracker/secret_key'")
        
        if len(secret_key) < 32:
            logger.warning(f"SECRET_KEY should be at least 32 characters long. Current length: {len(secret_key)}")
        
        app.config['SECRET_KEY'] = secret_key
    except Exception as e:
        logger.warning(f"Could not load secret key from SecureConfigLoader: {e}. Using fallback.")
        app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-issuetracker")
    
    # Configure CSRF to exempt API routes using a custom check function
    # This will be used by CustomCSRFProtect
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    
    # Flask configuration
    try:
        from alphafusion.config.config_helper import get_config_value
        
        app.config['FLASK_DEBUG'] = get_config_value("app/issuetracker/flask_debug", default=False)
        app.config['FLASK_PORT'] = int(get_config_value("app/issuetracker/flask_port", default=6001))
    except Exception:
        app.config['FLASK_DEBUG'] = os.getenv("FLASK_DEBUG", "False").lower() == "true"
        app.config['FLASK_PORT'] = int(os.getenv("FLASK_PORT", "6001"))
    
    # Session configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def init_extensions(app):
    """Initialize Flask extensions"""
    # CSRF Protection
    csrf.init_app(app)
    
    # Security Headers (Talisman)
    talisman.init_app(
        app,
        force_https=False,  # Set to True in production with HTTPS
        strict_transport_security=False,  # Set to True in production
        content_security_policy=None  # Can be configured for production
    )
    
    # Rate Limiting
    limiter.init_app(app)
    
    # OAuth (Google)
    from apps.web.oauth import init_oauth
    init_oauth(app)


def init_providers(app, cache_client=None):
    """
    Initialize providers and store in Flask app context.
    
    Args:
        app: Flask application instance
        cache_client: Optional CacheClient instance for Redis provider
    """
    try:
        from apps.web.utils.provider_factory import IssueTrackerProviderFactory
        
        # Create providers using factory
        firebase_provider, redis_provider = IssueTrackerProviderFactory.create_providers(
            cache_client=cache_client
        )
        
        # Store providers in app context
        app.firebase_helper_provider = firebase_provider
        app.redis_helper_provider = redis_provider
        
        logger.info("Issue Tracker providers initialized successfully")
        
        if not firebase_provider.is_available():
            logger.warning("Firebase provider not available - ensure Firebase credentials are configured")
        
        if not redis_provider.is_available():
            logger.warning("Redis provider not available - recent issues cache will not work")
    
    except Exception as e:
        logger.error(f"Failed to initialize providers: {e}", exc_info=True)
        # Create fallback providers (will fail gracefully)
        from apps.web.utils.provider_factory import IssueTrackerProviderFactory
        app.firebase_helper_provider = IssueTrackerProviderFactory.create_firebase_helper_provider()
        app.redis_helper_provider = IssueTrackerProviderFactory.create_redis_helper_provider(
            cache_client=cache_client
        )


def register_blueprints(app):
    """Register Flask blueprints"""
    # Register web routes
    register_routes(app)
    
    # Register API blueprint (for service-to-service calls)
    from apps.web.api import api_bp
    logger.info(f"Registering API blueprint: {api_bp.name} with URL prefix: {api_bp.url_prefix}")
    app.register_blueprint(api_bp)
    logger.info(f"API blueprint registered successfully. Blueprints: {list(app.blueprints.keys())}")
    
    # Exempt API blueprint from CSRF protection (for service-to-service calls)
    # This must be done after csrf.init_app() is called (which happens in init_extensions)
    from apps.web.extensions import csrf
    csrf.exempt(api_bp)
    logger.info("API blueprint exempted from CSRF protection")


def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return {'error': 'Not found'}, 404
        from flask import render_template
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        error_id = str(uuid.uuid4())
        app.logger.exception(
            "Internal server error",
            extra={'error_id': error_id, 'endpoint': request.endpoint, 'method': request.method, 'path': request.path}
        )
        if request.is_json or request.path.startswith("/api/"):
            return {'error': 'An internal error occurred', 'error_id': error_id}, 500
        from flask import render_template
        return render_template('500.html', error_id=error_id), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        error_id = str(uuid.uuid4())
        app.logger.exception(
            "Unhandled exception",
            extra={'error_id': error_id, 'endpoint': request.endpoint, 'method': request.method, 'path': request.path}
        )
        if request.is_json or request.path.startswith("/api/"):
            return {'error': 'An internal error occurred', 'error_id': error_id}, 500
        from flask import render_template
        return render_template('500.html', error_id=error_id), 500


if __name__ == "__main__":
    app = create_app()
    port = app.config.get('FLASK_PORT', 6001)
    debug = app.config.get('FLASK_DEBUG', False)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    finally:
        # Stop Kafka consumer on shutdown
        try:
            from apps.web.kafka_consumer import stop_consumer
            stop_consumer()
        except Exception as e:
            logger.warning(f"Error stopping Kafka consumer: {e}")

