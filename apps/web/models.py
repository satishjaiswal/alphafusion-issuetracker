#!/usr/bin/env python3
"""
Data models for Issue Tracker
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class IssueStatus(str, Enum):
    """Issue status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssuePriority(str, Enum):
    """Issue priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Issue type enumeration"""
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    ENHANCEMENT = "enhancement"


class BacklogCategory(str, Enum):
    """Backlog category enumeration"""
    FEATURE_REQUEST = "feature-request"
    SUGGESTIONS = "suggestions"
    IMPROVEMENT = "improvement"
    MUST_HAVE = "must-have"
    CRITICAL = "critical"


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    TESTER = "tester"
    VIEWER = "viewer"
    SERVICE = "service"  # For automated service users


class ActivityType(str, Enum):
    """Activity type enumeration"""
    CREATED = "created"
    UPDATED = "updated"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status-changed"
    COMMENTED = "commented"


class NotificationType(str, Enum):
    """Notification type enumeration"""
    ASSIGNED = "assigned"
    MENTIONED = "mentioned"
    STATUS_CHANGED = "status-changed"
    COMMENTED = "commented"


@dataclass
class Attachment:
    """Attachment model"""
    url: str
    name: str
    size: int
    uploaded_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "url": self.url,
            "name": self.name,
            "size": self.size,
            "uploadedAt": self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        """Create from dictionary"""
        uploaded_at = data.get("uploadedAt") or data.get("uploaded_at")
        if isinstance(uploaded_at, str):
            uploaded_at = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
        return cls(
            url=data["url"],
            name=data["name"],
            size=data["size"],
            uploaded_at=uploaded_at
        )


@dataclass
class User:
    """User model"""
    uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "email": self.email,
            "role": self.role.value,
        }
        if self.display_name:
            result["displayName"] = self.display_name
        if self.photo_url:
            result["photoURL"] = self.photo_url
        if self.created_at:
            result["createdAt"] = self.created_at
        if self.last_login:
            result["lastLogin"] = self.last_login
        return result

    @classmethod
    def from_dict(cls, uid: str, data: Dict[str, Any]) -> "User":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        last_login = data.get("lastLogin")
        if isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
        return cls(
            uid=uid,
            email=data.get("email", ""),
            display_name=data.get("displayName") or data.get("display_name"),
            photo_url=data.get("photoURL") or data.get("photo_url"),
            role=UserRole(data.get("role", "viewer")),
            created_at=created_at,
            last_login=last_login
        )


@dataclass
class Comment:
    """Comment model"""
    id: Optional[str] = None
    issue_id: Optional[str] = None
    author_id: str = ""
    content: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "issueId": self.issue_id or "",
            "authorId": self.author_id,
            "content": self.content,
        }
        if self.created_at:
            result["createdAt"] = self.created_at
        if self.updated_at:
            result["updatedAt"] = self.updated_at
        return result

    @classmethod
    def from_dict(cls, comment_id: str, data: Dict[str, Any]) -> "Comment":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        updated_at = data.get("updatedAt")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return cls(
            id=comment_id,
            issue_id=data.get("issueId") or data.get("issue_id"),
            author_id=data.get("authorId") or data.get("author_id", ""),
            content=data.get("content", ""),
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Activity:
    """Activity log model"""
    id: Optional[str] = None
    type: ActivityType = ActivityType.UPDATED
    user_id: str = ""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "type": self.type.value,
            "userId": self.user_id,
            "changes": self.changes,
        }
        if self.created_at:
            result["createdAt"] = self.created_at
        return result

    @classmethod
    def from_dict(cls, activity_id: str, data: Dict[str, Any]) -> "Activity":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return cls(
            id=activity_id,
            type=ActivityType(data.get("type", "updated")),
            user_id=data.get("userId") or data.get("user_id", ""),
            changes=data.get("changes", []),
            created_at=created_at
        )


