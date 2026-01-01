# AlphaFusion Issue Tracker

Issue tracking application for the AlphaFusion trading platform. Tracks bugs, features, tasks, and enhancements with a web UI and REST API.

## Overview

The Issue Tracker provides:
- **Web UI**: Manual issue creation and management (restricted to @quantory.app users via Google OAuth)
- **REST API**: Programmatic issue logging for services (no authentication required)
- **Firebase Integration**: Stores data in Firestore
- **Role-Based Access**: Admin, developer, tester, and viewer roles
- **Authentication**: Google OAuth for @quantory.app users only

## Architecture

### Tech Stack
- **Web Framework**: Flask 3.0+
- **Database**: Firebase Firestore (via existing FirebaseClient)
- **Security**: Flask-WTF (CSRF), Flask-Talisman (security headers), Flask-Limiter (rate limiting)
- **Base Image**: `alphafusion-baseimage:latest`
- **Configuration**: SecureConfigLoader

### Data Structure

Firestore collections:
- `users` - User management with roles
- `issues` - Main issue collection
- `issues/{issueId}/comments` - Issue comments (subcollection)
- `issues/{issueId}/activities` - Activity logs (subcollection)
- `notifications` - User notifications

## Setup

### Prerequisites
- Docker and docker-compose
- Firebase credentials configured in `.credentials/integrations/firebase.json`
- Access to alphafusion-network Docker network

### Configuration

1. **Firebase Credentials**: Ensure Firebase credentials are configured in `.credentials/integrations/firebase.json`:
   ```json
   {
     "credentials_path": "/app/.credentials/firebase-credentials.json",
     "project_id": "your-firebase-project-id"
   }
   ```

