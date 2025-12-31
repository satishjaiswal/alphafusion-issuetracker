#!/usr/bin/env python3
"""
Unit tests for Firebase helper.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from apps.web.utils.firebase_helper import FirebaseHelper
from apps.web.models import (
    Issue, Comment, User, Activity, Notification,
    IssueStatus, IssuePriority, IssueType, UserRole
)


class TestFirebaseHelper:
    """Tests for FirebaseHelper."""
    
    def test_initialization(self):
        """Test Firebase helper initialization."""
        with patch('apps.web.utils.firebase_helper.FirebaseClient') as mock_client_class:
            mock_client = Mock()
            mock_db = Mock()
            mock_client.get_client.return_value = mock_db
            mock_client_class.return_value = mock_client
            
            helper = FirebaseHelper()
            
            assert helper._firebase_client is not None
    
    def test_is_available(self):
        """Test checking Firebase availability."""
        helper = FirebaseHelper()
        
        # Mock db
        helper.db = Mock()
        assert helper.is_available() is True
        
        helper.db = None
        assert helper.is_available() is False
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_create_user(self, mock_firestore):
        """Test creating a user."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_collection = Mock()
        mock_doc = Mock()
        mock_collection.document.return_value = mock_doc
        helper.db.collection.return_value = mock_collection
        
        user = helper.create_user(
            uid="user1",
            email="user1@example.com",
            display_name="Test User",
            role=UserRole.DEVELOPER
        )
        
        assert user is not None
        assert user.uid == "user1"
        assert user.email == "user1@example.com"
        assert user.role == UserRole.DEVELOPER
        mock_doc.set.assert_called_once()
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_get_user(self, mock_firestore):
        """Test getting a user."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc.get.return_value.exists = True
        mock_doc.get.return_value.to_dict.return_value = {
            "email": "user1@example.com",
            "role": "developer",
            "displayName": "Test User"
        }
        mock_collection.document.return_value = mock_doc
        helper.db.collection.return_value = mock_collection
        
        user = helper.get_user("user1")
        
        assert user is not None
        assert user.uid == "user1"
        assert user.email == "user1@example.com"
        assert user.role == UserRole.DEVELOPER
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_create_issue(self, mock_firestore):
        """Test creating an issue."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "issue-123"
        mock_collection.add.return_value = (Mock(), mock_doc_ref)
        helper.db.collection.return_value = mock_collection
        
        issue = Issue(
            title="Test Issue",
            description="Test description",
            reporter_id="user1",
            created_at=datetime.now()
        )
        
        issue_id = helper.create_issue(issue)
        
        assert issue_id == "issue-123"
        mock_collection.add.assert_called_once()
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_get_issue(self, mock_firestore):
        """Test getting an issue."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc.get.return_value.exists = True
        mock_doc.get.return_value.to_dict.return_value = {
            "title": "Test Issue",
            "description": "Test description",
            "status": "open",
            "priority": "medium",
            "type": "bug",
            "reporterId": "user1",
            "createdAt": datetime.now().isoformat()
        }
        mock_collection.document.return_value = mock_doc
        helper.db.collection.return_value = mock_collection
        
        issue = helper.get_issue("issue-123")
        
        assert issue is not None
        assert issue.id == "issue-123"
        assert issue.title == "Test Issue"
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_list_issues(self, mock_firestore):
        """Test listing issues."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_limited_query = Mock()
        mock_docs = [
            Mock(to_dict=lambda: {
                "title": "Issue 1",
                "status": "open",
                "priority": "high",
                "type": "bug",
                "reporterId": "user1",
                "createdAt": datetime.now().isoformat()
            }),
            Mock(to_dict=lambda: {
                "title": "Issue 2",
                "status": "in-progress",
                "priority": "medium",
                "type": "feature",
                "reporterId": "user2",
                "createdAt": datetime.now().isoformat()
            })
        ]
        mock_ordered_query = Mock()
        mock_limited_query = Mock()
        mock_limited_query.stream.return_value = mock_docs
        mock_ordered_query.limit.return_value = mock_limited_query
        mock_query.order_by.return_value = mock_ordered_query
        mock_collection.order_by.return_value = mock_ordered_query  # For when no filters
        mock_collection.where.return_value = mock_query
        helper.db.collection.return_value = mock_collection
        
        issues = helper.list_issues(limit=10)
        
        assert len(issues) == 2
        assert issues[0].title == "Issue 1"
        assert issues[1].title == "Issue 2"
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_add_comment(self, mock_firestore):
        """Test adding a comment."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_issue_collection = Mock()
        mock_issue_doc = Mock()
        mock_comments_collection = Mock()
        mock_activities_collection = Mock()
        mock_comment_doc = Mock()
        mock_comment_doc.id = "comment-123"
        mock_comments_collection.add.return_value = (Mock(), mock_comment_doc)

        # Mock collection() to return different collections based on name
        def mock_collection(name):
            if name == "comments":
                return mock_comments_collection
            elif name == "activities":
                return mock_activities_collection
            return Mock()

        mock_issue_doc.collection.side_effect = mock_collection
        mock_issue_collection.document.return_value = mock_issue_doc
        helper.db.collection.return_value = mock_issue_collection
        
        comment = Comment(
            issue_id="issue-123",
            author_id="user1",
            content="Test comment",
            created_at=datetime.now()
        )
        
        comment_id = helper.create_comment("issue-123", comment)
        
        assert comment_id == "comment-123"
        # Should be called twice: once for comment, once for activity
        assert mock_comments_collection.add.call_count == 1
    
    @patch('apps.web.utils.firebase_helper.firestore')
    def test_get_comments(self, mock_firestore):
        """Test getting comments."""
        helper = FirebaseHelper()
        helper.db = Mock()
        
        mock_issue_collection = Mock()
        mock_issue_doc = Mock()
        mock_comments_collection = Mock()
        mock_query = Mock()
        mock_docs = [
            Mock(to_dict=lambda: {
                "issueId": "issue-123",
                "authorId": "user1",
                "content": "Comment 1",
                "createdAt": datetime.now().isoformat()
            }),
            Mock(to_dict=lambda: {
                "issueId": "issue-123",
                "authorId": "user2",
                "content": "Comment 2",
                "createdAt": datetime.now().isoformat()
            })
        ]
        mock_query.stream.return_value = mock_docs
        mock_comments_collection.order_by.return_value = mock_query
        mock_issue_doc.collection.return_value = mock_comments_collection
        mock_issue_collection.document.return_value = mock_issue_doc
        helper.db.collection.return_value = mock_issue_collection
        
        comments = helper.get_comments("issue-123")
        
        assert len(comments) == 2
        assert comments[0].content == "Comment 1"
        assert comments[1].content == "Comment 2"

