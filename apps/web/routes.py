#!/usr/bin/env python3
"""
Web UI routes for Issue Tracker
"""

import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, jsonify, flash, session, current_app
from apps.web.models import (
    Issue, Comment, IssueStatus, IssuePriority, IssueType, UserRole,
    Backlog, BacklogCategory
)
from apps.web.schemas import (
    IssueCreateSchema, IssueUpdateSchema, CommentCreateSchema,
    IssueQuerySchema, validate_json_body, validate_query_params,
    BacklogCreateSchema, BacklogUpdateSchema, BacklogQuerySchema
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
                return render_template("dashboard.html", stats={}, recent_issues=[], grouped_issues=[])
            
            # Get statistics
            all_issues = firebase_provider.list_issues(limit=1000)
            
            stats = {
                "total": len(all_issues),
                "open": len([i for i in all_issues if i.status == IssueStatus.OPEN]),
                "in_progress": len([i for i in all_issues if i.status == IssueStatus.IN_PROGRESS]),
                "resolved": len([i for i in all_issues if i.status == IssueStatus.RESOLVED]),
                "closed": len([i for i in all_issues if i.status == IssueStatus.CLOSED]),
            }
            
            # Get recent issues and group duplicates by title
            recent_issues = sorted(all_issues, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]
            
            # Group duplicates by title (case-insensitive, normalized)
            grouped_issues = {}
            for issue in recent_issues:
                # Normalize title for grouping (lowercase, strip whitespace)
                normalized_title = issue.title.lower().strip() if issue.title else ""
                if normalized_title not in grouped_issues:
                    grouped_issues[normalized_title] = []
                grouped_issues[normalized_title].append(issue)
            
            # Create list of grouped issues: first issue in each group is the primary, rest are duplicates
            grouped_list = []
            for normalized_title, issues in grouped_issues.items():
                if len(issues) > 1:
                    # Group has duplicates - first one is primary, rest are duplicates
                    grouped_list.append({
                        'is_group': True,
                        'primary': issues[0],
                        'duplicates': issues[1:],
                        'count': len(issues)
                    })
                else:
                    # Single issue, not a duplicate
                    grouped_list.append({
                        'is_group': False,
                        'primary': issues[0],
                        'duplicates': [],
                        'count': 1
                    })
            
            # Sort by primary issue's created_at (most recent first)
            grouped_list.sort(key=lambda x: x['primary'].created_at or datetime.min, reverse=True)
            
            return render_template("dashboard.html", stats=stats, recent_issues=recent_issues, grouped_issues=grouped_list)
        except Exception as e:
            logger.error(f"Error in dashboard: {e}", exc_info=True)
            flash("Error loading dashboard", "error")
            return render_template("dashboard.html", stats={}, recent_issues=[], grouped_issues=[])
    
    @app.route("/issues/recent")
    def issues_recent():
        """List recent issues from Redis (last 1 hour)"""
        try:
            redis_provider = _get_redis_provider()
            firebase_provider = _get_firebase_provider()
            
            if not redis_provider or not redis_provider.is_available():
                flash("Redis provider not available", "error")
                return render_template("issues.html", issues=[], users={}, filters={}, source="recent", grouped_issues=[])
            
            limit = int(request.args.get("limit", 100))
            
            # Get recent issues from Redis
            issues = redis_provider.list_recent_issues(limit=limit)
            
            # Group duplicates by title (case-insensitive, normalized)
            grouped_issues = {}
            for issue in issues:
                # Normalize title for grouping (lowercase, strip whitespace)
                normalized_title = issue.title.lower().strip() if issue.title else ""
                if normalized_title not in grouped_issues:
                    grouped_issues[normalized_title] = []
                grouped_issues[normalized_title].append(issue)
            
            # Create list of grouped issues: first issue in each group is the primary, rest are duplicates
            grouped_list = []
            for normalized_title, issues_list in grouped_issues.items():
                if len(issues_list) > 1:
                    # Group has duplicates - first one is primary, rest are duplicates
                    grouped_list.append({
                        'is_group': True,
                        'primary': issues_list[0],
                        'duplicates': issues_list[1:],
                        'count': len(issues_list)
                    })
                else:
                    # Single issue, not a duplicate
                    grouped_list.append({
                        'is_group': False,
                        'primary': issues_list[0],
                        'duplicates': [],
                        'count': 1
                    })
            
            # Sort by primary issue's created_at (most recent first)
            grouped_list.sort(key=lambda x: x['primary'].created_at or datetime.min, reverse=True)
            
            # Get users for display
            if firebase_provider:
                users = firebase_provider.list_users()
                users_dict = {user.uid: user for user in users}
            else:
                users_dict = {}
            
            return render_template("issues.html", issues=issues, users=users_dict, filters=request.args, source="recent", grouped_issues=grouped_list)
        except Exception as e:
            logger.error(f"Error listing recent issues: {e}", exc_info=True)
            flash("Error loading recent issues", "error")
            return render_template("issues.html", issues=[], users={}, filters={}, source="recent", grouped_issues=[])
    
    @app.route("/issues/all")
    def issues_all():
        """List all issues from Firebase"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return render_template("issues.html", issues=[], users={}, filters={}, source="all", grouped_issues=[])
            
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
            
            # Group duplicates by title (case-insensitive, normalized)
            grouped_issues = {}
            for issue in issues:
                # Normalize title for grouping (lowercase, strip whitespace)
                normalized_title = issue.title.lower().strip() if issue.title else ""
                if normalized_title not in grouped_issues:
                    grouped_issues[normalized_title] = []
                grouped_issues[normalized_title].append(issue)
            
            # Create list of grouped issues: first issue in each group is the primary, rest are duplicates
            grouped_list = []
            for normalized_title, issues_list in grouped_issues.items():
                if len(issues_list) > 1:
                    # Group has duplicates - first one is primary, rest are duplicates
                    grouped_list.append({
                        'is_group': True,
                        'primary': issues_list[0],
                        'duplicates': issues_list[1:],
                        'count': len(issues_list)
                    })
                else:
                    # Single issue, not a duplicate
                    grouped_list.append({
                        'is_group': False,
                        'primary': issues_list[0],
                        'duplicates': [],
                        'count': 1
                    })
            
            # Sort by primary issue's created_at (most recent first)
            grouped_list.sort(key=lambda x: x['primary'].created_at or datetime.min, reverse=True)
            
            # Get users for display
            users = firebase_provider.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template("issues.html", issues=issues, users=users_dict, filters=request.args, source="all", grouped_issues=grouped_list)
        except Exception as e:
            logger.error(f"Error listing all issues: {e}", exc_info=True)
            flash("Error loading issues", "error")
            return render_template("issues.html", issues=[], users={}, filters={}, source="all", grouped_issues=[])
    
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
            # Get current user first
            user_id = get_current_user_id()
            if not user_id:
                flash("Authentication required", "error")
                return redirect(url_for("login"))
            
            # Prepare form data, excluding csrf_token and setting reporter_id
            form_data = request.form.to_dict()
            form_data.pop('csrf_token', None)  # Remove CSRF token from validation
            form_data['reporter_id'] = user_id  # Set reporter_id from session
            
            # Parse tags from comma-separated string
            if 'tags' in form_data and form_data['tags']:
                tags_str = form_data['tags']
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                form_data['tags'] = tags
            else:
                form_data['tags'] = []
            
            # Validate request
            data = validate_json_body(IssueCreateSchema, form_data)
            
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
                    reporter_id=data["reporter_id"],
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
    
    @app.route("/backlog")
    def backlog_list():
        """List all backlog items"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return render_template("backlog.html", backlog_items=[], users={}, filters={}, grouped_backlog=[])
            
            # Get query parameters
            filters = {}
            if request.args.get("category"):
                filters["category"] = BacklogCategory(request.args.get("category"))
            if request.args.get("assignee_id"):
                filters["assignee_id"] = request.args.get("assignee_id")
            if request.args.get("reporter_id"):
                filters["reporter_id"] = request.args.get("reporter_id")
            
            limit = int(request.args.get("limit", 100))
            
            # Get backlog items from Firebase
            backlog_items = firebase_provider.list_backlog(filters=filters, limit=limit)
            
            # Group duplicates by title (case-insensitive, normalized)
            grouped_backlog = {}
            for item in backlog_items:
                normalized_title = item.title.lower().strip() if item.title else ""
                if normalized_title not in grouped_backlog:
                    grouped_backlog[normalized_title] = []
                grouped_backlog[normalized_title].append(item)
            
            # Create list of grouped backlog items
            grouped_list = []
            for normalized_title, items_list in grouped_backlog.items():
                if len(items_list) > 1:
                    grouped_list.append({
                        'is_group': True,
                        'primary': items_list[0],
                        'duplicates': items_list[1:],
                        'count': len(items_list)
                    })
                else:
                    grouped_list.append({
                        'is_group': False,
                        'primary': items_list[0],
                        'duplicates': [],
                        'count': 1
                    })
            
            # Sort by primary item's created_at (most recent first)
            grouped_list.sort(key=lambda x: x['primary'].created_at or datetime.min, reverse=True)
            
            # Get users for display
            users = firebase_provider.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template("backlog.html", backlog_items=backlog_items, users=users_dict, filters=request.args, grouped_backlog=grouped_list)
        except Exception as e:
            logger.error(f"Error listing backlog: {e}", exc_info=True)
            flash("Error loading backlog", "error")
            return render_template("backlog.html", backlog_items=[], users={}, filters={}, grouped_backlog=[])
    
    @app.route("/backlog/create", methods=["GET", "POST"])
    @require_auth
    def create_backlog():
        """Create new backlog item"""
        if request.method == "GET":
            return render_template("create_backlog.html")
        
        try:
            # Get current user first
            user_id = get_current_user_id()
            if not user_id:
                flash("Authentication required", "error")
                return redirect(url_for("login"))
            
            # Prepare form data, excluding csrf_token and setting reporter_id
            form_data = request.form.to_dict()
            form_data.pop('csrf_token', None)  # Remove CSRF token from validation
            form_data['reporter_id'] = user_id  # Set reporter_id from session
            
            # Parse tags from comma-separated string
            if 'tags' in form_data and form_data['tags']:
                tags_str = form_data['tags']
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                form_data['tags'] = tags
            else:
                form_data['tags'] = []
            
            # Validate request
            data = validate_json_body(BacklogCreateSchema, form_data)
            
            # Create backlog item
            firebase_provider = _get_firebase_provider()
            if not firebase_provider or not firebase_provider.is_available():
                flash("Firebase provider not available. Please ensure Firebase credentials are configured.", "error")
                logger.warning("Firebase provider not available when creating backlog item")
                return render_template("create_backlog.html")
            
            backlog = Backlog(
                title=data["title"],
                description=data["description"],
                category=BacklogCategory(data.get("category", "feature-request")),
                reporter_id=data["reporter_id"],
                assignee_id=data.get("assignee_id"),
                tags=data.get("tags", [])
            )
            
            backlog_id = firebase_provider.create_backlog(backlog)
            
            if backlog_id:
                flash("Backlog item created successfully", "success")
                return redirect(url_for("backlog_list"))
            else:
                flash("Failed to create backlog item. Firebase may not be properly configured.", "error")
                logger.error("Failed to create backlog item - create_backlog returned None")
                return render_template("create_backlog.html")
        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return render_template("create_backlog.html")
        except Exception as e:
            logger.error(f"Error creating backlog item: {e}", exc_info=True)
            flash("Error creating backlog item", "error")
            return render_template("create_backlog.html")
    
    @app.route("/backlog/<backlog_id>")
    def backlog_detail(backlog_id: str):
        """Backlog item detail view"""
        try:
            firebase_provider = _get_firebase_provider()
            if not firebase_provider:
                flash("Firebase provider not available", "error")
                return redirect(url_for("backlog_list"))
            
            backlog = firebase_provider.get_backlog(backlog_id)
            if not backlog:
                flash("Backlog item not found", "error")
                return redirect(url_for("backlog_list"))
            
            # Get users for display
            users = firebase_provider.list_users()
            users_dict = {user.uid: user for user in users}
            
            return render_template("backlog_detail.html", backlog=backlog, users=users_dict)
        except Exception as e:
            logger.error(f"Error getting backlog detail: {e}", exc_info=True)
            flash("Error loading backlog item", "error")
            return redirect(url_for("backlog_list"))
    
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
            # NOTE: We create user accounts automatically on first login - this is expected behavior
            firebase_provider = _get_firebase_provider()
            if not firebase_provider or not firebase_provider.is_available():
                logger.error("Firebase provider not available - cannot create/login user")
                flash("Firebase database not available. Please contact administrator.", "error")
                return redirect(url_for("login"))
            
            # Check if user exists in Firebase
            user = firebase_provider.get_user(email)
            if not user:
                # Auto-create user account for first-time login (normal behavior)
                # This happens automatically when a new @quantory.app user logs in for the first time
                display_name = session.get('oauth_name', email.split('@')[0])
                photo_url = session.get('oauth_picture')
                
                logger.info(f"First-time login detected - creating user account for {email}")
                user = firebase_provider.create_user(
                    uid=email,
                    email=email,
                    display_name=display_name,
                    photo_url=photo_url,
                    role=UserRole.DEVELOPER  # Internal quantory.app users get developer role
                )
                
                if not user:
                    logger.error(f"Failed to create user account for {email} - Firebase may not be configured correctly")
                    flash("Failed to create user account. Firebase may not be configured. Please contact administrator.", "error")
                    return redirect(url_for("login"))
            
            # Get display name from OAuth session or user object
            display_name = session.get('oauth_name') or user.display_name or email.split('@')[0]
            
            # Update user info if available (for existing users or to refresh OAuth data)
            if session.get('oauth_name'):
                firebase_provider.update_user(email, display_name=session.get('oauth_name'))
            if session.get('oauth_picture'):
                firebase_provider.update_user(email, photo_url=session.get('oauth_picture'))
            
            # Log in user with display name
            login_user(email, display_name=display_name)
            
            # Get redirect URL from session
            redirect_url = session.pop('oauth_redirect', url_for('dashboard'))
            flash("Logged in successfully", "success")
            return redirect(redirect_url)
        
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

