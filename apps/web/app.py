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
    from apps.web.api import api_bp
    from apps.web.auth import ensure_default_admin
    
    logger.info("All Flask dependencies imported successfully")
except ImportError as e:
    logger.error(f"Failed to import Flask dependencies: {e}", exc_info=True)
    print(f"FATAL ERROR: Failed to import required modules: {e}", file=sys.stderr)
    sys.stderr.flush()
    raise


def create_app():
    """Create and configure Flask application"""
    # Ensure default admin user exists
    try:
        ensure_default_admin()
    except Exception as e:
        logger.debug(f"Default admin creation skipped: {e}")
    
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
    
    # 3. Register Blueprints
    register_blueprints(app)
    
    # 4. Register Error Handlers
    register_error_handlers(app)
    
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
    
    # Exempt API routes from CSRF
    _exempt_api_routes(app)


def _exempt_api_routes(app):
    """Exempt API routes from CSRF protection"""
    try:
        # Exempt all API routes
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/api/'):
                endpoint = rule.endpoint
                if endpoint in app.view_functions:
                    csrf.exempt(app.view_functions[endpoint])
        
        logger.info("API routes exempted from CSRF")
    except Exception as e:
        logger.error(f"Error exempting API routes from CSRF: {e}", exc_info=True)


def register_blueprints(app):
    """Register Flask blueprints"""
    # Register API blueprint
    app.register_blueprint(api_bp)
    
    # Register web routes
    register_routes(app)


def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json or request.path.startswith("/api/"):
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
    app.run(host='0.0.0.0', port=port, debug=debug)

