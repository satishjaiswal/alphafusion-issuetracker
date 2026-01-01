#!/usr/bin/env python3
"""
Provider Interfaces for Issue Tracker

Defines provider protocols for dependency injection following the Provider Pattern.
"""

from typing import Protocol, Optional, List, Dict, Any

from apps.web.models import (
    User, Issue, Comment, Activity, Notification,
    UserRole, IssueStatus, IssuePriority, IssueType,
    ActivityType, NotificationType
)


class FirebaseHelperProvider(Protocol):
    """
    Protocol for Firebase helper provider.
    
    Provides Firebase Firestore operations for Issue Tracker.
    """
    
    def is_available(self) -> bool:
        """Check if Firebase is available"""
        ...
    
    def create_user(
        self,
        uid: str,
        email: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        role: UserRole = UserRole.VIEWER
    ) -> Optional[User]:
        """Create a new user"""
        ...
    
    def get_user(self, uid: str) -> Optional[User]:
        """Get user by UID"""
        ...
    
    def update_user(self, uid: str, **kwargs) -> bool:
        """Update user"""
        ...
    
    def list_users(self) -> List[User]:
        """List all users"""
        ...
    
    def create_issue(self, issue: Issue) -> Optional[str]:
        """Create a new issue and return its ID"""
        ...
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get issue by ID"""
        ...
    
    def update_issue(self, issue_id: str, changes: Dict[str, Any], user_id: str) -> bool:
        """Update issue and log activity"""
        ...
    
    def list_issues(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Issue]:
        """List issues with optional filters"""
        ...
    
    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue (and its subcollections)"""
        ...
    
    def create_comment(self, issue_id: str, comment: Comment) -> Optional[str]:
        """Create a comment on an issue"""
        ...
    
    def get_comments(self, issue_id: str) -> List[Comment]:
        """Get all comments for an issue"""
        ...
    
    def create_activity(
        self,
        issue_id: str,
        activity_type: ActivityType,
        user_id: str,
        changes: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Create an activity log entry"""
        ...
    
    def get_activities(self, issue_id: str) -> List[Activity]:
        """Get all activities for an issue"""
        ...
    
    def create_notification(self, notification: Notification) -> Optional[str]:
        """Create a notification"""
        ...
    
    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user"""
        ...
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        ...


class RedisHelperProvider(Protocol):
    """
    Protocol for Redis helper provider.
    
    Provides Redis cache operations for Issue Tracker with TTL support.
    """
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        ...
    
    def store_issue(self, issue: Issue) -> bool:
        """Store issue in Redis with TTL (1 hour)"""
        ...
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get issue from Redis"""
        ...
    
    def list_recent_issues(self, limit: int = 100) -> List[Issue]:
        """List recent issues from Redis"""
        ...
    
    def update_issue(self, issue: Issue) -> bool:
        """Update issue in Redis"""
        ...
    
    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue from Redis"""
        ...