@dataclass
class Issue:
    """Issue model"""
    id: Optional[str] = None
    title: str = ""
    description: str = ""
    status: IssueStatus = IssueStatus.OPEN
    priority: IssuePriority = IssuePriority.MEDIUM
    type: IssueType = IssueType.TASK
    reporter_id: str = ""
    assignee_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "type": self.type.value,
            "reporterId": self.reporter_id,
            "tags": self.tags,
            "attachments": [att.to_dict() for att in self.attachments],
        }
        if self.assignee_id:
            result["assigneeId"] = self.assignee_id
        if self.created_at:
            result["createdAt"] = self.created_at
        if self.updated_at:
            result["updatedAt"] = self.updated_at
        if self.resolved_at:
            result["resolvedAt"] = self.resolved_at
        return result

    @classmethod
    def from_dict(cls, issue_id: str, data: Dict[str, Any]) -> "Issue":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        updated_at = data.get("updatedAt")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        resolved_at = data.get("resolvedAt")
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        attachments = [
            Attachment.from_dict(att) if isinstance(att, dict) else att
            for att in data.get("attachments", [])
        ]
        return cls(
            id=issue_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=IssueStatus(data.get("status", "open")),
            priority=IssuePriority(data.get("priority", "medium")),
            type=IssueType(data.get("type", "task")),
            reporter_id=data.get("reporterId") or data.get("reporter_id", ""),
            assignee_id=data.get("assigneeId") or data.get("assignee_id"),
            tags=data.get("tags", []),
            attachments=attachments,
            created_at=created_at,
            updated_at=updated_at,
            resolved_at=resolved_at
        )


@dataclass
class Backlog:
    """Backlog item model"""
    id: Optional[str] = None
    title: str = ""
    description: str = ""
    category: BacklogCategory = BacklogCategory.FEATURE_REQUEST
    reporter_id: str = ""
    assignee_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "reporterId": self.reporter_id,
            "tags": self.tags,
            "attachments": [att.to_dict() for att in self.attachments],
        }
        if self.assignee_id:
            result["assigneeId"] = self.assignee_id
        if self.created_at:
            result["createdAt"] = self.created_at
        if self.updated_at:
            result["updatedAt"] = self.updated_at
        if self.completed_at:
            result["completedAt"] = self.completed_at
        return result

    @classmethod
    def from_dict(cls, backlog_id: str, data: Dict[str, Any]) -> "Backlog":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        updated_at = data.get("updatedAt")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        completed_at = data.get("completedAt")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        attachments = [
            Attachment.from_dict(att) if isinstance(att, dict) else att
            for att in data.get("attachments", [])
        ]
        return cls(
            id=backlog_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=BacklogCategory(data.get("category", "feature-request")),
            reporter_id=data.get("reporterId") or data.get("reporter_id", ""),
            assignee_id=data.get("assigneeId") or data.get("assignee_id"),
            tags=data.get("tags", []),
            attachments=attachments,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at
        )


@dataclass
class Notification:
    """Notification model"""
    id: Optional[str] = None
    user_id: str = ""
    type: NotificationType = NotificationType.COMMENTED
    issue_id: Optional[str] = None
    message: str = ""
    read: bool = False
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore"""
        result = {
            "userId": self.user_id,
            "type": self.type.value,
            "message": self.message,
            "read": self.read,
        }
        if self.issue_id:
            result["issueId"] = self.issue_id
        if self.created_at:
            result["createdAt"] = self.created_at
        return result

    @classmethod
    def from_dict(cls, notification_id: str, data: Dict[str, Any]) -> "Notification":
        """Create from Firestore document"""
        created_at = data.get("createdAt")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return cls(
            id=notification_id,
            user_id=data.get("userId") or data.get("user_id", ""),
            type=NotificationType(data.get("type", "commented")),
            issue_id=data.get("issueId") or data.get("issue_id"),
            message=data.get("message", ""),
            read=data.get("read", False),
            created_at=created_at
        )

