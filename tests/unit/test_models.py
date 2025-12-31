#!/usr/bin/env python3
"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from apps.web.models import (
    Issue, Comment, User, Activity, Notification, Attachment,
    IssueStatus, IssuePriority, IssueType, UserRole,
    ActivityType, NotificationType
)


class TestIssue:
    """Tests for Issue model."""
    
    def test_issue_creation(self):
        """Test creating an issue."""
        issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.OPEN,
            priority=IssuePriority.HIGH,
            type=IssueType.BUG,
            reporter_id="user1",
            assignee_id="user2",
            tags=["bug", "critical"],
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert issue.id == "test-123"
        assert issue.title == "Test Issue"
        assert issue.status == IssueStatus.OPEN
        assert issue.priority == IssuePriority.HIGH
        assert issue.type == IssueType.BUG
        assert issue.reporter_id == "user1"
        assert issue.assignee_id == "user2"
        assert len(issue.tags) == 2
    
    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = Issue(
            id="test-123",
            title="Test Issue",
            description="Test description",
            status=IssueStatus.OPEN,
            priority=IssuePriority.HIGH,
            type=IssueType.BUG,
            reporter_id="user1",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = issue.to_dict()
        
        assert data["title"] == "Test Issue"
        assert data["status"] == "open"
        assert data["priority"] == "high"
        assert data["type"] == "bug"
        assert data["reporterId"] == "user1"
        assert "createdAt" in data
    
    def test_issue_from_dict(self):
        """Test creating issue from dictionary."""
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "status": "open",
            "priority": "high",
            "type": "bug",
            "reporterId": "user1",
            "assigneeId": "user2",
            "tags": ["bug", "critical"],
            "createdAt": "2024-01-01T12:00:00Z"
        }
        
        issue = Issue.from_dict("test-123", data)
        
        assert issue.id == "test-123"
        assert issue.title == "Test Issue"
        assert issue.status == IssueStatus.OPEN
        assert issue.priority == IssuePriority.HIGH
        assert issue.type == IssueType.BUG
        assert issue.reporter_id == "user1"
        assert issue.assignee_id == "user2"
        assert len(issue.tags) == 2


class TestComment:
    """Tests for Comment model."""
    
    def test_comment_creation(self):
        """Test creating a comment."""
        comment = Comment(
            id="comment-123",
            issue_id="issue-123",
            author_id="user1",
            content="Test comment",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert comment.id == "comment-123"
        assert comment.issue_id == "issue-123"
        assert comment.author_id == "user1"
        assert comment.content == "Test comment"
    
    def test_comment_to_dict(self):
        """Test converting comment to dictionary."""
        comment = Comment(
            issue_id="issue-123",
            author_id="user1",
            content="Test comment",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = comment.to_dict()
        
        assert data["issueId"] == "issue-123"
        assert data["authorId"] == "user1"
        assert data["content"] == "Test comment"
        assert "createdAt" in data
    
    def test_comment_from_dict(self):
        """Test creating comment from dictionary."""
        data = {
            "issueId": "issue-123",
            "authorId": "user1",
            "content": "Test comment",
            "createdAt": "2024-01-01T12:00:00Z"
        }
        
        comment = Comment.from_dict("comment-123", data)
        
        assert comment.id == "comment-123"
        assert comment.issue_id == "issue-123"
        assert comment.author_id == "user1"
        assert comment.content == "Test comment"


class TestUser:
    """Tests for User model."""
    
    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            uid="user1",
            email="user1@example.com",
            display_name="Test User",
            role=UserRole.DEVELOPER,
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert user.uid == "user1"
        assert user.email == "user1@example.com"
        assert user.display_name == "Test User"
        assert user.role == UserRole.DEVELOPER
    
    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        user = User(
            uid="user1",
            email="user1@example.com",
            display_name="Test User",
            role=UserRole.DEVELOPER,
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = user.to_dict()
        
        assert data["email"] == "user1@example.com"
        assert data["role"] == "developer"
        assert data["displayName"] == "Test User"
    
    def test_user_from_dict(self):
        """Test creating user from dictionary."""
        data = {
            "email": "user1@example.com",
            "displayName": "Test User",
            "role": "developer",
            "createdAt": "2024-01-01T12:00:00Z"
        }
        
        user = User.from_dict("user1", data)
        
        assert user.uid == "user1"
        assert user.email == "user1@example.com"
        assert user.display_name == "Test User"
        assert user.role == UserRole.DEVELOPER


class TestActivity:
    """Tests for Activity model."""
    
    def test_activity_creation(self):
        """Test creating an activity."""
        activity = Activity(
            id="activity-123",
            type=ActivityType.CREATED,
            user_id="user1",
            changes=[{"field": "status", "old": "open", "new": "in-progress"}],
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert activity.id == "activity-123"
        assert activity.type == ActivityType.CREATED
        assert activity.user_id == "user1"
        assert len(activity.changes) == 1
    
    def test_activity_to_dict(self):
        """Test converting activity to dictionary."""
        activity = Activity(
            type=ActivityType.CREATED,
            user_id="user1",
            changes=[{"field": "status", "old": "open", "new": "in-progress"}],
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = activity.to_dict()
        
        assert data["type"] == "created"
        assert data["userId"] == "user1"
        assert len(data["changes"]) == 1


class TestNotification:
    """Tests for Notification model."""
    
    def test_notification_creation(self):
        """Test creating a notification."""
        notification = Notification(
            id="notif-123",
            user_id="user1",
            type=NotificationType.ASSIGNED,
            issue_id="issue-123",
            message="You have been assigned to an issue",
            read=False,
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert notification.id == "notif-123"
        assert notification.user_id == "user1"
        assert notification.type == NotificationType.ASSIGNED
        assert notification.issue_id == "issue-123"
        assert notification.read is False
    
    def test_notification_to_dict(self):
        """Test converting notification to dictionary."""
        notification = Notification(
            user_id="user1",
            type=NotificationType.ASSIGNED,
            issue_id="issue-123",
            message="You have been assigned",
            read=False,
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = notification.to_dict()
        
        assert data["userId"] == "user1"
        assert data["type"] == "assigned"
        assert data["issueId"] == "issue-123"
        assert data["read"] is False


class TestAttachment:
    """Tests for Attachment model."""
    
    def test_attachment_creation(self):
        """Test creating an attachment."""
        attachment = Attachment(
            url="https://example.com/file.pdf",
            name="file.pdf",
            size=1024,
            uploaded_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert attachment.url == "https://example.com/file.pdf"
        assert attachment.name == "file.pdf"
        assert attachment.size == 1024
    
    def test_attachment_to_dict(self):
        """Test converting attachment to dictionary."""
        attachment = Attachment(
            url="https://example.com/file.pdf",
            name="file.pdf",
            size=1024,
            uploaded_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        data = attachment.to_dict()
        
        assert data["url"] == "https://example.com/file.pdf"
        assert data["name"] == "file.pdf"
        assert data["size"] == 1024

