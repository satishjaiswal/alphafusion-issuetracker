# Issue Tracking Data Flow

## Overview

The issue tracking system uses a **Kafka-based event-driven architecture** where services publish issues to Kafka, and the issue tracker service consumes from Kafka to write to Firebase.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICES (alphafusion-core,                  │
│                    alphafusion-workflow, etc.)                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ IssueTrackerClient.log_issue()
                        │ HTTP POST /api/v1/issues
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              ISSUE TRACKER SERVICE (Flask API)                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /api/v1/issues (POST)                                  │   │
│  │  - Receives HTTP request                                │   │
│  │  - Publishes to Kafka topic: alphafusion.issues         │   │
│  │  - Returns 201 with issue ID                            │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          │                                       │
│                          │ publish_issue()                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  IssuePublisher                                          │   │
│  │  - Publishes to Kafka topic: alphafusion.issues          │   │
│  │  - Stores in Redis (for recent issues view)              │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           │ Kafka Message
                           │ Topic: alphafusion.issues
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              KAFKA BROKER                                         │
│              Topic: alphafusion.issues                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Consumer Group: issuetracker-consumer
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              ISSUE TRACKER SERVICE (Kafka Consumer)              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  IssueTrackerConsumer                                    │   │
│  │  - Consumes from Kafka topic: alphafusion.issues         │   │
│  │  - Processes issue messages                              │   │
│  │  - Writes to Firebase                                    │   │
│  │  - Updates Redis cache                                   │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          │                                       │
│                          │ create_issue()                        │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FirebaseHelperProvider                                   │   │
│  │  - Writes issue to Firebase Firestore                     │   │
│  │  - Collection: issues/{id}                                │   │
│  │  - Subcollection: issues/{id}/activities                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  RedisHelperProvider                                      │   │
│  │  - Stores issue in Redis (1-hour TTL)                     │   │
│  │  - Key: issuetracker:issue:{issue_id}                     │   │
│  │  - Sorted Set: issuetracker:issues:recent                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Steps

### Step 1: Service Logs Issue

Services use `IssueTrackerClient` to log issues:

```python
from alphafusion.utils.issue_tracker_client import IssueTrackerClient

client = IssueTrackerClient()
issue_id = client.log_issue(
    title="Trade execution failed",
    description="Failed to execute trade for BTCUSDT",
    type="bug",
    priority="high",
    tags=["trading", "execution"]
)
```

**Location**: `alphafusion-core/src/alphafusion/utils/issue_tracker_client.py`

### Step 2: HTTP Request to Issue Tracker API

`IssueTrackerClient.log_issue()` makes HTTP POST request to:
- **Endpoint**: `http://issuetracker:6001/api/v1/issues`
- **Method**: POST
- **Payload**: JSON with issue details

**Location**: `alphafusion-core/src/alphafusion/utils/issue_tracker_client.py:114`

### Step 3: API Endpoint Publishes to Kafka

The Flask API endpoint receives the request and publishes to Kafka:

```python
# In /api/v1/issues POST handler
from alphafusion.utils.issue_publisher import get_issue_publisher

publisher = get_issue_publisher()
success = publisher.publish_issue(
    title=data["title"],
    description=data["description"],
    type=data["type"],
    priority=data["priority"],
    reporter_id=reporter_id,
    tags=data.get("tags", [])
)
```

**Location**: `alphafusion-issuetracker/apps/web/api.py:48`

**Kafka Topic**: `alphafusion.issues`

**Location**: `alphafusion-core/src/alphafusion/utils/issue_publisher.py:24`

### Step 4: Kafka Consumer Processes Issue

The `IssueTrackerConsumer` runs in a background thread and consumes messages:

```python
# Consumer loop
messages = self.consumer.poll(timeout_ms=1000, max_records=10)
for message in messages:
    self._process_issue(message.value)
    self.consumer.commit()
```

**Location**: `alphafusion-issuetracker/apps/web/kafka_consumer.py:113`

### Step 5: Write to Firebase

The consumer processes the issue and writes to Firebase:

