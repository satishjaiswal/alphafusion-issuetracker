#!/usr/bin/env python3
"""
Provider Factory for Issue Tracker

Factory for creating provider instances following the Factory Pattern.
"""

import logging
from typing import Optional

from apps.web.utils.providers import (
    FirebaseHelperProvider,
    RedisHelperProvider
)
from apps.web.utils.provider_implementations import (
    FirebaseHelperProviderImpl,
    RedisHelperProviderImpl
)
from apps.web.utils.firebase_helper import FirebaseHelper
from apps.web.utils.redis_helper import RedisHelper
from alphafusion.storage.cache_interface import CacheClient

logger = logging.getLogger(__name__)


class IssueTrackerProviderFactory:
    """
    Factory for creating Issue Tracker provider instances.
    
    Design Patterns:
    - Factory Pattern: Creates provider instances
    - Singleton Pattern: Providers use singleton pattern internally
    - Dependency Injection: Accepts dependencies for providers
    """
    
    @staticmethod
    def create_firebase_helper_provider(
        firebase_helper: Optional[FirebaseHelper] = None
    ) -> FirebaseHelperProvider:
        """
        Create Firebase helper provider instance.
        
        Args:
            firebase_helper: Optional FirebaseHelper instance.
                          If None, creates new instance.
        
        Returns:
            FirebaseHelperProvider instance
        """
        return FirebaseHelperProviderImpl(firebase_helper=firebase_helper)
    
    @staticmethod
    def create_redis_helper_provider(
        redis_helper: Optional[RedisHelper] = None,
        cache_client: Optional[CacheClient] = None
    ) -> RedisHelperProvider:
        """
        Create Redis helper provider instance.
        
        Args:
            redis_helper: Optional RedisHelper instance.
                        If None, creates new instance.
            cache_client: Optional CacheClient instance.
                         Passed to RedisHelper if redis_helper is None.
        
        Returns:
            RedisHelperProvider instance
        """
        if redis_helper is None:
            # Create RedisHelper with optional cache_client
            redis_helper = RedisHelper(cache_client=cache_client)
        
        return RedisHelperProviderImpl(redis_helper=redis_helper)
    
    @staticmethod
    def create_providers(
        firebase_helper: Optional[FirebaseHelper] = None,
        redis_helper: Optional[RedisHelper] = None,
        cache_client: Optional[CacheClient] = None
    ) -> tuple[FirebaseHelperProvider, RedisHelperProvider]:
        """
        Create both providers at once.
        
        Args:
            firebase_helper: Optional FirebaseHelper instance
            redis_helper: Optional RedisHelper instance
            cache_client: Optional CacheClient instance
        
        Returns:
            Tuple of (FirebaseHelperProvider, RedisHelperProvider)
        """
        firebase_provider = IssueTrackerProviderFactory.create_firebase_helper_provider(
            firebase_helper=firebase_helper
        )
        redis_provider = IssueTrackerProviderFactory.create_redis_helper_provider(
            redis_helper=redis_helper,
            cache_client=cache_client
        )
        
        return firebase_provider, redis_provider

