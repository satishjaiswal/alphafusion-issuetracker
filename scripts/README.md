# IssueTracker Scripts

## Kafka → Firebase Integration Test

### `test_kafka_firebase_workflow.py`

Tests the complete workflow of publishing an issue to Kafka and verifying it gets written to Firebase.

**What it tests:**
1. ✅ Publishes a test issue to Kafka topic `alphafusion.issues`
2. ✅ Starts Kafka consumer to process the message
3. ✅ Verifies the issue is written to Firebase Firestore
4. ✅ Verifies issue details match what was published
5. ✅ Cleans up the test issue

**Prerequisites:**
- Kafka must be running and accessible
- Firebase credentials must be configured in `.credentials/integrations/firebase.json`
- Redis must be running (optional, for Redis storage)

**Usage:**

```bash
# From project root
cd alphafusion-issuetracker
python scripts/test_kafka_firebase_workflow.py

# Or from alphafusion root
python -m alphafusion_issuetracker.scripts.test_kafka_firebase_workflow
```

**Expected Output:**

```
======================================================================
Kafka → Firebase Integration Test
======================================================================

Step 1: Initializing Firebase provider...
✓ Firebase provider initialized

Step 2: Initializing Kafka consumer...
✓ Kafka consumer initialized
✓ Kafka consumer started

Step 3: Publishing test issue to Kafka...
✓ Published test issue to Kafka: Integration Test Issue - 2026-01-01T15:...

Step 4: Waiting for Kafka consumer to process issue...
(This may take up to 30 seconds)
✓ Found issue in Firebase: abc123xyz

Step 5: Verifying issue details in Firebase...
✓ Issue retrieved from Firebase
  ID: abc123xyz
  Title: Integration Test Issue - 2026-01-01T15:...
  Type: bug
  Priority: medium
  Reporter: integration_test
  Tags: ['integration-test', 'kafka', 'firebase']
  Status: open
  Created: 2026-01-01 15:30:45
✓ Issue verification complete

Step 6: Cleaning up test issue...
✓ Deleted test issue abc123xyz
✓ Stopped Kafka consumer

======================================================================
✅ Integration test PASSED!
======================================================================
Summary:
  ✓ Issue published to Kafka
  ✓ Kafka consumer processed the message
  ✓ Issue written to Firebase
  ✓ Issue verified in Firebase
======================================================================
```

**Troubleshooting:**

1. **Firebase provider not available**
   - Check that `.credentials/integrations/firebase.json` exists
   - Verify `credentials_path` points to `firebase-admin.json`
   - Run `python alphafusion-tools/scripts/test_firebase_connection.py` to test Firebase

2. **Kafka consumer not available**
   - Ensure Kafka is running: `docker-compose ps` (if using Docker)
   - Check Kafka connection settings in Consul or environment variables
   - Verify Kafka topic `alphafusion.issues` exists

3. **Issue not found in Firebase**
   - Check Kafka consumer logs for errors
   - Verify consumer is processing messages
   - Increase wait time in script if needed

4. **Import errors**
   - Ensure you're running from the correct directory
   - Check that all dependencies are installed: `pip install -e .`
   - Verify Python path includes project root

