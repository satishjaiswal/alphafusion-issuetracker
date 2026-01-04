#!/usr/bin/env python3
"""
Google OAuth authentication for Issue Tracker
Handles OAuth flow for @quantory.app users

This module uses the OAuthProvider from alphafusion-core for OAuth functionality.
"""

import logging
from typing import Optional
from flask import session, url_for, redirect, request

from alphafusion.auth.oauth_factory import get_default_google_oauth_provider
from alphafusion.auth.oauth_provider import OAuthProvider

logger = logging.getLogger(__name__)

# OAuth provider instance (initialized in init_oauth)
_oauth_provider: Optional[OAuthProvider] = None


def init_oauth(app):
    """Initialize OAuth with Flask app"""
    global _oauth_provider
    
    provider = get_default_google_oauth_provider(
        credential_path="app/issuetracker/google-issuetracker.json",
        allowed_email_domains=["@quantory.app"]
    )
    
    if provider:
        provider.initialize(app)
        _oauth_provider = provider
        logger.info("Google OAuth initialized using OAuthProvider from alphafusion-core")
    else:
        logger.warning("Failed to create Google OAuth provider. @quantory.app users will not be able to login.")


def is_quantory_email(email: str) -> bool:
    """Check if email is from quantory.app domain"""
    if not _oauth_provider:
        return email and email.endswith('@quantory.app')
    return _oauth_provider.validate_email_domain(email, ["@quantory.app"])


def get_google_oauth():
    """Get Google OAuth client from Flask app context (for backward compatibility)"""
    from flask import current_app
    return getattr(current_app, 'google_oauth', None)


def start_google_oauth():
    """Start Google OAuth flow - redirects to Google"""
    if not _oauth_provider:
        logger.error("Google OAuth not initialized")
        return None
    
    # Store redirect URL in session
    redirect_url = request.args.get('next') or url_for('dashboard')
    session['oauth_redirect'] = redirect_url
    
    # Start OAuth flow via provider
    return _oauth_provider.start_oauth_flow(redirect_url)


def handle_google_callback() -> Optional[str]:
    """
    Handle Google OAuth callback
    
    Returns:
        User ID (email) if successful, None otherwise
    """
    if not _oauth_provider:
        logger.error("Google OAuth not initialized")
        return None
    
    try:
        # Handle callback via provider
        user_info = _oauth_provider.handle_callback()
        
        if not user_info:
            return None
        
        email = user_info.get('email')
        if not email:
            return None
        
        # User info is already stored in session by the provider
        return email
    
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback: {e}", exc_info=True)
        return None

