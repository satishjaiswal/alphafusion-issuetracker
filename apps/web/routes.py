#!/usr/bin/env python3
"""
Web UI routes for Issue Tracker
"""

import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, jsonify, flash, session
from apps.web.utils.firebase_helper import FirebaseHelper
from apps.web.models import (
    Issue, Comment, IssueStatus, IssuePriority, IssueType, UserRole
)
from apps.web.schemas import (
    IssueCreateSchema, IssueUpdateSchema, CommentCreateSchema,
    IssueQuerySchema, validate_json_body, validate_query_params
)
from apps.web.auth import require_auth, get_current_user, get_current_user_id, login_user, logout_user

logger = logging.getLogger(__name__)

# Initialize Firebase helper
firebase_helper = FirebaseHelper()


def register_routes(app):
    """Register all web UI routes"""
    
    @app.route("/")
    def dashboard():
        """Dashboard - issue overview"""
        try:
            # Get statistics
            all_issues = firebase_helper.list_issues(limit=1000)
            
            stats = {
                "total": len(all_issues),
                "open": len([i for i in all_issues if i.status == IssueStatus.OPEN]),
                "in_progress": len([i for i in all_issues if i.status == IssueStatus.IN_PROGRESS]),
                "resolved": len([i for i in all_issues if i.status == IssueStatus.RESOLVED]),
                "closed": len([i for i in all_issues if i.status == IssueStatus.CLOSED]),
            }
            
            # Get recent issues
            recent_issues = sorted(all_issues, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]
            
            return render_template("dashboard.html", stats=stats, recent_issues=recent_issues)
        except Exception as e:
            logger.error(f"Error in dashboard: {e}", exc_info=True)
            flash("Error loading dashboard", "error")
            return render_template("dashboard.html", stats={}, recent_issues=[])
    
    @app.route("/issues")
    def issues_list():
        """List all issues with filters"""
        try:
            # Get query parameters
            filters = {}
            if request.args.get("status"):
                filters["status"] = IssueStatus(request.args.get("status"))
            if request.args.get("priority"):
                filters["priority"] = IssuePriority(request.args.get("priority"))
            if request.args.get("type"):
                filters["type"] = IssueType(request.args.get("type"))
            if request.args.get("assignee_id"):
                filters["assignee_id"] = request.args.get("assignee_id")
            if request.args.get("reporter_id"):
                filters["reporter_id"] = request.args.get("reporter_id")
            
            limit = int(request.args.get("limit", 100))
            
            # Get issues
            issues = firebase_helper.list_issues(filters=filters, limit=limit)
            
            # Get users for display
            users = firebase_helper.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template("issues.html", issues=issues, users=users_dict, filters=request.args)
        except Exception as e:
            logger.error(f"Error listing issues: {e}", exc_info=True)
            flash("Error loading issues", "error")
            return render_template("issues.html", issues=[], users={}, filters={})
    
    @app.route("/issues/<issue_id>")
    def issue_detail(issue_id: str):
        """Issue detail view"""
        try:
            issue = firebase_helper.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("routes.issues_list"))
            
            # Get comments
            comments = firebase_helper.get_comments(issue_id)
            
            # Get activities
            activities = firebase_helper.get_activities(issue_id)
            
            # Get users for display
            users = firebase_helper.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template(
                "issue_detail.html",
                issue=issue,
                comments=comments,
                activities=activities,
                users=users_dict
            )
        except Exception as e:
            logger.error(f"Error getting issue detail: {e}", exc_info=True)
            flash("Error loading issue", "error")
            return redirect(url_for("routes.issues_list"))
    
    @app.route("/issues/create", methods=["GET", "POST"])
    @require_auth
    def create_issue():
        """Create new issue"""
        if request.method == "GET":
            return render_template("create_issue.html")
        
        try:
            # Validate request
            data = validate_json_body(IssueCreateSchema, request.form.to_dict())
            
            # Get current user
            user_id = get_current_user_id()
            if not user_id:
                flash("Authentication required", "error")
                return redirect(url_for("routes.login"))
            
            # Create issue
            issue = Issue(
                title=data["title"],
                description=data["description"],
                status=IssueStatus(data.get("status", "open")),
                priority=IssuePriority(data.get("priority", "medium")),
                type=IssueType(data.get("type", "task")),
                reporter_id=user_id,
                assignee_id=data.get("assignee_id"),
                tags=data.get("tags", [])
            )
            
            issue_id = firebase_helper.create_issue(issue)
            
            if issue_id:
                flash("Issue created successfully", "success")
                return redirect(url_for("routes.issue_detail", issue_id=issue_id))
            else:
                flash("Failed to create issue", "error")
                return render_template("create_issue.html")
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return render_template("create_issue.html")
        except Exception as e:
            logger.error(f"Error creating issue: {e}", exc_info=True)
            flash("Error creating issue", "error")
            return render_template("create_issue.html")
    
    @app.route("/issues/<issue_id>/update", methods=["POST"])
    @require_auth
    def update_issue(issue_id: str):
        """Update issue"""
        try:
            # Get current issue
            issue = firebase_helper.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("routes.issues_list"))
            
            # Validate request
            form_data = request.form.to_dict()
            data = validate_json_body(IssueUpdateSchema, form_data)
            
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
                changes["assignee_id"] = data["assignee_id"] if data["assignee_id"] else None
            if "tags" in data:
                # Handle tags as comma-separated string or list
                tags = data["tags"]
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                changes["tags"] = tags
            
            # Update issue
            user_id = get_current_user_id()
            success = firebase_helper.update_issue(issue_id, changes, user_id)
            
            if success:
                flash("Issue updated successfully", "success")
            else:
                flash("Failed to update issue", "error")
            
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
        except Exception as e:
            logger.error(f"Error updating issue: {e}", exc_info=True)
            flash("Error updating issue", "error")
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
    
    @app.route("/issues/<issue_id>/comment", methods=["POST"])
    @require_auth
    def add_comment(issue_id: str):
        """Add comment to issue"""
        try:
            # Check if issue exists
            issue = firebase_helper.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("routes.issues_list"))
            
            # Validate request
            form_data = request.form.to_dict()
            form_data["author_id"] = get_current_user_id()
            data = validate_json_body(CommentCreateSchema, form_data)
            
            # Create comment
            comment = Comment(
                author_id=data["author_id"],
                content=data["content"]
            )
            
            comment_id = firebase_helper.create_comment(issue_id, comment)
            
            if comment_id:
                flash("Comment added successfully", "success")
            else:
                flash("Failed to add comment", "error")
            
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
        except Exception as e:
            logger.error(f"Error adding comment: {e}", exc_info=True)
            flash("Error adding comment", "error")
            return redirect(url_for("routes.issue_detail", issue_id=issue_id))
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Simple login (for demo - can be enhanced)"""
        if request.method == "GET":
            return render_template("login.html")
        
        try:
            user_id = request.form.get("user_id")
            if not user_id:
                flash("User ID is required", "error")
                return render_template("login.html")
            
            # Check if user exists, create if not
            user = firebase_helper.get_user(user_id)
            if not user:
                # Create user with viewer role
                user = firebase_helper.create_user(
                    uid=user_id,
                    email=f"{user_id}@alphafusion.local",
                    display_name=user_id,
                    role=UserRole.VIEWER
                )
            
            if user:
                login_user(user_id)
                flash("Logged in successfully", "success")
                return redirect(url_for("routes.dashboard"))
            else:
                flash("Failed to login", "error")
                return render_template("login.html")
        except Exception as e:
            logger.error(f"Error logging in: {e}", exc_info=True)
            flash("Error logging in", "error")
            return render_template("login.html")
    
    @app.route("/logout")
    def logout():
        """Logout"""
        logout_user()
        flash("Logged out successfully", "success")
        return redirect(url_for("routes.dashboard"))