2. **Google OAuth Credentials** (for @quantory.app users):
   - **You need OAuth Client ID and Client Secret** (not an API key)
   - **Recommended**: Create `.credentials/app/issuetracker/google-issuetracker.json`:
     ```json
     {
         "GOOGLE_CLIENT_ID": "your-client-id",
         "GOOGLE_CLIENT_SECRET": "your-client-secret"
     }
     ```
   - **Alternative 1**: Set environment variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
   - **Alternative 2**: Configure via SecureConfigLoader at `app/issuetracker/google_client_id` and `app/issuetracker/google_client_secret`
   - **Quick Setup**:
     1. Go to [Google Cloud Console](https://console.cloud.google.com/)
     2. Create/select a project
     3. Enable "Google+ API" or "Google Identity API"
     4. Go to "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID"
     5. Application type: "Web application"
     6. Authorized redirect URIs: `http://localhost:6002/oauth/callback` (dev) and your production URL
     7. Copy Client ID and Client Secret
   - **Detailed Setup Guide**: See [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md)

3. **Service Configuration**: Service config is in `alphafusion-config/services/issuetracker.json`

4. **SecureConfigLoader**: Config mapping is in `config_mapping.json`

### Running with Docker Compose

The service is integrated into the main docker-compose.yml. To run:

```bash
cd alphafusion-common/container
docker-compose up -d issuetracker
```

Or run standalone:

```bash
cd alphafusion-issuetracker
docker-compose up -d
```

### Access

- **Web UI**: http://localhost:6002
- **API**: http://localhost:6002/api/v1/

## API Documentation

### Health Check

```http
GET /api/health
```

Returns service health status.

### Create Issue

```http
POST /api/v1/issues
Content-Type: application/json

{
  "title": "Error in workflow",
  "description": "Workflow failed at step X",
  "type": "bug",
  "priority": "high",
  "reporter_id": "user123",
  "assignee_id": "dev456",  // optional
  "tags": ["workflow", "error"]  // optional
}
```

**Response**: `201 Created`
```json
{
  "id": "issue-id-here",
  "title": "Error in workflow",
  "status": "open",
  "priority": "high",
  "type": "bug"
}
```

### Get Issue

```http
GET /api/v1/issues/{issue_id}
```

**Response**: `200 OK`
```json
{
  "id": "issue-id",
  "title": "Error in workflow",
  "description": "Workflow failed at step X",
  "status": "open",
  "priority": "high",
  "type": "bug",
  "reporterId": "user123",
  "assigneeId": "dev456",
  "tags": ["workflow", "error"],
  "createdAt": "2024-01-01T12:00:00Z",
  "updatedAt": "2024-01-01T12:00:00Z"
}
```

### Update Issue

```http
PATCH /api/v1/issues/{issue_id}
Content-Type: application/json
X-User-Id: user123

{
  "status": "in-progress",
  "priority": "critical"
}
```

### Add Comment

```http
POST /api/v1/issues/{issue_id}/comments
Content-Type: application/json

{
  "content": "Fixed in commit abc123",
  "author_id": "dev456"
}
```

### Get Comments

```http
GET /api/v1/issues/{issue_id}/comments
```

## Service Integration

Services can log issues programmatically using the `IssueTrackerClient`:

```python
from alphafusion.utils.issue_tracker_client import IssueTrackerClient

client = IssueTrackerClient()

# Log an issue (non-blocking, fails silently if service unavailable)
# Service users are auto-created with SERVICE role if they don't exist
issue_id = client.log_issue(
    title="Error in workflow",
    description="Workflow failed at step X",
    type="bug",
    priority="high",
    reporter_id="workflow-consumer"  # Auto-created as service user if needed
)

# Add a comment
client.add_comment(
    issue_id=issue_id,
    content="Fixed in commit abc123",
    author_id="workflow-consumer"  # Auto-created as service user if needed
)

# Update status
client.update_issue_status(
    issue_id=issue_id,
    status="resolved"
)
```

**Important**: 
- All operations are non-blocking and fail silently if the issue tracker service is unavailable. This ensures services continue to operate even if the tracker is down.
- **Auto-User Creation**: When services log issues via the API, service users are automatically created with the `SERVICE` role if they don't exist. The user ID is used as the identifier (e.g., "workflow-consumer", "data-enrich"). This ensures proper user tracking and display in the web UI.

## Web UI

### Features
- **Dashboard**: Overview of issue statistics and recent issues
- **Issue List**: View and filter all issues
- **Issue Detail**: View issue details, comments, and activities
- **Create Issue**: Create new issues via web form
- **Update Issue**: Update status, priority, assignee
- **Comments**: Add comments to issues

### Authentication

Simple session-based authentication. Users can login with a user ID, and a user will be created automatically if it doesn't exist.

Default roles:
- **admin**: Full access
- **developer**: Can create and update issues
- **tester**: Can create issues and add comments
- **viewer**: Read-only access
- **service**: Automated service users (auto-created when services log issues via API)

## Development

### Project Structure

```
alphafusion-issuetracker/
├── apps/
│   └── web/
│       ├── app.py              # Flask app
│       ├── routes.py            # Web UI routes
│       ├── api.py               # API endpoints
│       ├── models.py            # Data models
│       ├── schemas.py           # Validation schemas
│       ├── auth.py              # Authentication
│       ├── extensions.py        # Flask extensions
│       ├── templates/           # Jinja2 templates
│       └── utils/
│           └── firebase_helper.py
├── Dockerfile
├── docker-compose.yml
├── config_mapping.json
└── README.md
```

### Running Locally

```bash
# Install dependencies
pip install Flask Flask-WTF Flask-Talisman Flask-Limiter marshmallow firebase-admin

# Set environment variables
export ALPHAFUSION_CREDENTIALS_DIR=/path/to/.credentials
export ALPHAFUSION_CONFIG_MAPPING=/path/to/config_mapping.json

# Run the app
python -m apps.web.app
```

## Security

- **CSRF Protection**: Web UI routes protected, API routes exempt
- **Rate Limiting**: Applied to API endpoints (100 requests/minute per IP)
- **Input Validation**: Marshmallow schemas for all inputs
- **Role-Based Access**: Different permissions for different roles
- **Security Headers**: Flask-Talisman for CSP, HSTS, etc.

## License

Part of the AlphaFusion trading platform.

# alphafusion-issuetracker
# alphafusion-issuetracker
