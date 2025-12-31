#!/usr/bin/env python3
"""
Integration tests for API flow.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from datetime import datetime

# Mock Flask extensions before any imports
sys.modules['flask_talisman'] = MagicMock()
sys.modules['flask_limiter'] = MagicMock()
sys.modules['flask_wtf.csrf'] = MagicMock()

from apps.web.models import Issue, Comment, IssueStatus, IssuePriority, IssueType


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Mock limiter decorator
    mock_limiter = Mock()
    mock_limiter.limit.return_value = lambda f: f
    
    # Register API blueprint with mocked dependencies
    with patch('apps.web.api.limiter', mock_limiter):
        from apps.web.api import api_bp
        app.register_blueprint(api_bp)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestIssueLifecycle:
    """Integration tests for complete issue lifecycle."""
    
    @patch('apps.web.api.firebase_helper')
    def test_create_get_update_issue_flow(self, mock_firebase_helper, client):
        """Test complete issue lifecycle: create -> get -> update."""
        # Step 1: Create issue
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
        mock_firebase_helper.get_user.return_value = None
        mock_firebase_helper.create_user.return_value = Mock()
        
        create_data = {
            "title": "Test Issue",
            "description": "Test description",
            "type": "bug",
            "priority": "high",
            "reporter_id": "user1"
        }
        
        create_response = client.post('/api/v1/issues', json=create_data)
        assert create_response.status_code == 201
        create_result = create_response.get_json()
        issue_id = create_result['id']
        
        # Step 2: Get issue
        get_response = client.get(f'/api/v1/issues/{issue_id}')
        assert get_response.status_code == 200
        get_result = get_response.get_json()
        assert get_result['title'] == "Test Issue"
        assert get_result['status'] == "open"
        
        # Step 3: Update issue
        updated_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.IN_PROGRESS,
            priority=IssuePriority.CRITICAL,
            type=IssueType.BUG,
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.get_issue.return_value = updated_issue
        mock_firebase_helper.update_issue.return_value = True
        
        update_data = {
            "status": "in-progress",
            "priority": "critical"
        }
        
        update_response = client.patch(
            f'/api/v1/issues/{issue_id}',
            json=update_data,
            headers={"X-User-Id": "user1"}
        )
        assert update_response.status_code == 200
    
    @patch('apps.web.api.firebase_helper')
    def test_create_issue_add_comments_flow(self, mock_firebase_helper, client):
        """Test issue creation and comment addition flow."""
        # Step 1: Create issue
        mock_issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            reporter_id="user1",
            created_at=datetime.now()
        )
        mock_firebase_helper.create_issue.return_value = "test-123"
        mock_firebase_helper.get_issue.return_value = mock_issue
        mock_firebase_helper.get_user.return_value = None
        mock_firebase_helper.create_user.return_value = Mock()
        
        create_data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1"
        }
        
        create_response = client.post('/api/v1/issues', json=create_data)
        assert create_response.status_code == 201
        issue_id = create_response.get_json()['id']
        
        # Step 2: Add first comment
        mock_firebase_helper.add_comment.return_value = "comment-1"
        comment1_data = {
            "content": "First comment",
            "author_id": "user1"
        }
        
        comment1_response = client.post(
            f'/api/v1/issues/{issue_id}/comments',
            json=comment1_data
        )
        assert comment1_response.status_code == 201
        assert comment1_response.get_json()['id'] == "comment-1"
        
        # Step 3: Add second comment
        mock_firebase_helper.add_comment.return_value = "comment-2"
        comment2_data = {
            "content": "Second comment",
            "author_id": "user2"
        }
        
        comment2_response = client.post(
            f'/api/v1/issues/{issue_id}/comments',
            json=comment2_data
        )
        assert comment2_response.status_code == 201
        
        # Step 4: Get all comments
        mock_comments = [
            Comment(
                id="comment-1",
                issue_id=issue_id,
                author_id="user1",
                content="First comment",
                created_at=datetime.now()
            ),
            Comment(
                id="comment-2",
                issue_id=issue_id,
                author_id="user2",
                content="Second comment",
                created_at=datetime.now()
            )
        ]
        mock_firebase_helper.get_comments.return_value = mock_comments
        
        get_comments_response = client.get(f'/api/v1/issues/{issue_id}/comments')
        assert get_comments_response.status_code == 200
        comments = get_comments_response.get_json()
        assert len(comments) == 2
        assert comments[0]['content'] == "First comment"
        assert comments[1]['content'] == "Second comment"
    
    @patch('apps.web.api.firebase_helper')
    def test_error_handling_flow(self, mock_firebase_helper, client):
        """Test error handling in API flow."""
        # Test invalid request data
        invalid_data = {
            "description": "Test description"
            # Missing required fields
        }
        
        response = client.post('/api/v1/issues', json=invalid_data)
        assert response.status_code == 400
        
        # Test non-existent issue
        mock_firebase_helper.get_issue.return_value = None
        
        response = client.get('/api/v1/issues/nonexistent')
        assert response.status_code == 404
        
        # Test Firebase unavailable
        mock_firebase_helper.is_available.return_value = False
        mock_firebase_helper.create_issue.return_value = None
        
        valid_data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1"
        }
        
        response = client.post('/api/v1/issues', json=valid_data)
        assert response.status_code == 500

