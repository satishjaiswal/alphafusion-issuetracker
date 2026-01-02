#!/usr/bin/env python3
"""
Entry point for running the Flask app as a module

Creates and injects dependencies (Queue, Cache, Cloud providers) following
the dependency injection pattern used by other services.
"""

import logging
import sys
from pathlib import Path

# Set up logging before importing app
try:
    from alphafusion.utils.logging_config import setup_logging, get_logger
    setup_logging(application="issuetracker", include_console=True)
    logger = get_logger(__name__)
except ImportError:
    # Fallback if alphafusion-core not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Try to import degraded mode support (optional)
try:
    from alphafusion.config.degraded_mode import DegradedModeManager, ServiceState
    from alphafusion.config.dependency_checker import DependencyChecker
    DEGRADED_MODE_AVAILABLE = True
except ImportError:
    DEGRADED_MODE_AVAILABLE = False
    logger.warning("Degraded mode support not available - service will fail if dependencies unavailable")

from apps.web.app import create_app


def create_dependencies():
    """
    Create Queue, Cache, and Cloud provider dependencies.
    
    Returns:
        tuple: (queue_consumer, cache_client, firebase_provider, redis_provider)
    """
    queue_consumer = None
    cache_client = None
    firebase_provider = None
    redis_provider = None
    
    # Create Queue Consumer (for Kafka)
    # Note: Kafka consumers are lazy - they only connect when subscribe() is called
    try:
        from alphafusion.storage.queue_factory import create_queue_consumer
        queue_consumer = create_queue_consumer()
        if queue_consumer:
            logger.info("Queue consumer (Kafka) created successfully (will connect on subscribe)")
        else:
            logger.warning("Queue consumer creation returned None - Kafka may be unavailable")
    except Exception as e:
        logger.warning(f"Failed to create queue consumer: {e}. Kafka consumer will not be available.")
    
    # Create Cache Client (for Redis)
    try:
        from alphafusion.storage.cache_factory import get_default_cache_client
        cache_client = get_default_cache_client(use_pool=True)
        if cache_client and cache_client.is_connected():
            logger.info("Cache client (Redis) created and connected")
        else:
            logger.warning("Cache client created but not connected - Redis may be unavailable")
    except Exception as e:
        logger.warning(f"Failed to create cache client: {e}. Redis cache will not be available.")
    
    # Create Cloud providers (Firebase and Redis helper providers)
    try:
        from apps.web.utils.provider_factory import IssueTrackerProviderFactory
        firebase_provider, redis_provider = IssueTrackerProviderFactory.create_providers(
            cache_client=cache_client
        )
        if firebase_provider and firebase_provider.is_available():
            logger.info("Firebase provider created and available")
        else:
            logger.warning("Firebase provider created but not available - check credentials")
        
        if redis_provider and redis_provider.is_available():
            logger.info("Redis provider created and available")
        else:
            logger.warning("Redis provider created but not available")
    except Exception as e:
        logger.warning(f"Failed to create cloud providers: {e}")
    
    return queue_consumer, cache_client, firebase_provider, redis_provider


def main():
    """Main entry point - creates dependencies and starts Flask app"""
    degraded_mode_manager = None
    
    # Initialize degraded mode manager if available
    if DEGRADED_MODE_AVAILABLE:
        required_dependencies = ["redis", "cassandra"]  # Kafka is optional for issuetracker
        dependency_checker = DependencyChecker()
        degraded_mode_manager = DegradedModeManager(
            required_dependencies=required_dependencies,
            dependency_checker=dependency_checker,
            check_interval_seconds=30.0
        )
        
        # Check dependencies (non-blocking - service can start in degraded mode)
        logger.info("Checking dependencies...")
        degraded_mode_manager.update_state_from_dependencies()
        
        if degraded_mode_manager.is_degraded():
            logger.warning("⚠️  Some dependencies unavailable - starting in degraded mode")
        else:
            logger.info("✓ All dependencies healthy")
        
        # Start background monitoring
        degraded_mode_manager.start_monitoring()
    
    # Create dependencies
    queue_consumer, cache_client, firebase_provider, redis_provider = create_dependencies()
    
    # Create Flask app with injected dependencies
    app = create_app(
        queue_consumer=queue_consumer,
        cache_client=cache_client,
        firebase_provider=firebase_provider,
        redis_provider=redis_provider
    )
    
    # Get port and debug settings
    port = app.config.get('FLASK_PORT', 6001)
    debug = app.config.get('FLASK_DEBUG', False)
    
    if degraded_mode_manager and degraded_mode_manager.is_degraded():
        logger.warning(f"Starting Issue Tracker service in degraded mode on port {port} (debug={debug})")
    else:
        logger.info(f"Starting Issue Tracker service on port {port} (debug={debug})")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    finally:
        if degraded_mode_manager:
            degraded_mode_manager.stop_monitoring()


if __name__ == "__main__":
    main()

