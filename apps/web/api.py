#!/usr/bin/env python3
"""
API endpoints for Issue Tracker (for service-to-service calls)
"""

import logging
from flask import Blueprint, request, jsonify
from apps.web.extensions import limiter
from apps.web.utils.firebase_helper import FirebaseHelper
from apps.web.models import Issue, Comment, IssueStatus, IssuePriority, IssueType, ActivityType, UserRole
from apps.web.schemas import (
    IssueCreateSchema, IssueUpdateSchema, CommentCreateSchema,
    IssuePathSchema, validate_json_body, validate_path_params
)

logger = logging.getLogger(__name__)

# Initialize Firebase helper
firebase_helper = FirebaseHelper()

# Create API blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Exempt entire API blueprint from CSRF protection
# This must be done after csrf is initialized in app.py
# We'll do it in app.py after blueprint registration


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "firebase_available": firebase_helper.is_available()
    }), 200


@api_bp.route("/v1/issues", methods=["POST"])
@limiter.limit("100 per minute")
def create_issue():
    """Create a new issue (for services)"""
    try:
        # Validate request body
        data = validate_json_body(IssueCreateSchema, request.get_json() or {})
        
        # Auto-create service user if reporter doesn't exist
        reporter_id = data["reporter_id"]
        _ensure_service_user(reporter_id)
        
        # Auto-create service user for assignee if provided and doesn't exist
        if data.get("assignee_id"):
            _ensure_service_user(data["assignee_id"])
        
        # Create issue model
        issue = Issue(
            title=data["title"],
            description=data["description"],
            status=IssueStatus(data.get("status", "open")),
            priority=IssuePriority(data.get("priority", "medium")),
            type=IssueType(data.get("type", "task")),
            reporter_id=reporter_id,
            assignee_id=data.get("assignee_id"),
            tags=data.get("tags", [])
        )
        
        # Save to Firebase (this also stores in Redis automatically)
        issue_id = firebase_helper.create_issue(issue)
        
        if not issue_id:
            return jsonify({"error": "Failed to create issue"}), 500
        
        # Get created issue
        created_issue = firebase_helper.get_issue(issue_id)
        if not created_issue:
            return jsonify({"error": "Issue created but not found"}), 500
        
        return jsonify({
            "id": issue_id,
            "title": created_issue.title,
            "status": created_issue.status.value,
            "priority": created_issue.priority.value,
            "type": created_issue.type.value
        }), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating issue: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/v1/issues/<issue_id>", methods=["GET"])
@limiter.limit("200 per minute")
def get_issue(issue_id: str):
    """Get issue by ID"""
    try:
        # Validate path parameter
        validate_path_params(IssuePathSchema, {"issue_id": issue_id})
        
        issue = firebase_helper.get_issue(issue_id)
        
        if not issue:
            return jsonify({"error": "Issue not found"}), 404
        
        # Convert to dict
        issue_dict = issue.to_dict()
        issue_dict["id"] = issue.id
        
        return jsonify(issue_dict), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting issue: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/v1/issues/<issue_id>", methods=["PATCH"])
