#!/usr/bin/env python3
"""
Google OAuth authentication for Issue Tracker
Handles OAuth flow for @quantory.app users
"""

import logging
import os
from typing import Optional
from flask import session, url_for, redirect, request, current_app
from authlib.integrations.flask_client import OAuth
from apps.web.models import UserRole

logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with Flask app"""
    oauth.init_app(app)
    
    # Get Google OAuth credentials from SecureConfigLoader or environment
    client_id = None
    client_secret = None
    
    # Try to load from google-issuetracker.json file first
    try:
        from alphafusion.config.secure_config_loader import get_secure_config_loader
        from pathlib import Path
        import json
        
        loader = get_secure_config_loader()
        
        if loader and loader.credentials_dir:
            # Try to load from .credentials/app/issuetracker/google-issuetracker.json
            google_creds_file = loader.credentials_dir / "app" / "issuetracker" / "google-issuetracker.json"
            
            if google_creds_file.exists():
                try:
                    with open(google_creds_file, 'r', encoding='utf-8') as f:
                        google_creds = json.load(f)
                        # Support both uppercase and lowercase keys
                        client_id = google_creds.get('GOOGLE_CLIENT_ID') or google_creds.get('google_client_id')
                        client_secret = google_creds.get('GOOGLE_CLIENT_SECRET') or google_creds.get('google_client_secret')
                        if client_id and client_secret:
                            logger.info("Loaded Google OAuth credentials from google-issuetracker.json")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load google-issuetracker.json: {e}")
        
        # If not found in google-issuetracker.json, try individual keys via SecureConfigLoader
        if not client_id or not client_secret:
            try:
                from alphafusion.config.config_helper import get_config_value
                if not client_id:
                    client_id = get_config_value("app/issuetracker/google_client_id")
                if not client_secret:
                    client_secret = get_config_value("app/issuetracker/google_client_secret")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Could not load credentials via SecureConfigLoader: {e}")
    
    # Fallback to environment variables
    if not client_id:
        client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    if not client_secret:
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    # Register Google OAuth
    google = oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    app.google_oauth = google
    
    if client_id and client_secret:
        logger.info("Google OAuth initialized")
    else:
        logger.warning("Google OAuth credentials not configured. @quantory.app users will not be able to login.")


def is_quantory_email(email: str) -> bool:
    """Check if email is from quantory.app domain"""
    return email and email.endswith('@quantory.app')


def get_google_oauth():
    """Get Google OAuth client from Flask app context"""
    return getattr(current_app, 'google_oauth', None)


def start_google_oauth():
    """Start Google OAuth flow - redirects to Google"""
    google = get_google_oauth()
    if not google:
        logger.error("Google OAuth not initialized")
        return None
    
    # Store redirect URL in session
    redirect_url = request.args.get('next') or url_for('dashboard')
    session['oauth_redirect'] = redirect_url
    
    # Generate redirect URI
    redirect_uri = url_for('oauth_callback', _external=True)
    
    # Redirect to Google
    return google.authorize_redirect(redirect_uri)


def handle_google_callback() -> Optional[str]:
    """
    Handle Google OAuth callback
    
    Returns:
        User ID (email) if successful, None otherwise
    """
    google = get_google_oauth()
    if not google:
        logger.error("Google OAuth not initialized")
        return None
    
    try:
        # Get token from Google
        token = google.authorize_access_token()
        
        # Fetch user info from Google using the full URL
        resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch user info: {resp.status_code}")
            return None
        
        user_info = resp.json()
        
        email = user_info.get('email')
        if not email:
            logger.error("No email in Google user info")
            return None
        
        # Verify it's a quantory.app email
        if not is_quantory_email(email):
            logger.warning(f"Email {email} is not from quantory.app domain")
            return None
        
        # Store user info in session
        session['oauth_email'] = email
        session['oauth_name'] = user_info.get('name', email.split('@')[0])
        session['oauth_picture'] = user_info.get('picture')
        
        return email
    
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback: {e}", exc_info=True)
        return None

