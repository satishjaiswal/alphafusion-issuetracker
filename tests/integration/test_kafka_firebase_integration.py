#!/usr/bin/env python3
"""
Integration test for Kafka → Firebase workflow in IssueTracker.

This test verifies the complete flow:
1. Publish an issue to Kafka
2. Kafka consumer picks up the message
3. Issue is written to Firebase
4. Issue can be retrieved from Firebase

Usage:
    pytest tests/integration/test_kafka_firebase_integration.py -v
    pytest tests/integration/test_kafka_firebase_integration.py -v -s  # With output
    pytest tests/integration/test_kafka_firebase_integration.py::test_kafka_firebase_workflow -v
"""

import pytest
import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Set environment variables for Firebase BEFORE any imports
# Assume tests are run from alphafusion-issuetracker/ directory
issuetracker_root = Path(__file__).resolve().parent.parent.parent
project_root = issuetracker_root.parent

if not os.getenv('FIREBASE_CREDENTIALS_PATH'):
    cred_path = project_root / ".credentials" / "integrations" / "firebase-admin.json"
    if cred_path.exists():
        os.environ['FIREBASE_CREDENTIALS_PATH'] = str(cred_path.resolve())

if not os.getenv('FIREBASE_PROJECT_ID'):
    firebase_json = project_root / ".credentials" / "integrations" / "firebase.json"
    if firebase_json.exists():
        try:
            with open(firebase_json) as f:
                config = json.load(f)
                project_id = config.get('project_id') or config.get('projectId')
                if project_id:
                    os.environ['FIREBASE_PROJECT_ID'] = project_id
        except Exception:
            pass

