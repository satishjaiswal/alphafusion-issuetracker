#!/usr/bin/env python3
"""
Unit tests for authentication and authorization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session
from apps.web.auth import (
    get_current_user_id, get_current_user, require_auth, require_role,
    login_user, logout_user, ensure_default_admin
)
from apps.web.models import User, UserRole


class TestAuthHelpers:
    """Tests for authentication helper functions."""
    
    def test_get_current_user_id_with_session(self):
        """Test getting user ID from session."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        with app.test_request_context():
            session["user_id"] = "user123"
            user_id = get_current_user_id()
            assert user_id == "user123"
    
    def test_get_current_user_id_without_session(self):
        """Test getting user ID when not logged in."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        with app.test_request_context():
            user_id = get_current_user_id()
            assert user_id is None
    
    @patch('apps.web.auth.firebase_helper')
    def test_get_current_user(self, mock_firebase_helper):
        """Test getting current user from Firebase."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        mock_user = User(
            uid="user123",
            email="user@example.com",
            role=UserRole.DEVELOPER
        )
        mock_firebase_helper.get_user.return_value = mock_user
        
        with app.test_request_context():
            session["user_id"] = "user123"
            user = get_current_user()
            
            assert user is not None
            assert user.uid == "user123"
            mock_firebase_helper.get_user.assert_called_once_with("user123")
    
    @patch('apps.web.auth.firebase_helper')
    def test_get_current_user_not_logged_in(self, mock_firebase_helper):
        """Test getting current user when not logged in."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        with app.test_request_context():
            user = get_current_user()
            
            assert user is None
            mock_firebase_helper.get_user.assert_not_called()
    
    def test_login_user(self):
        """Test logging in a user."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        with app.test_request_context():
            login_user("user123")
            
            assert session.get("user_id") == "user123"
    
    def test_logout_user(self):
        """Test logging out a user."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        with app.test_request_context():
            session["user_id"] = "user123"
            logout_user()
            
            assert session.get("user_id") is None


class TestRequireAuth:
    """Tests for require_auth decorator."""
    
    def test_require_auth_authenticated(self):
        """Test require_auth with authenticated user."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        @app.route("/test")
        @require_auth
        def test_route():
            return "success"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user123"
            
            response = client.get("/test")
            assert response.status_code == 200
            assert response.data == b"success"
    
    def test_require_auth_not_authenticated_web(self):
        """Test require_auth redirects to login for web requests."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        @app.route("/login")
        def login():
            return "login"
        
        @app.route("/test")
        @require_auth
        def test_route():
            return "success"
        
        with app.test_client() as client:
            response = client.get("/test", follow_redirects=False)
            assert response.status_code == 302  # Redirect to login
    
    def test_require_auth_not_authenticated_api(self):
        """Test require_auth returns 401 for API requests."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        @app.route("/api/test")
        @require_auth
        def test_route():
            return "success"
        
        with app.test_client() as client:
            response = client.get(
                "/api/test",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 401
            assert b"Authentication required" in response.data


class TestRequireRole:
    """Tests for require_role decorator."""
    
    @patch('apps.web.auth.get_current_user')
    def test_require_role_success(self, mock_get_user):
        """Test require_role with correct role."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        mock_user = User(
            uid="user123",
            email="user@example.com",
            role=UserRole.DEVELOPER
        )
        mock_get_user.return_value = mock_user
        
        @app.route("/test")
        @require_role(UserRole.DEVELOPER, UserRole.ADMIN)
        def test_route():
            return "success"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user123"
            
            response = client.get("/test")
            assert response.status_code == 200
    
    @patch('apps.web.auth.get_current_user')
    def test_require_role_insufficient_permissions(self, mock_get_user):
        """Test require_role with insufficient permissions."""
        app = Flask(__name__)
        app.secret_key = "test-secret"
        
        mock_user = User(
            uid="user123",
            email="user@example.com",
            role=UserRole.VIEWER
        )
        mock_get_user.return_value = mock_user
        
        @app.route("/api/test")
        @require_role(UserRole.DEVELOPER, UserRole.ADMIN)
        def test_route():
            return "success"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user123"
            
            response = client.get(
                "/api/test",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 403
            assert b"Insufficient permissions" in response.data

