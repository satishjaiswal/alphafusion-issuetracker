#!/usr/bin/env python3
"""
Unit tests for API endpoints.

Note: These tests mock Flask extensions to avoid dependency issues.
For full integration tests, see tests/integration/.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from datetime import datetime

# Mock Flask extensions before any imports
# Comment out sys.modules mocking to see actual issues
# sys.modules['flask_talisman'] = MagicMock()
# sys.modules['flask_limiter'] = MagicMock()
# sys.modules['flask_wtf.csrf'] = MagicMock()

from apps.web.models import Issue, IssueStatus, IssuePriority, IssueType, Comment


@pytest.fixture
def app():
    """Create Flask app for testing."""
    # Create a minimal Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Mock limiter decorator
    mock_limiter = Mock()
    mock_limiter.limit.return_value = lambda f: f
    
    # Register API routes manually (avoiding blueprint import issues)
    with patch('apps.web.extensions.limiter', mock_limiter):
        with patch('apps.web.api.firebase_helper'):
            from apps.web.api import api_bp
            app.register_blueprint(api_bp)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_health_check_available(self, mock_firebase_helper, client):
        """Test health check when Firebase is available."""
        mock_firebase_helper.is_available.return_value = True
        
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['firebase_available'] is True
    
    @patch('apps.web.api.firebase_helper')
    def test_health_check_unavailable(self, mock_firebase_helper, client):
        """Test health check when Firebase is unavailable."""
        mock_firebase_helper.is_available.return_value = False
        
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['firebase_available'] is False


class TestCreateIssue:
    """Tests for create issue endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_create_issue_success(self, mock_firebase_helper, client):
        """Test successful issue creation."""
        # Mock Firebase helper
        mock_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.OPEN,
            priority=IssuePriority.HIGH,
            type=IssueType.BUG,
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.create_issue.return_value = "test-123"
        mock_firebase_helper.get_issue.return_value = mock_issue
        mock_firebase_helper.get_user.return_value = None  # User doesn't exist
        mock_firebase_helper.create_user.return_value = Mock()  # Auto-create user
        
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "type": "bug",
            "priority": "high",
            "reporter_id": "user1"
        }
        
        response = client.post('/api/v1/issues', json=data)
        
        assert response.status_code == 201
        result = response.get_json()
        assert result['id'] == "test-123"
        assert result['title'] == "Test Issue"
        assert result['status'] == "open"
        assert result['priority'] == "high"
        assert result['type'] == "bug"
    
    def test_create_issue_invalid_data(self, client):
        """Test issue creation with invalid data."""
        data = {
            "description": "Test description"
            # Missing required fields
        }
        
        response = client.post('/api/v1/issues', json=data)
        
        assert response.status_code == 400
        assert 'error' in response.get_json()
    
    @patch('apps.web.api.firebase_helper')
    def test_create_issue_firebase_error(self, mock_firebase_helper, client):
        """Test issue creation when Firebase fails."""
        mock_firebase_helper.create_issue.return_value = None
        mock_firebase_helper.get_user.return_value = None
        mock_firebase_helper.create_user.return_value = Mock()
        
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1"
        }
        
        response = client.post('/api/v1/issues', json=data)
        
        assert response.status_code == 500
        assert 'error' in response.get_json()


class TestGetIssue:
    """Tests for get issue endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_get_issue_success(self, mock_firebase_helper, client):
        """Test successful issue retrieval."""
        mock_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.OPEN,
            priority=IssuePriority.HIGH,
            type=IssueType.BUG,
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.get_issue.return_value = mock_issue
        
        response = client.get('/api/v1/issues/test-123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == "test-123"
        assert data['title'] == "Test Issue"
    
    @patch('apps.web.api.firebase_helper')
    def test_get_issue_not_found(self, mock_firebase_helper, client):
        """Test getting non-existent issue."""
        mock_firebase_helper.get_issue.return_value = None
        
        response = client.get('/api/v1/issues/nonexistent')
        
        assert response.status_code == 404
        assert 'error' in response.get_json()


class TestUpdateIssue:
    """Tests for update issue endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_update_issue_success(self, mock_firebase_helper, client):
        """Test successful issue update."""
        mock_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.OPEN,
            priority=IssuePriority.HIGH,
            type=IssueType.BUG,
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.get_issue.return_value = mock_issue
        mock_firebase_helper.update_issue.return_value = True
        
        data = {
            "status": "in-progress",
            "priority": "critical"
        }
        
        response = client.patch(
            '/api/v1/issues/test-123',
            json=data,
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        mock_firebase_helper.update_issue.assert_called_once()
    
    @patch('apps.web.api.firebase_helper')
    def test_update_issue_not_found(self, mock_firebase_helper, client):
        """Test updating non-existent issue."""
        mock_firebase_helper.get_issue.return_value = None
        
        data = {"status": "in-progress"}
        
        response = client.patch(
            '/api/v1/issues/nonexistent',
            json=data,
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 404


class TestAddComment:
    """Tests for add comment endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_add_comment_success(self, mock_firebase_helper, client):
        """Test successful comment addition."""
        mock_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.get_issue.return_value = mock_issue
        mock_firebase_helper.create_comment.return_value = "comment-123"
        mock_firebase_helper.get_user.return_value = None
        mock_firebase_helper.create_user.return_value = Mock()
        
        data = {
            "content": "Test comment",
            "author_id": "user1"
        }
        
        response = client.post('/api/v1/issues/test-123/comments', json=data)
        
        assert response.status_code == 201
        result = response.get_json()
        assert result['id'] == "comment-123"
        assert result['content'] == "Test comment"
    
    @patch('apps.web.api.firebase_helper')
    def test_add_comment_issue_not_found(self, mock_firebase_helper, client):
        """Test adding comment to non-existent issue."""
        mock_firebase_helper.get_issue.return_value = None
        
        data = {
            "content": "Test comment",
            "author_id": "user1"
        }
        
        response = client.post('/api/v1/issues/nonexistent/comments', json=data)
        
        assert response.status_code == 404


class TestGetComments:
    """Tests for get comments endpoint."""
    
    @patch('apps.web.api.firebase_helper')
    def test_get_comments_success(self, mock_firebase_helper, client):
        """Test successful comment retrieval."""
        mock_comments = [
            Comment(
                id="comment-1",
                issue_id="test-123",
                author_id="user1",
                content="Comment 1",
                created_at=datetime.now()
            ),
            Comment(
                id="comment-2",
                issue_id="test-123",
                author_id="user2",
                content="Comment 2",
                created_at=datetime.now()
            )
        ]
        mock_firebase_helper.get_comments.return_value = mock_comments
        
        response = client.get('/api/v1/issues/test-123/comments')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['comments']) == 2
        assert data['comments'][0]['id'] == "comment-1"
        assert data['comments'][1]['id'] == "comment-2"

