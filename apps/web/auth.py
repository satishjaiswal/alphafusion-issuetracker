#!/usr/bin/env python3
"""
Authentication and authorization for Issue Tracker
"""

import logging
from functools import wraps
from typing import Optional
from flask import session, redirect, url_for, request, jsonify, current_app
from apps.web.models import UserRole
from apps.web.oauth import is_quantory_email

logger = logging.getLogger(__name__)


def _get_firebase_provider():
    """Get Firebase provider from Flask app context"""
    return getattr(current_app, 'firebase_helper_provider', None)


def get_current_user_id():
    """Get current user ID from session"""
    return session.get("user_id")


def get_current_user():
    """Get current user from Firebase"""
    user_id = get_current_user_id()
    if not user_id:
        return None
    
    firebase_provider = _get_firebase_provider()
    if not firebase_provider:
        return None
    
    return firebase_provider.get_user(user_id)


def require_auth(f):
    """Decorator to require authentication - only @quantory.app users allowed"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        
        # Verify user is from @quantory.app domain
        if not is_quantory_email(user_id):
            logger.warning(f"Access denied for non-quantory.app user: {user_id}")
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Access denied. Only @quantory.app users are allowed."}), 403
            flash("Access denied. Only @quantory.app users are allowed.", "error")
            logout_user()
            return redirect(url_for("login"))
        
        return f(*args, **kwargs)
    return decorated_function


def require_role(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("login"))
            
            user_role = UserRole(user.role.value if hasattr(user.role, 'value') else user.role)
            if user_role not in roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Insufficient permissions"}), 403
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_user(user_id: str, display_name: Optional[str] = None):
    """Log in a user"""
    session["user_id"] = user_id
    if display_name:
        session["user_display_name"] = display_name
    # Update last login
    firebase_provider = _get_firebase_provider()
    if firebase_provider:
        firebase_provider.update_user(user_id, last_login=None)  # Will be set to now in update_user


def logout_user():
    """Log out current user"""
    session.pop("user_id", None)


def ensure_default_admin():
    """Ensure default admin user exists"""
    try:
        # Try to get provider from app context if available
        # If not available (e.g., during app initialization), create temporary instance
        try:
            firebase_provider = _get_firebase_provider()
        except RuntimeError:
            # App context not available, create temporary provider
            from apps.web.utils.provider_factory import IssueTrackerProviderFactory
            firebase_provider = IssueTrackerProviderFactory.create_firebase_helper_provider()
        
        if not firebase_provider or not firebase_provider.is_available():
            logger.warning("Firebase not available, cannot create default admin")
            return
        
        # Check if any admin exists
        users = firebase_provider.list_users()
        has_admin = any(user.role == UserRole.ADMIN for user in users)
        
        if not has_admin:
            # Create default admin
            default_admin = firebase_provider.create_user(
                uid="admin",
                email="admin@alphafusion.local",
                display_name="System Administrator",
                role=UserRole.ADMIN
            )
            if default_admin:
                logger.info("Created default admin user (uid: admin, email: admin@alphafusion.local)")
            else:
                logger.error("Failed to create default admin user")
    except Exception as e:
        logger.debug(f"Default admin creation skipped: {e}")

