#!/usr/bin/env python3
"""
Provider Factory for Issue Tracker

Factory for creating provider instances following the Factory Pattern.
"""

import logging
from typing import Optional

from apps.web.utils.providers import (
    FirebaseHelperProvider
)
from apps.web.utils.provider_implementations import (
    FirebaseHelperProviderImpl
)
from apps.web.utils.firebase_helper import FirebaseHelper

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