```python
issue = Issue(
    title=issue_data["title"],
    description=issue_data["description"],
    type=IssueType(issue_data["type"]),
    priority=IssuePriority(issue_data["priority"]),
    reporter_id=issue_data["reporter_id"]
)

issue_id = self.firebase_provider.create_issue(issue)
```

**Location**: `alphafusion-issuetracker/apps/web/kafka_consumer.py:178`

**Firebase Collection**: `issues/{issue_id}`

### Step 6: Update Redis Cache

The consumer also stores the issue in Redis for the recent issues view:

```python
if self.redis_provider and self.redis_provider.is_available():
    issue.id = issue_id
    self.redis_provider.store_issue(issue)
```

**Location**: `alphafusion-issuetracker/apps/web/kafka_consumer.py:184`

**Redis Keys**:
- `issuetracker:issue:{issue_id}` - Individual issue (1-hour TTL)
- `issuetracker:issues:recent` - Sorted set of recent issues (1-hour TTL)

## Components

### 1. IssueTrackerClient

**Purpose**: HTTP client for services to log issues

**Location**: `alphafusion-core/src/alphafusion/utils/issue_tracker_client.py`

**Key Methods**:
- `log_issue()` - Log a new issue
- `add_comment()` - Add comment to issue
- `update_issue_status()` - Update issue status

**Non-blocking**: All operations fail gracefully if service is unavailable

### 2. IssuePublisher

**Purpose**: Publishes issues to Kafka and Redis

**Location**: `alphafusion-core/src/alphafusion/utils/issue_publisher.py`

**Key Methods**:
- `publish_issue()` - Publish issue to Kafka and Redis

**Kafka Topic**: `alphafusion.issues`

### 3. IssueTrackerConsumer

**Purpose**: Consumes issues from Kafka and writes to Firebase

**Location**: `alphafusion-issuetracker/apps/web/kafka_consumer.py`

**Key Methods**:
- `start()` - Start consumer in background thread
- `_consume_loop()` - Main consumption loop
- `_process_issue()` - Process issue message and write to Firebase

**Consumer Group**: `issuetracker-consumer`

### 4. FirebaseHelperProvider

**Purpose**: Firebase Firestore operations

**Location**: `alphafusion-issuetracker/apps/web/utils/firebase_helper.py`

**Key Methods**:
- `create_issue()` - Create issue in Firestore
- `get_issue()` - Get issue by ID
- `list_issues()` - List issues with filters
- `update_issue()` - Update issue

**Firebase Collections**:
- `issues/{id}` - Issue documents
- `issues/{id}/activities` - Activity log subcollection
- `issues/{id}/comments` - Comments subcollection

### 5. RedisHelperProvider

**Purpose**: Redis cache operations for recent issues

**Location**: `alphafusion-issuetracker/apps/web/utils/redis_helper.py`

**Key Methods**:
- `store_issue()` - Store issue in Redis
- `list_recent_issues()` - List recent issues from Redis
- `update_issue()` - Update issue in Redis

**Redis Keys**:
- `issuetracker:issue:{issue_id}` - Individual issue (JSON, 1-hour TTL)
- `issuetracker:issues:recent` - Sorted set (score = negative timestamp, 1-hour TTL)

## Service Integration

### Workflow Consumer Service

**Location**: `alphafusion-workflow/src/alphafusion_workflowconsumer/`

**Integration**:
```python
# In DependencyContainer
self._issue_tracker_client = self._create_issue_tracker_client()

# In WorkflowProcessor
if self.issue_tracker_client:
    self.issue_tracker_client.log_issue(
        title="Workflow Error",
        description=str(error),
        type="bug",
        priority="high"
    )
```

### RealTimeTradingWorkflow

**Location**: `alphafusion-core/src/alphafusion/workflows/realtime_trading_workflow.py`

**Integration**:
```python
# In __init__
self.issue_tracker_client = issue_tracker_client

# In exception handler
if self.issue_tracker_client:
    self.issue_tracker_client.log_issue(
        title=f"Workflow Error: {exception_type}",
        description=description,
        type="bug",
        priority=priority
    )
```

## Configuration

