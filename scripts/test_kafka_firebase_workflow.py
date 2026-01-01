#!/usr/bin/env python3
"""
Standalone integration test script for Kafka → Firebase workflow.

This script tests the complete flow:
1. Publishes an issue to Kafka
2. Starts Kafka consumer to process the message
3. Verifies issue is written to Firebase
4. Cleans up test issue

Usage:
    cd alphafusion-issuetracker
    python scripts/test_kafka_firebase_workflow.py
"""

import sys
import os
import time
import logging
import json
from pathlib import Path
from datetime import datetime

# Set environment variables for Firebase BEFORE any imports
# Assume script is run from alphafusion-issuetracker/ directory
# Project root (alphafusion/) is parent of issuetracker
issuetracker_root = Path.cwd()
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

# Add project root to path
sys.path.insert(0, str(issuetracker_root))
sys.path.insert(0, str(issuetracker_root / "apps"))
sys.path.insert(0, str(project_root / "alphafusion-core" / "src"))  # For alphafusion imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the integration test"""
    print("=" * 70)
    print("Kafka → Firebase Integration Test")
    print("=" * 70)
    print()
    
    test_issue_id = None
    consumer = None
    
    # Show environment setup
    if os.getenv('FIREBASE_CREDENTIALS_PATH'):
        print(f"✓ Using FIREBASE_CREDENTIALS_PATH: {os.getenv('FIREBASE_CREDENTIALS_PATH')}")
    if os.getenv('FIREBASE_PROJECT_ID'):
        print(f"✓ Using FIREBASE_PROJECT_ID: {os.getenv('FIREBASE_PROJECT_ID')}")
    print()
    
    try:
        # Step 1: Initialize Firebase provider
        print("Step 1: Initializing Firebase provider...")
        try:
            from apps.web.utils.provider_factory import IssueTrackerProviderFactory
            firebase_provider = IssueTrackerProviderFactory.create_firebase_helper_provider()
            
            if not firebase_provider or not firebase_provider.is_available():
                print("❌ ERROR: Firebase provider not available")
                print("   Ensure Firebase credentials are configured in .credentials/integrations/firebase.json")
                return 1
            
            print("✓ Firebase provider initialized")
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize Firebase provider: {e}")
            return 1
        
        # Step 2: Initialize and start Kafka consumer
        print("\nStep 2: Initializing Kafka consumer...")
        try:
            from apps.web.kafka_consumer import IssueTrackerConsumer
            consumer = IssueTrackerConsumer()
            
            if not consumer or not consumer.consumer:
                print("❌ ERROR: Kafka consumer not available")
                print("   Ensure Kafka is running and accessible")
                return 1
            
            print("✓ Kafka consumer initialized")
            
            # Start consumer
            consumer.start()
            print("✓ Kafka consumer started")
            time.sleep(2)  # Give consumer time to connect
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize/start Kafka consumer: {e}")
            return 1
        
        # Step 3: Publish test issue to Kafka
        print("\nStep 3: Publishing test issue to Kafka...")
        try:
            from alphafusion.utils.issue_publisher import IssuePublisher
            
            publisher = IssuePublisher()
            
            if not publisher.is_available():
                print("❌ ERROR: Issue publisher not available (Kafka or Redis not connected)")
                return 1
            
            # Create test issue
            test_title = f"Integration Test Issue - {datetime.now().isoformat()}"
            test_description = f"""
This is an automated integration test issue to verify the Kafka → Firebase workflow.

Test Details:
- Published at: {datetime.now().isoformat()}
- Test ID: test_{int(time.time())}
- Purpose: Verify Kafka consumer picks up messages and writes to Firebase
            """
            
            # Publish issue
            success = publisher.publish_issue(
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
            
            if not success:
                print("❌ ERROR: Failed to publish issue to Kafka")
                return 1
            
            print(f"✓ Published test issue to Kafka: {test_title[:50]}...")
        except Exception as e:
            print(f"❌ ERROR: Failed to publish issue: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Step 4: Wait for consumer to process issue
        print("\nStep 4: Waiting for Kafka consumer to process issue...")
        print("(This may take up to 30 seconds)")
        
        start_time = time.time()
        max_wait = 30
        issue_id = None
        
        while time.time() - start_time < max_wait:
            try:
                # Try to find the issue in Firebase by title
                issues = firebase_provider.list_issues(limit=50)
                
                for issue in issues:
                    if issue.title == test_title:
                        issue_id = issue.id
                        test_issue_id = issue_id
                        break
                
                if issue_id:
                    break
                
                if not consumer.running:
                    print("⚠ WARNING: Consumer stopped running")
                    break
                
                time.sleep(1)
                print(".", end="", flush=True)
                
            except Exception as e:
                logger.debug(f"Error checking for issue: {e}")
                time.sleep(1)
        
        print()  # New line after dots
        
        if not issue_id:
            print(f"❌ ERROR: Issue not found in Firebase after {max_wait} seconds")
            print("   The consumer may not have processed the message yet.")
            print("   Check Kafka consumer logs for errors.")
            return 1
        
        print(f"✓ Found issue in Firebase: {issue_id}")
        
        # Step 5: Verify issue details
        print("\nStep 5: Verifying issue details in Firebase...")
        try:
            issue = firebase_provider.get_issue(issue_id)
            
            if not issue:
                print(f"❌ ERROR: Issue {issue_id} not found in Firebase")
                return 1
            
            print("✓ Issue retrieved from Firebase")
            print(f"  ID: {issue.id}")
            print(f"  Title: {issue.title}")
            print(f"  Type: {issue.type.value}")
            print(f"  Priority: {issue.priority.value}")
            print(f"  Reporter: {issue.reporter_id}")
            print(f"  Tags: {issue.tags}")
            print(f"  Status: {issue.status.value}")
            print(f"  Created: {issue.created_at}")
            
            # Verify it's our test issue
            if "Integration Test Issue" not in issue.title:
                print("⚠ WARNING: Issue title doesn't match expected test pattern")
            
            if "integration-test" not in issue.tags:
                print("⚠ WARNING: Test tag not found in issue tags")
            
            print("✓ Issue verification complete")
        except Exception as e:
            print(f"❌ ERROR: Failed to verify issue: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Step 6: Cleanup
        print("\nStep 6: Cleaning up test issue...")
        if test_issue_id:
            try:
                success = firebase_provider.delete_issue(test_issue_id)
                if success:
                    print(f"✓ Deleted test issue {test_issue_id}")
                else:
                    print(f"⚠ WARNING: Failed to delete test issue {test_issue_id}")
            except Exception as e:
                print(f"⚠ WARNING: Error deleting test issue: {e}")
        
        if consumer:
            try:
                consumer.stop()
                print("✓ Stopped Kafka consumer")
            except Exception as e:
                print(f"⚠ WARNING: Error stopping consumer: {e}")
        
        # Success!
        print("\n" + "=" * 70)
        print("✅ Integration test PASSED!")
        print("=" * 70)
        print("Summary:")
        print("  ✓ Issue published to Kafka")
        print("  ✓ Kafka consumer processed the message")
        print("  ✓ Issue written to Firebase")
        print("  ✓ Issue verified in Firebase")
        print("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup on exit
        if test_issue_id and 'firebase_provider' in locals():
            try:
                firebase_provider.delete_issue(test_issue_id)
            except:
                pass
        if consumer:
            try:
                consumer.stop()
            except:
                pass


if __name__ == "__main__":
    sys.exit(main())

