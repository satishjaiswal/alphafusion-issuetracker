#!/usr/bin/env python3
"""
Firebase Helper for Issue Tracker
Wraps FirebaseClient for Firestore operations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from firebase_admin import firestore

try:
    from alphafusion.storage.firebase.firebase_client import FirebaseClient
except ImportError:
    # Fallback for development
    FirebaseClient = None

from apps.web.models import (
    User, Issue, Comment, Activity, Notification, Backlog,
    UserRole, IssueStatus, IssuePriority, IssueType, BacklogCategory,
    ActivityType, NotificationType
)

logger = logging.getLogger(__name__)


class FirebaseHelper:
    """Helper class for Firebase Firestore operations"""
    
    def __init__(self):
        """Initialize Firebase helper"""
        self._firebase_client = None
        self.db: Optional[firestore.Client] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Firebase client"""
        try:
            if FirebaseClient:
                logger.debug("Creating FirebaseClient instance...")
                self._firebase_client = FirebaseClient()
                self.db = self._firebase_client.get_client()
                if self.db:
                    logger.info("Firebase helper initialized successfully")
                else:
                    logger.warning("Firebase client not available - FirebaseClient.get_client() returned None")
                    # Log more details about why it failed
                    if self._firebase_client:
                        logger.debug(f"FirebaseClient.db is None. Check FirebaseClient initialization logs.")
            else:
                logger.warning("FirebaseClient not available")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase helper: {e}", exc_info=True)
            self.db = None
    
    def is_available(self) -> bool:
        """Check if Firebase is available"""
        return self.db is not None
    
    # User operations
    def create_user(self, uid: str, email: str, display_name: Optional[str] = None,
                   photo_url: Optional[str] = None, role: UserRole = UserRole.VIEWER) -> Optional[User]:
        """Create a new user"""
        if not self.db:
            return None
        
        try:
            user = User(
                uid=uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                role=role,
                created_at=datetime.now()
            )
            user_ref = self.db.collection("users").document(uid)
            user_ref.set(user.to_dict())
            return user
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    def get_user(self, uid: str) -> Optional[User]:
        """Get user by UID"""
        if not self.db:
            return None
        
        try:
            user_ref = self.db.collection("users").document(uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                return User.from_dict(uid, user_doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def update_user(self, uid: str, **kwargs) -> bool:
        """Update user"""
        if not self.db:
            return False
        
        try:
            user_ref = self.db.collection("users").document(uid)
            update_data = {}
            if "display_name" in kwargs:
                update_data["displayName"] = kwargs["display_name"]
            if "photo_url" in kwargs:
                update_data["photoURL"] = kwargs["photo_url"]
            if "role" in kwargs:
                update_data["role"] = kwargs["role"].value if isinstance(kwargs["role"], UserRole) else kwargs["role"]
            if "last_login" in kwargs:
                # If last_login is None, set it to current datetime; otherwise use the provided value
                if kwargs["last_login"] is None:
                    update_data["lastLogin"] = datetime.now()
                else:
                    update_data["lastLogin"] = kwargs["last_login"]
            
            user_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    def list_users(self) -> List[User]:
        """List all users"""
        if not self.db:
            return []
        
        try:
            users_ref = self.db.collection("users")
            users = []
            for doc in users_ref.stream():
                users.append(User.from_dict(doc.id, doc.to_dict()))
            return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    # Issue operations
    def create_issue(self, issue: Issue) -> Optional[str]:
        """Create a new issue and return its ID"""
        if not self.db:
            return None
        
        try:
            now = datetime.now()
            issue.created_at = now
            issue.updated_at = now
            
            issues_ref = self.db.collection("issues")
            doc_ref = issues_ref.add(issue.to_dict())
            issue_id = doc_ref[1].id
            issue.id = issue_id  # Set the ID for the issue
            
            # Create activity log
            self.create_activity(
                issue_id=issue_id,
                activity_type=ActivityType.CREATED,
                user_id=issue.reporter_id
            )
            
            return issue_id
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return None
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get issue by ID"""
        if not self.db:
            return None
        
        try:
            issue_ref = self.db.collection("issues").document(issue_id)
            issue_doc = issue_ref.get()
            if issue_doc.exists:
                return Issue.from_dict(issue_id, issue_doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Failed to get issue: {e}")
            return None
    
    def update_issue(self, issue_id: str, changes: Dict[str, Any], user_id: str) -> bool:
        """Update issue and log activity"""
        if not self.db:
            return False
        
        try:
            issue_ref = self.db.collection("issues").document(issue_id)
            issue_doc = issue_ref.get()
            
            if not issue_doc.exists:
                return False
            
            current_data = issue_doc.to_dict()
            update_data = {}
            activity_changes = []
            
            # Track changes for activity log
            for key, new_value in changes.items():
                old_value = current_data.get(key)
                if old_value != new_value:
                    # Convert enum to value if needed
                    if isinstance(new_value, (IssueStatus, IssuePriority, IssueType)):
                        new_value = new_value.value
                    if isinstance(old_value, (IssueStatus, IssuePriority, IssueType)):
                        old_value = old_value.value
                    
                    # Map to Firestore field names
                    firestore_key = self._map_field_name(key)
                    update_data[firestore_key] = new_value
                    activity_changes.append({
                        "field": key,
                        "oldValue": str(old_value) if old_value is not None else None,
                        "newValue": str(new_value) if new_value is not None else None
                    })
            
            if not update_data:
                return True  # No changes
            
            update_data["updatedAt"] = datetime.now()
            
            # If status changed to resolved, set resolved_at
            if "status" in changes and changes["status"] == IssueStatus.RESOLVED:
                update_data["resolvedAt"] = datetime.now()
            elif "status" in changes and current_data.get("status") == "resolved" and changes["status"] != IssueStatus.RESOLVED:
                update_data["resolvedAt"] = None
            
            issue_ref.update(update_data)
            
            # Log activity
            if activity_changes:
                activity_type = ActivityType.STATUS_CHANGED if any(c["field"] == "status" for c in activity_changes) else ActivityType.UPDATED
                self.create_activity(
                    issue_id=issue_id,
                    activity_type=activity_type,
                    user_id=user_id,
                    changes=activity_changes
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to update issue: {e}")
            return False
    
    def list_issues(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Issue]:
        """List issues with optional filters"""
        if not self.db:
            return []
        
        try:
            issues_ref = self.db.collection("issues")
            query = issues_ref
            
            # Apply filters
            if filters:
                if "status" in filters:
                    query = query.where("status", "==", filters["status"].value if isinstance(filters["status"], IssueStatus) else filters["status"])
                if "priority" in filters:
                    query = query.where("priority", "==", filters["priority"].value if isinstance(filters["priority"], IssuePriority) else filters["priority"])
                if "type" in filters:
                    query = query.where("type", "==", filters["type"].value if isinstance(filters["type"], IssueType) else filters["type"])
                if "assignee_id" in filters:
                    query = query.where("assigneeId", "==", filters["assignee_id"])
                if "reporter_id" in filters:
                    query = query.where("reporterId", "==", filters["reporter_id"])
            
            # Order by created_at descending
            query = query.order_by("createdAt", direction=firestore.Query.DESCENDING)
            
            issues = []
            for doc in query.limit(limit).stream():
                issues.append(Issue.from_dict(doc.id, doc.to_dict()))
            return issues
        except Exception as e:
            logger.error(f"Failed to list issues: {e}")
            return []
    
    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue (and its subcollections)"""
        if not self.db:
            return False
        
        try:
            issue_ref = self.db.collection("issues").document(issue_id)
            
            # Delete subcollections
            comments_ref = issue_ref.collection("comments")
            for comment_doc in comments_ref.stream():
                comment_doc.reference.delete()
            
            activities_ref = issue_ref.collection("activities")
            for activity_doc in activities_ref.stream():
                activity_doc.reference.delete()
            
            # Delete issue
            issue_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete issue: {e}")
            return False
    
    # Comment operations
    def create_comment(self, issue_id: str, comment: Comment) -> Optional[str]:
        """Create a comment on an issue"""
        if not self.db:
            return None
        
        try:
            now = datetime.now()
            comment.issue_id = issue_id
            comment.created_at = now
            comment.updated_at = now
            
            issue_ref = self.db.collection("issues").document(issue_id)
            comments_ref = issue_ref.collection("comments")
            doc_ref = comments_ref.add(comment.to_dict())
            comment_id = doc_ref[1].id
            
            # Create activity log
            self.create_activity(
                issue_id=issue_id,
                activity_type=ActivityType.COMMENTED,
                user_id=comment.author_id
            )
            
            return comment_id
        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            return None
    
    def get_comments(self, issue_id: str) -> List[Comment]:
        """Get all comments for an issue"""
        if not self.db:
            return []
        
        try:
            issue_ref = self.db.collection("issues").document(issue_id)
            comments_ref = issue_ref.collection("comments")
            comments = []
            for doc in comments_ref.order_by("createdAt", direction=firestore.Query.ASCENDING).stream():
                comments.append(Comment.from_dict(doc.id, doc.to_dict()))
            return comments
        except Exception as e:
            logger.error(f"Failed to get comments: {e}")
            return []
    
    # Activity operations
    def create_activity(self, issue_id: str, activity_type: ActivityType,
                       user_id: str, changes: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Create an activity log entry"""
        if not self.db:
            return None
        
        try:
            activity = Activity(
                type=activity_type,
                user_id=user_id,
                changes=changes or [],
                created_at=datetime.now()
            )
            
            issue_ref = self.db.collection("issues").document(issue_id)
            activities_ref = issue_ref.collection("activities")
            doc_ref = activities_ref.add(activity.to_dict())
            return doc_ref[1].id
        except Exception as e:
            logger.error(f"Failed to create activity: {e}")
            return None
    
    def get_activities(self, issue_id: str) -> List[Activity]:
        """Get all activities for an issue"""
        if not self.db:
            return []
        
        try:
            issue_ref = self.db.collection("issues").document(issue_id)
            activities_ref = issue_ref.collection("activities")
            activities = []
            for doc in activities_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).stream():
                activities.append(Activity.from_dict(doc.id, doc.to_dict()))
            return activities
        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
            return []
    
    # Notification operations
    def create_notification(self, notification: Notification) -> Optional[str]:
        """Create a notification"""
        if not self.db:
            return None
        
        try:
            notification.created_at = datetime.now()
            notifications_ref = self.db.collection("notifications")
            doc_ref = notifications_ref.add(notification.to_dict())
            return doc_ref[1].id
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None
    
    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user"""
        if not self.db:
            return []
        
        try:
            notifications_ref = self.db.collection("notifications")
            query = notifications_ref.where("userId", "==", user_id)
            if unread_only:
                query = query.where("read", "==", False)
            
            notifications = []
            for doc in query.order_by("createdAt", direction=firestore.Query.DESCENDING).stream():
                notifications.append(Notification.from_dict(doc.id, doc.to_dict()))
            return notifications
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        if not self.db:
            return False
        
        try:
            notification_ref = self.db.collection("notifications").document(notification_id)
            notification_ref.update({"read": True})
            return True
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False
    
    # Helper methods
    # Backlog operations
    def create_backlog(self, backlog: Backlog) -> Optional[str]:
        """Create a new backlog item and return its ID"""
        if not self.db:
            return None
        
        try:
            now = datetime.now()
            backlog.created_at = now
            backlog.updated_at = now
            
            backlog_ref = self.db.collection("backlog")
            doc_ref = backlog_ref.add(backlog.to_dict())
            backlog_id = doc_ref[1].id
            backlog.id = backlog_id
            
            return backlog_id
        except Exception as e:
            logger.error(f"Failed to create backlog item: {e}")
            return None
    
    def get_backlog(self, backlog_id: str) -> Optional[Backlog]:
        """Get backlog item by ID"""
        if not self.db:
            return None
        
        try:
            backlog_ref = self.db.collection("backlog").document(backlog_id)
            backlog_doc = backlog_ref.get()
            if backlog_doc.exists:
                return Backlog.from_dict(backlog_id, backlog_doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Failed to get backlog item: {e}")
            return None
    
    def update_backlog(self, backlog_id: str, changes: Dict[str, Any], user_id: str) -> bool:
        """Update backlog item"""
        if not self.db:
            return False
        
        try:
            backlog_ref = self.db.collection("backlog").document(backlog_id)
            backlog_doc = backlog_ref.get()
            
            if not backlog_doc.exists:
                return False
            
            current_data = backlog_doc.to_dict()
            update_data = {}
            
            # Track changes
            for key, new_value in changes.items():
                old_value = current_data.get(key)
                if old_value != new_value:
                    # Convert enum to value if needed
                    if isinstance(new_value, BacklogCategory):
                        new_value = new_value.value
                    if isinstance(old_value, BacklogCategory):
                        old_value = old_value.value
                    
                    # Map to Firestore field names
                    firestore_key = self._map_field_name(key)
                    update_data[firestore_key] = new_value
            
            if not update_data:
                return True  # No changes
            
            update_data["updatedAt"] = datetime.now()
            
            backlog_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update backlog item: {e}")
            return False
    
    def list_backlog(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Backlog]:
        """List backlog items with optional filters"""
        if not self.db:
            return []
        
        try:
            backlog_ref = self.db.collection("backlog")
            query = backlog_ref
            
            # Apply filters
            if filters:
                if "category" in filters:
                    query = query.where("category", "==", filters["category"].value if isinstance(filters["category"], BacklogCategory) else filters["category"])
                if "assignee_id" in filters:
                    query = query.where("assigneeId", "==", filters["assignee_id"])
                if "reporter_id" in filters:
                    query = query.where("reporterId", "==", filters["reporter_id"])
            
            # Order by created_at descending
            query = query.order_by("createdAt", direction=firestore.Query.DESCENDING)
            
            backlog_items = []
            for doc in query.limit(limit).stream():
                backlog_items.append(Backlog.from_dict(doc.id, doc.to_dict()))
            return backlog_items
        except Exception as e:
            logger.error(f"Failed to list backlog items: {e}")
            return []
    
    def delete_backlog(self, backlog_id: str) -> bool:
        """Delete backlog item"""
        if not self.db:
            return False
        
        try:
            backlog_ref = self.db.collection("backlog").document(backlog_id)
            backlog_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete backlog item: {e}")
            return False

    def _map_field_name(self, field_name: str) -> str:
        """Map Python field name to Firestore field name"""
        mapping = {
            "reporter_id": "reporterId",
            "assignee_id": "assigneeId",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "resolved_at": "resolvedAt",
            "completed_at": "completedAt",
            "author_id": "authorId",
            "user_id": "userId",
            "issue_id": "issueId",
            "display_name": "displayName",
            "photo_url": "photoURL",
            "last_login": "lastLogin",
        }
        return mapping.get(field_name, field_name)

