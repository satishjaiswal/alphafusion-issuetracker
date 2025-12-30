#!/usr/bin/env python3
"""
Authentication and authorization for Issue Tracker
"""

import logging
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from apps.web.models import UserRole
from apps.web.utils.firebase_helper import FirebaseHelper

logger = logging.getLogger(__name__)

# Initialize Firebase helper
firebase_helper = FirebaseHelper()


def get_current_user_id():
    """Get current user ID from session"""
    return session.get("user_id")


def get_current_user():
    """Get current user from Firebase"""
    user_id = get_current_user_id()
    if not user_id:
        return None
    return firebase_helper.get_user(user_id)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user_id():
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("routes.login"))
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
                return redirect(url_for("routes.login"))
            
            user_role = UserRole(user.role.value if hasattr(user.role, 'value') else user.role)
            if user_role not in roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Insufficient permissions"}), 403
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_user(user_id: str):
    """Log in a user"""
    session["user_id"] = user_id
    # Update last login
    firebase_helper.update_user(user_id, last_login=None)  # Will be set to now in update_user


def logout_user():
    """Log out current user"""
    session.pop("user_id", None)


def ensure_default_admin():
    """Ensure default admin user exists"""
    if not firebase_helper.is_available():
        logger.warning("Firebase not available, cannot create default admin")
        return
    
    # Check if any admin exists
    users = firebase_helper.list_users()
    has_admin = any(user.role == UserRole.ADMIN for user in users)
    
    if not has_admin:
        # Create default admin
        default_admin = firebase_helper.create_user(
            uid="admin",
            email="admin@alphafusion.local",
            display_name="System Administrator",
            role=UserRole.ADMIN
        )
        if default_admin:
            logger.info("Created default admin user (uid: admin, email: admin@alphafusion.local)")
        else:
            logger.error("Failed to create default admin user")