# Add paths
sys.path.insert(0, str(issuetracker_root))
sys.path.insert(0, str(issuetracker_root / "apps"))
sys.path.insert(0, str(project_root / "alphafusion-core" / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def firebase_provider():
    """Fixture to provide Firebase provider."""
    from apps.web.utils.provider_factory import IssueTrackerProviderFactory
    provider = IssueTrackerProviderFactory.create_firebase_helper_provider()
    
    if not provider or not provider.is_available():
        pytest.skip("Firebase provider not available - ensure credentials are configured")
    
    return provider


@pytest.fixture(scope="function")
def kafka_consumer():
    """Fixture to provide Kafka consumer."""
    from apps.web.kafka_consumer import IssueTrackerConsumer
    consumer = IssueTrackerConsumer()
    
    if not consumer or not consumer.consumer:
        pytest.skip("Kafka consumer not available - ensure Kafka is running")
    
    # Start consumer
    consumer.start()
    time.sleep(2)  # Give consumer time to connect
    
    yield consumer
    
    # Cleanup
    consumer.stop()


@pytest.fixture(scope="function")
def issue_publisher():
    """Fixture to provide issue publisher."""
    from alphafusion.utils.issue_publisher import IssuePublisher
    publisher = IssuePublisher()
    
    if not publisher.is_available():
        pytest.skip("Issue publisher not available (Kafka or Redis not connected)")
    
    return publisher


@pytest.mark.integration
class TestKafkaFirebaseWorkflow:
    """Integration tests for Kafka → Firebase workflow."""
    
    def test_kafka_firebase_workflow(
        self,
        firebase_provider,
        kafka_consumer,
        issue_publisher
    ):
        """
        Test complete Kafka → Firebase workflow.
        
        This test:
        1. Publishes an issue to Kafka
        2. Waits for consumer to process it
        3. Verifies issue is written to Firebase
        4. Verifies issue details
        5. Cleans up test issue
        """
        test_issue_id = None
        
        try:
            # Step 1: Publish test issue to Kafka
            test_title = f"Integration Test Issue - {datetime.now().isoformat()}"
            test_description = f"""
This is an automated integration test issue to verify the Kafka → Firebase workflow.

Test Details:
- Published at: {datetime.now().isoformat()}
- Test ID: test_{int(time.time())}
- Purpose: Verify Kafka consumer picks up messages and writes to Firebase
            """
            
            success = issue_publisher.publish_issue(
                title=test_title,
                description=test_description,
                type="bug",
                priority="medium",
                reporter_id="integration_test",
                tags=["integration-test", "kafka", "firebase"],
                component="issuetracker",
                context={
                    "test": True,
                    "test_timestamp": datetime.now().isoformat()
                }
            )
            
            assert success, "Failed to publish issue to Kafka"
            logger.info(f"✓ Published test issue to Kafka: {test_title[:50]}...")
            
            # Step 2: Wait for consumer to process issue
            logger.info("Waiting for Kafka consumer to process issue...")
            start_time = time.time()
            max_wait = 30
            issue_id = None
            
            while time.time() - start_time < max_wait:
                try:
                    issues = firebase_provider.list_issues(limit=50)
                    
                    for issue in issues:
                        if issue.title == test_title:
                            issue_id = issue.id
                            test_issue_id = issue_id
                            break
                    
                    if issue_id:
                        break
                    
                    if not kafka_consumer.running:
                        pytest.fail("Consumer stopped running")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Error checking for issue: {e}")
                    time.sleep(1)
            
            assert issue_id is not None, f"Issue not found in Firebase after {max_wait} seconds"
            logger.info(f"✓ Found issue in Firebase: {issue_id}")
            
            # Step 3: Verify issue details
            issue = firebase_provider.get_issue(issue_id)
            assert issue is not None, f"Issue {issue_id} not found in Firebase"
            
            logger.info("✓ Issue retrieved from Firebase")
            logger.info(f"  ID: {issue.id}")
            logger.info(f"  Title: {issue.title}")
            logger.info(f"  Type: {issue.type.value}")
            logger.info(f"  Priority: {issue.priority.value}")
            logger.info(f"  Reporter: {issue.reporter_id}")
            logger.info(f"  Tags: {issue.tags}")
            logger.info(f"  Status: {issue.status.value}")
            
            # Verify it's our test issue
            assert "Integration Test Issue" in issue.title, "Issue title doesn't match"
            assert "integration-test" in issue.tags, "Test tag not found"
            assert issue.reporter_id == "integration_test", f"Reporter ID mismatch: {issue.reporter_id}"
            assert issue.type.value == "bug", f"Type mismatch: {issue.type.value}"
            assert issue.priority.value == "medium", f"Priority mismatch: {issue.priority.value}"
            
            logger.info("✓ All assertions passed - workflow verified!")
            
        finally:
            # Cleanup: Delete test issue
            if test_issue_id:
                try:
                    firebase_provider.delete_issue(test_issue_id)
                    logger.info(f"✓ Cleaned up test issue {test_issue_id}")
                except Exception as e:
                    logger.warning(f"⚠ Failed to delete test issue: {e}")
    
    def test_firebase_provider_available(self, firebase_provider):
        """Test that Firebase provider is available."""
        assert firebase_provider is not None
        assert firebase_provider.is_available()
    
    def test_kafka_consumer_available(self, kafka_consumer):
        """Test that Kafka consumer is available."""
        assert kafka_consumer is not None
        assert kafka_consumer.consumer is not None
        assert kafka_consumer.running
    
    def test_issue_publisher_available(self, issue_publisher):
        """Test that issue publisher is available."""
        assert issue_publisher is not None
        assert issue_publisher.is_available()


@pytest.mark.integration
def test_firebase_connection(firebase_provider):
    """Test Firebase connection independently."""
    assert firebase_provider is not None
    assert firebase_provider.is_available()
    
    # Try to list issues (should not fail)
    issues = firebase_provider.list_issues(limit=10)
    assert isinstance(issues, list)


@pytest.mark.integration
def test_kafka_publish_only(issue_publisher):
    """Test publishing to Kafka without waiting for consumer."""
    test_title = f"Test Publish Only - {datetime.now().isoformat()}"
    
    success = issue_publisher.publish_issue(
        title=test_title,
        description="Test publish only",
        type="bug",
        priority="low",
        reporter_id="test",
        tags=["test"]
    )
    
    assert success, "Failed to publish issue to Kafka"