### Issue Tracker Service URL

**Config Path**: `services/issuetracker/url`

**Default**: `http://issuetracker:6001`

**Environment Variable**: `ISSUETRACKER_URL`

### Kafka Configuration

**Topic**: `alphafusion.issues`

**Consumer Group**: `issuetracker-consumer`

**Config**: Uses `SecureConfigLoader` or environment variables

### Firebase Configuration

**Credentials**: `.credentials/integrations/firebase.json`

**Config Path**: `integrations/firebase`

### Redis Configuration

**Host**: From `SecureConfigLoader` or environment

**Port**: Default 6379

**Keyspace**: Uses default Redis database (0)

## Troubleshooting

### No Issues Being Logged

1. **Check API Blueprint Registration**
   - Ensure `api_bp` is registered in `register_blueprints()`
   - Check: `alphafusion-issuetracker/apps/web/app.py:196`

2. **Check Kafka Consumer**
   - Verify consumer is started: `start_consumer()` called in `create_app()`
   - Check logs for: "Issue tracker Kafka consumer started"
   - Verify subscription: "Subscribed to Kafka topic: alphafusion.issues"

3. **Check Kafka Connectivity**
   - Verify Kafka broker is running
   - Check topic exists: `alphafusion.issues`
   - Verify producer can publish to topic

4. **Check Service Connectivity**
   - Verify `IssueTrackerClient` can reach issue tracker service
   - Check health endpoint: `GET /api/health`
   - Verify service URL configuration

5. **Check Firebase**
   - Verify Firebase credentials are configured
   - Check Firebase provider is available
   - Verify Firestore permissions

### Issues Not Appearing in Firebase

1. **Check Kafka Consumer Logs**
   - Look for: "Created issue {id} from Kafka"
   - Check for errors in `_process_issue()`

2. **Check Firebase Provider**
   - Verify `firebase_provider.is_available()` returns True
   - Check Firebase credentials

3. **Check Consumer Loop**
   - Verify consumer is polling: Check `_consume_loop()` logs
   - Verify messages are being committed

### Issues Not Appearing in Recent Issues View

1. **Check Redis**
   - Verify Redis provider is available
   - Check Redis connectivity
   - Verify TTL is set correctly (1 hour)

2. **Check Redis Keys**
   - Verify keys are created: `issuetracker:issue:{id}`
   - Check sorted set: `issuetracker:issues:recent`

## Testing

### Test Issue Logging

```python
from alphafusion.utils.issue_tracker_client import IssueTrackerClient

client = IssueTrackerClient()
issue_id = client.log_issue(
    title="Test Issue",
    description="This is a test issue",
    type="bug",
    priority="medium"
)
print(f"Issue ID: {issue_id}")
```

### Test Kafka Publishing

```python
from alphafusion.utils.issue_publisher import get_issue_publisher

publisher = get_issue_publisher()
success = publisher.publish_issue(
    title="Test Issue",
    description="Test description",
    type="bug",
    priority="medium"
)
print(f"Published: {success}")
```

### Check Kafka Topic

```bash
# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Consume from topic
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic alphafusion.issues \
  --from-beginning
```

## Current Status

### ✅ Implemented

- `IssueTrackerClient` - HTTP client for services
- `IssuePublisher` - Kafka publisher
- `IssueTrackerConsumer` - Kafka consumer
- Firebase integration
- Redis caching
- Web UI routes

### ⚠️ Issues Found

1. **API Blueprint Not Registered**
   - The `api_bp` blueprint is defined but not registered
   - This means `/api/v1/issues` endpoint doesn't exist
   - Services calling `IssueTrackerClient.log_issue()` will fail

2. **API Endpoint Writes Directly to Firebase**
   - Current implementation bypasses Kafka
   - Should publish to Kafka instead
   - Consumer should be the only writer to Firebase

### 🔧 Required Fixes

1. Register API blueprint in `register_blueprints()`
2. Modify `/api/v1/issues` endpoint to publish to Kafka instead of writing directly to Firebase
3. Ensure Kafka consumer is the single source of truth for Firebase writes