@limiter.limit("100 per minute")
def update_issue(issue_id: str):
    """Update an issue"""
    try:
        # Validate path parameter
        validate_path_params(IssuePathSchema, {"issue_id": issue_id})
        
        # Validate request body
        data = validate_json_body(IssueUpdateSchema, request.get_json() or {})
        
        # Get current issue
        issue = firebase_helper.get_issue(issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404
        
        # Prepare changes
        changes = {}
        if "title" in data:
            changes["title"] = data["title"]
        if "description" in data:
            changes["description"] = data["description"]
        if "status" in data:
            changes["status"] = IssueStatus(data["status"])
        if "priority" in data:
            changes["priority"] = IssuePriority(data["priority"])
        if "type" in data:
            changes["type"] = IssueType(data["type"])
        if "assignee_id" in data:
            changes["assignee_id"] = data["assignee_id"]
        if "tags" in data:
            changes["tags"] = data["tags"]
        
        # Use reporter_id as user_id for activity log (or get from request if available)
        user_id = request.headers.get("X-User-Id") or issue.reporter_id
        
        # Update issue
        success = firebase_helper.update_issue(issue_id, changes, user_id)
        
        if not success:
            return jsonify({"error": "Failed to update issue"}), 500
        
        # Get updated issue
        updated_issue = firebase_helper.get_issue(issue_id)
        if not updated_issue:
            return jsonify({"error": "Issue updated but not found"}), 500
        
        issue_dict = updated_issue.to_dict()
        issue_dict["id"] = updated_issue.id
        
        return jsonify(issue_dict), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating issue: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/v1/issues/<issue_id>/comments", methods=["POST"])
@limiter.limit("100 per minute")
def create_comment(issue_id: str):
    """Create a comment on an issue"""
    try:
        # Validate path parameter
        validate_path_params(IssuePathSchema, {"issue_id": issue_id})
        
        # Validate request body
        data = validate_json_body(CommentCreateSchema, request.get_json() or {})
        
        # Check if issue exists
        issue = firebase_helper.get_issue(issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404
        
        # Auto-create service user if author doesn't exist
        author_id = data["author_id"]
        _ensure_service_user(author_id)
        
        # Create comment
        comment = Comment(
            author_id=author_id,
            content=data["content"]
        )
        
        comment_id = firebase_helper.create_comment(issue_id, comment)
        
        if not comment_id:
            return jsonify({"error": "Failed to create comment"}), 500
        
        # Update issue in Redis if it exists there (to refresh TTL)
        try:
            from apps.web.utils.redis_helper import RedisHelper
            redis_helper = RedisHelper()
            if redis_helper.is_available():
                updated_issue = firebase_helper.get_issue(issue_id)
                if updated_issue:
                    redis_helper.update_issue(updated_issue)
        except Exception as e:
            logger.debug(f"Failed to update issue in Redis after comment (non-critical): {e}")
        
        # Get created comment
        comments = firebase_helper.get_comments(issue_id)
        created_comment = next((c for c in comments if c.id == comment_id), None)
        
        if not created_comment:
            return jsonify({"error": "Comment created but not found"}), 500
        
        comment_dict = created_comment.to_dict()
        comment_dict["id"] = created_comment.id
        
        return jsonify(comment_dict), 201
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating comment: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/v1/issues/<issue_id>/comments", methods=["GET"])
@limiter.limit("200 per minute")
def get_comments(issue_id: str):
    """Get all comments for an issue"""
    try:
        # Validate path parameter
        validate_path_params(IssuePathSchema, {"issue_id": issue_id})
        
        # Check if issue exists
        issue = firebase_helper.get_issue(issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404
        
        # Get comments
        comments = firebase_helper.get_comments(issue_id)
        
        comments_list = []
        for comment in comments:
            comment_dict = comment.to_dict()
            comment_dict["id"] = comment.id
            comments_list.append(comment_dict)
        
        return jsonify({"comments": comments_list}), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting comments: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


def _ensure_service_user(user_id: str):
    """
    Ensure a service user exists in Firebase.
    Creates the user with SERVICE role if it doesn't exist.
    Non-blocking - logs warning but doesn't raise exception.
    """
    try:
        # Check if user exists
        user = firebase_helper.get_user(user_id)
        if user:
            return  # User already exists
        
        # Create service user
        email = f"{user_id}@service.alphafusion.local"
        display_name = user_id.replace("-", " ").replace("_", " ").title()
        
        created_user = firebase_helper.create_user(
            uid=user_id,
            email=email,
            display_name=display_name,
            role=UserRole.SERVICE
        )
        
        if created_user:
            logger.info(f"Auto-created service user: {user_id} with SERVICE role")
        else:
            logger.warning(f"Failed to auto-create service user: {user_id}")
    
    except Exception as e:
        # Non-blocking - log warning but don't fail the request
        logger.warning(f"Error ensuring service user exists ({user_id}): {e}")

