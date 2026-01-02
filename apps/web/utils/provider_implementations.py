#!/usr/bin/env python3
"""
Provider Implementations for Issue Tracker

Concrete implementations of provider protocols wrapping FirebaseHelper.
"""

import logging
from typing import Optional, List, Dict, Any

from apps.web.utils.providers import (
    FirebaseHelperProvider
)
from apps.web.utils.firebase_helper import FirebaseHelper
from apps.web.models import (
    User, Issue, Comment, Activity, Notification, Backlog,
    UserRole, IssueStatus, IssuePriority, IssueType, BacklogCategory,
    ActivityType, NotificationType
)

logger = logging.getLogger(__name__)


class FirebaseHelperProviderImpl:
    """
    Implementation of FirebaseHelperProvider.
    
    Wraps FirebaseHelper to provide dependency injection.
    """
    
    def __init__(self, firebase_helper: Optional[FirebaseHelper] = None):
        """
        Initialize Firebase helper provider.
        
        Args:
            firebase_helper: Optional FirebaseHelper instance.
                          If None, creates new instance.
        """
        if firebase_helper is not None:
            if not isinstance(firebase_helper, FirebaseHelper):
                raise TypeError("firebase_helper must be an instance of FirebaseHelper")
            self._firebase_helper = firebase_helper
        else:
            self._firebase_helper = FirebaseHelper()
    
    def is_available(self) -> bool:
        """Check if Firebase is available"""
        return self._firebase_helper.is_available()
    
    def create_user(
        self,
        uid: str,
        email: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        role: UserRole = UserRole.VIEWER
    ) -> Optional[User]:
        """Create a new user"""
        return self._firebase_helper.create_user(uid, email, display_name, photo_url, role)
    
    def get_user(self, uid: str) -> Optional[User]:
        """Get user by UID"""
        return self._firebase_helper.get_user(uid)
    
    def update_user(self, uid: str, **kwargs) -> bool:
        """Update user"""
        return self._firebase_helper.update_user(uid, **kwargs)
    
    def list_users(self) -> List[User]:
        """List all users"""
        return self._firebase_helper.list_users()
    
    def create_issue(self, issue: Issue) -> Optional[str]:
        """Create a new issue and return its ID"""
        return self._firebase_helper.create_issue(issue)
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get issue by ID"""
        return self._firebase_helper.get_issue(issue_id)
    
    def update_issue(self, issue_id: str, changes: Dict[str, Any], user_id: str) -> bool:
        """Update issue and log activity"""
        return self._firebase_helper.update_issue(issue_id, changes, user_id)
    
    def list_issues(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Issue]:
        """List issues with optional filters"""
        return self._firebase_helper.list_issues(filters=filters, limit=limit)
    
    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue (and its subcollections)"""
        return self._firebase_helper.delete_issue(issue_id)
    
    def create_comment(self, issue_id: str, comment: Comment) -> Optional[str]:
        """Create a comment on an issue"""
        return self._firebase_helper.create_comment(issue_id, comment)
    
    def get_comments(self, issue_id: str) -> List[Comment]:
        """Get all comments for an issue"""
        return self._firebase_helper.get_comments(issue_id)
    
    def create_activity(
        self,
        issue_id: str,
        activity_type: ActivityType,
        user_id: str,
        changes: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Create an activity log entry"""
        return self._firebase_helper.create_activity(issue_id, activity_type, user_id, changes)
    
    def get_activities(self, issue_id: str) -> List[Activity]:
        """Get all activities for an issue"""
        return self._firebase_helper.get_activities(issue_id)
    
    def create_notification(self, notification: Notification) -> Optional[str]:
        """Create a notification"""
        return self._firebase_helper.create_notification(notification)
    
    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user"""
        return self._firebase_helper.get_notifications(user_id, unread_only=unread_only)
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        return self._firebase_helper.mark_notification_read(notification_id)
    
    def create_backlog(self, backlog: Backlog) -> Optional[str]:
        """Create a new backlog item and return its ID"""
        return self._firebase_helper.create_backlog(backlog)
    
    def get_backlog(self, backlog_id: str) -> Optional[Backlog]:
        """Get backlog item by ID"""
        return self._firebase_helper.get_backlog(backlog_id)
    
    def update_backlog(self, backlog_id: str, changes: Dict[str, Any], user_id: str) -> bool:
        """Update backlog item"""
        return self._firebase_helper.update_backlog(backlog_id, changes, user_id)
    
    def list_backlog(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Backlog]:
        """List backlog items with optional filters"""
        return self._firebase_helper.list_backlog(filters=filters, limit=limit)
    
    def delete_backlog(self, backlog_id: str) -> bool:
        """Delete backlog item"""
        return self._firebase_helper.delete_backlog(backlog_id)

