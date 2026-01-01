# IssueTracker Integration Tests

Integration tests for IssueTracker service, testing real integrations with Kafka and Firebase.

## Prerequisites

Before running integration tests, ensure:

1. **Firebase Credentials**: Configured in `.credentials/integrations/firebase.json`
   - Set `credentials_path` to point to `firebase-admin.json`
   - Set `project_id` to your Firebase project ID

2. **Kafka**: Running and accessible (for Kafka → Firebase workflow tests)
   ```bash
   # If using Docker Compose:
   cd alphafusion-common/container
   docker-compose up -d kafka
   ```

3. **Redis**: Running (optional, for Redis storage tests)
   ```bash
   docker-compose up -d redis
   ```

## Running Integration Tests

### Run All Integration Tests

```bash
cd alphafusion-issuetracker
pytest tests/integration/ -v
```

### Run Specific Test

```bash
# Test Firebase connection only
pytest tests/integration/test_kafka_firebase_integration.py::test_firebase_connection -v

# Test complete Kafka → Firebase workflow
pytest tests/integration/test_kafka_firebase_integration.py::TestKafkaFirebaseWorkflow::test_kafka_firebase_workflow -v

# Test Kafka publish only (doesn't require consumer)
pytest tests/integration/test_kafka_firebase_integration.py::test_kafka_publish_only -v
```

### Skip Integration Tests

To run only unit tests (skip integration tests):

```bash
pytest -m "not integration" -v
```

### Run with Output

To see detailed output during tests:

```bash
pytest tests/integration/ -v -s
```

## Test Files

### `test_kafka_firebase_integration.py`

Tests the complete Kafka → Firebase workflow:

1. **`test_kafka_firebase_workflow`**: Full end-to-end test
   - Publishes issue to Kafka
   - Waits for consumer to process
   - Verifies issue in Firebase
   - Cleans up test issue

2. **`test_firebase_connection`**: Tests Firebase connection independently

3. **`test_kafka_publish_only`**: Tests publishing to Kafka without waiting for consumer

4. **`test_firebase_provider_available`**: Verifies Firebase provider initialization

5. **`test_kafka_consumer_available`**: Verifies Kafka consumer initialization

6. **`test_issue_publisher_available`**: Verifies issue publisher initialization

## Test Fixtures

The tests use pytest fixtures for setup/teardown:

- **`firebase_provider`**: Provides Firebase provider instance
- **`kafka_consumer`**: Provides and manages Kafka consumer lifecycle
- **`issue_publisher`**: Provides issue publisher instance

Fixtures automatically skip tests if dependencies are unavailable.

## Troubleshooting

### Firebase Not Available

```
SKIPPED [1] tests/integration/test_kafka_firebase_integration.py: Firebase provider not available
```

**Solution:**
- Check `.credentials/integrations/firebase.json` exists
- Verify `credentials_path` points to `firebase-admin.json`
- Ensure Firebase credentials file exists and is valid

### Kafka Not Available

```
SKIPPED [1] tests/integration/test_kafka_firebase_integration.py: Kafka consumer not available
```

**Solution:**
- Start Kafka: `docker-compose up -d kafka`
- Check Kafka is accessible on configured port
- Verify Kafka configuration in Consul or environment

### Test Timeout

If `test_kafka_firebase_workflow` times out waiting for issue:

- Check Kafka consumer logs for errors
- Verify consumer is processing messages
- Increase timeout in test if needed (default: 30 seconds)

## Manual Testing

You can also run the standalone script for manual testing:

```bash
cd alphafusion-issuetracker
python scripts/test_kafka_firebase_workflow.py
```

This provides more detailed output and is useful for debugging.

