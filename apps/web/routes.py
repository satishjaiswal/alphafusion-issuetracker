#!/usr/bin/env python3
"""
Web UI routes for Issue Tracker
"""

import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, jsonify, flash, session, current_app
from apps.web.models import (
    Issue, Comment, IssueStatus, IssuePriority, IssueType, UserRole
)
from apps.web.schemas import (
    IssueCreateSchema, IssueUpdateSchema, CommentCreateSchema,
    IssueQuerySchema, validate_json_body, validate_query_params
)
from apps.web.auth import require_auth, get_current_user, get_current_user_id, login_user, logout_user
from apps.web.oauth import start_google_oauth, handle_google_callback, is_quantory_email

logger = logging.getLogger(__name__)


def _get_firebase_provider():
    """Get Firebase provider from Flask app context"""
    return getattr(current_app, 'firebase_helper_provider', None)


def _get_redis_provider():
    """Get Redis provider from Flask app context"""
    return getattr(current_app, 'redis_helper_provider', None)


def register_routes(app):
    """Register all web UI routes"""
    
    @app.route("/")
    def dashboard():
        """Dashboard - issue overview"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return render_template("dashboard.html", stats={}, recent_issues=[])
            
            # Get statistics
            all_issues = firebase_provider.list_issues(limit=1000)
            
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
    
    @app.route("/issues/recent")
    def issues_recent():
        """List recent issues from Redis (last 1 hour)"""
        try:
            redis_provider = _get_redis_provider()
            firebase_provider = _get_firebase_provider()
            
            if not redis_provider or not redis_provider.is_available():
                flash("Redis provider not available", "error")
                return render_template("issues.html", issues=[], users={}, filters={}, source="recent")
            
            limit = int(request.args.get("limit", 100))
            
            # Get recent issues from Redis
            issues = redis_provider.list_recent_issues(limit=limit)
            
            # Get users for display
            if firebase_provider:
                users = firebase_provider.list_users()
                users_dict = {user.uid: user for user in users}
            else:
                users_dict = {}
            
            return render_template("issues.html", issues=issues, users=users_dict, filters=request.args, source="recent")
        except Exception as e:
            logger.error(f"Error listing recent issues: {e}", exc_info=True)
            flash("Error loading recent issues", "error")
            return render_template("issues.html", issues=[], users={}, filters={}, source="recent")
    
    @app.route("/issues/all")
    def issues_all():
        """List all issues from Firebase"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return render_template("issues.html", issues=[], users={}, filters={}, source="all")
            
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
            
            # Get issues from Firebase
            issues = firebase_provider.list_issues(filters=filters, limit=limit)
            
            # Get users for display
            users = firebase_provider.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template("issues.html", issues=issues, users=users_dict, filters=request.args, source="all")
        except Exception as e:
            logger.error(f"Error listing all issues: {e}", exc_info=True)
            flash("Error loading issues", "error")
            return render_template("issues.html", issues=[], users={}, filters={}, source="all")
    
    @app.route("/issues")
    def issues_list():
        """Redirect to recent issues by default"""
        return redirect(url_for("issues_recent"))
    
    @app.route("/issues/<issue_id>")
    def issue_detail(issue_id: str):
        """Issue detail view"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return redirect(url_for("issues_list"))
            
            issue = firebase_provider.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("issues_list"))
            
            # Get comments
            comments = firebase_provider.get_comments(issue_id)
            
            # Get activities
            activities = firebase_provider.get_activities(issue_id)
            
            # Get users for display
            users = firebase_provider.list_users()
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
            return redirect(url_for("issues_list"))
    
    @app.route("/issues/create", methods=["GET", "POST"])
    @require_auth
    def create_issue():
        """Create new issue (publishes to Kafka/Redis only - background consumer writes to Firebase)"""
        if request.method == "GET":
            return render_template("create_issue.html")
        
        try:
            # Validate request
            data = validate_json_body(IssueCreateSchema, request.form.to_dict())
            
            # Get current user
            user_id = get_current_user_id()
            if not user_id:
                flash("Authentication required", "error")
                return redirect(url_for("login"))
            
            # Publish to Kafka/Redis (single data flow - no direct Firebase write)
            try:
                from alphafusion.utils.issue_publisher import get_issue_publisher
                publisher = get_issue_publisher()
                
                if not publisher or not publisher.is_available():
                    flash("Issue publishing service unavailable. Please try again later.", "error")
                    return render_template("create_issue.html")
                
                # Publish issue to Kafka/Redis
                success = publisher.publish_issue(
                    title=data["title"],
                    description=data["description"],
                    type=data.get("type", "task"),
                    priority=data.get("priority", "medium"),
                    reporter_id=user_id,
                    assignee_id=data.get("assignee_id"),
                    tags=data.get("tags", []),
                    component="web-ui"
                )
                
                if success:
                    flash("Issue created successfully. It will appear in the system shortly.", "success")
                    # Redirect to recent issues (will show from Redis)
                    return redirect(url_for("issues_recent"))
                else:
                    flash("Failed to publish issue. Please try again.", "error")
                    return render_template("create_issue.html")
            except Exception as e:
                logger.error(f"Error publishing issue: {e}", exc_info=True)
                flash("Error creating issue. Please try again.", "error")
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
            firebase_provider = _get_firebase_provider()
            redis_provider = _get_redis_provider()
            
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return redirect(url_for("issues_list"))
            
            # Get current issue
            issue = firebase_provider.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("issues_list"))
            
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
            success = firebase_provider.update_issue(issue_id, changes, user_id)
            
            # Update in Redis if available
            if success and redis_provider and redis_provider.is_available():
                updated_issue = firebase_provider.get_issue(issue_id)
                if updated_issue:
                    redis_provider.update_issue(updated_issue)
            
            if success:
                flash("Issue updated successfully", "success")
            else:
                flash("Failed to update issue", "error")
            
            return redirect(url_for("issue_detail", issue_id=issue_id))
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("issue_detail", issue_id=issue_id))
        except Exception as e:
            logger.error(f"Error updating issue: {e}", exc_info=True)
            flash("Error updating issue", "error")
            return redirect(url_for("issue_detail", issue_id=issue_id))
    
    @app.route("/issues/<issue_id>/comment", methods=["POST"])
    @require_auth
    def add_comment(issue_id: str):
        """Add comment to issue"""
        try:
            firebase_provider = _get_firebase_provider()
            redis_provider = _get_redis_provider()
            
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return redirect(url_for("issues_list"))
            
            # Check if issue exists
            issue = firebase_provider.get_issue(issue_id)
            if not issue:
                flash("Issue not found", "error")
                return redirect(url_for("issues_list"))
            
            # Validate request
            form_data = request.form.to_dict()
            form_data["author_id"] = get_current_user_id()
            data = validate_json_body(CommentCreateSchema, form_data)
            
            # Create comment
            comment = Comment(
                author_id=data["author_id"],
                content=data["content"]
            )
            
            comment_id = firebase_provider.create_comment(issue_id, comment)
            
            # Update issue in Redis if available (to refresh TTL)
            if comment_id and redis_provider and redis_provider.is_available():
                updated_issue = firebase_provider.get_issue(issue_id)
                if updated_issue:
                    redis_provider.update_issue(updated_issue)
            
            if comment_id:
                flash("Comment added successfully", "success")
            else:
                flash("Failed to add comment", "error")
            
            return redirect(url_for("issue_detail", issue_id=issue_id))
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("issue_detail", issue_id=issue_id))
        except Exception as e:
            logger.error(f"Error adding comment: {e}", exc_info=True)
            flash("Error adding comment", "error")
            return redirect(url_for("issue_detail", issue_id=issue_id))
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Login - Only @quantory.app users allowed via Google OAuth"""
        if request.method == "GET":
            return render_template("login.html")
        
        try:
            user_id = request.form.get("user_id")
            if not user_id:
                flash("Email is required", "error")
                return render_template("login.html")
            
            # Only allow @quantory.app emails
            if not is_quantory_email(user_id):
                flash("Only @quantory.app email addresses are allowed", "error")
                return render_template("login.html")
            
            # Start Google OAuth flow
            redirect_response = start_google_oauth()
            if redirect_response:
                return redirect_response
            else:
                flash("Google OAuth not configured. Please contact administrator.", "error")
                return render_template("login.html")
        
        except Exception as e:
            logger.error(f"Error logging in: {e}", exc_info=True)
            flash("Error logging in", "error")
            return render_template("login.html")
    
    @app.route("/oauth/callback")
    def oauth_callback():
        """Handle Google OAuth callback"""
        try:
            # Handle OAuth callback
            email = handle_google_callback()
            
            if not email:
                flash("Failed to authenticate with Google", "error")
                return redirect(url_for("login"))
            
            # Get or create user in Firebase
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return redirect(url_for("login"))
            
            # Check if user exists
            user = firebase_provider.get_user(email)
            if not user:
                # Create user with developer role (quantory.app users are internal)
                display_name = session.get('oauth_name', email.split('@')[0])
                photo_url = session.get('oauth_picture')
                
                user = firebase_provider.create_user(
                    uid=email,
                    email=email,
                    display_name=display_name,
                    photo_url=photo_url,
                    role=UserRole.DEVELOPER  # Internal quantory.app users get developer role
                )
            
            if user:
                # Update user info if available
                if session.get('oauth_name'):
                    firebase_provider.update_user(email, display_name=session.get('oauth_name'))
                if session.get('oauth_picture'):
                    firebase_provider.update_user(email, photo_url=session.get('oauth_picture'))
                
                # Log in user
                login_user(email)
                
                # Get redirect URL from session
                redirect_url = session.pop('oauth_redirect', url_for('dashboard'))
                flash("Logged in successfully", "success")
                return redirect(redirect_url)
            else:
                flash("Failed to create user account", "error")
                return redirect(url_for("login"))
        
        except Exception as e:
            logger.error(f"Error in OAuth callback: {e}", exc_info=True)
            flash("Error during authentication", "error")
            return redirect(url_for("login"))
    
    @app.route("/logout")
    def logout():
        """Logout"""
        logout_user()
        flash("Logged out successfully", "success")
        return redirect(url_for("dashboard"))
    
    @app.route("/favicon.ico")
    def favicon():
        """Handle favicon requests"""
        from flask import abort
        abort(404)

