#!/usr/bin/env python3
"""
Kafka consumer for issue tracker - listens to issues topic and writes to Firebase.
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Kafka topic for issues
ISSUES_TOPIC = "alphafusion.issues"


class IssueTrackerConsumer:
    """
    Kafka consumer that listens to issues topic and writes to Firebase.
    
    Runs in a background thread and processes issues as they arrive.
    
    Uses Provider Pattern for dependency injection of Firebase and Redis providers.
    """
    
    def __init__(
        self,
        queue_consumer=None,
        cache_client=None,
        firebase_provider=None,
        redis_provider=None
    ):
        """
        Initialize Kafka consumer.
        
        Args:
            queue_consumer: Optional QueueConsumer instance. If None, creates default from factory.
            cache_client: Optional CacheClient instance. If None, RedisHelper creates default.
            firebase_provider: Optional FirebaseHelperProvider instance. If None, creates default.
            redis_provider: Optional RedisHelperProvider instance. If None, creates default.
        """
        self.consumer = queue_consumer
        self.firebase_provider = firebase_provider
        self.redis_provider = redis_provider
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._initialize(cache_client=cache_client)
    
    def _initialize(self, cache_client=None):
        """Initialize consumer and providers"""
        try:
            # Initialize providers if not provided
            if self.firebase_provider is None:
                from apps.web.utils.provider_factory import IssueTrackerProviderFactory
                self.firebase_provider = IssueTrackerProviderFactory.create_firebase_helper_provider()
            
            if self.redis_provider is None:
                from apps.web.utils.provider_factory import IssueTrackerProviderFactory
                self.redis_provider = IssueTrackerProviderFactory.create_redis_helper_provider(
                    cache_client=cache_client
                )
            
            # Initialize Kafka consumer if not provided
            if self.consumer is None:
                from alphafusion.storage.queue_factory import create_queue_consumer
                self.consumer = create_queue_consumer()
            
            if not self.consumer or not self.consumer.is_connected():
                logger.warning("Kafka consumer not available - issue tracking will not work")
                self.consumer = None
                return
            
            # Subscribe to issues topic
            if self.consumer.subscribe([ISSUES_TOPIC], group_id="issuetracker-consumer"):
                logger.info(f"Subscribed to Kafka topic: {ISSUES_TOPIC}")
            else:
                logger.error("Failed to subscribe to issues topic")
                self.consumer = None
        
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}", exc_info=True)
            self.consumer = None
    
    def start(self):
        """Start the consumer in a background thread"""
        if not self.consumer:
            logger.warning("Kafka consumer not available, cannot start")
            return
        
        if self.running:
            logger.warning("Consumer already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.thread.start()
        logger.info("Issue tracker Kafka consumer started")
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                logger.warning(f"Error closing consumer: {e}")
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Issue tracker Kafka consumer stopped")
    
    def _consume_loop(self):
        """Main consumption loop"""
        logger.info("Starting issue consumption loop")
        
        while self.running:
            try:
                # Poll for messages (timeout: 1 second)
                messages = self.consumer.poll(timeout_ms=1000, max_records=10)
                
                if messages:
                    for message in messages:
                        try:
                            self._process_issue(message.value)
                            # Commit after processing
                            self.consumer.commit()
                        except Exception as e:
                            logger.error(f"Error processing issue message: {e}", exc_info=True)
                            # Still commit to avoid reprocessing bad messages
                            self.consumer.commit()
                
                # Small sleep to avoid busy waiting
                time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in consumption loop: {e}", exc_info=True)
                time.sleep(1)  # Wait before retrying
    
    def _process_issue(self, issue_data: dict):
        """
        Process an issue message from Kafka and write to Firebase.
        
        This is the single point where issues are written to Firebase.
        All issues (from web UI or services) go through this flow.
        
        Args:
            issue_data: Issue data dictionary from Kafka message
        """
        if not self.firebase_provider or not self.firebase_provider.is_available():
            logger.warning("Firebase provider not available, cannot process issue")
            return
        
        try:
            from apps.web.models import Issue, IssueStatus, IssuePriority, IssueType
            
            # Parse issue data
            title = issue_data.get("title", "Untitled Issue")
            description = issue_data.get("description", "")
            issue_type = IssueType(issue_data.get("type", "bug"))
            priority = IssuePriority(issue_data.get("priority", "medium"))
            reporter_id = issue_data.get("reporter_id", "system")
            assignee_id = issue_data.get("assignee_id")
            tags = issue_data.get("tags", [])
            
            # Create issue model
            issue = Issue(
                title=title,
                description=description,
                type=issue_type,
                priority=priority,
                reporter_id=reporter_id,
                assignee_id=assignee_id,
                tags=tags
            )
            
            # Create issue in Firebase
            issue_id = self.firebase_provider.create_issue(issue)
            
            if issue_id:
                logger.info(f"Created issue {issue_id} from Kafka: {title[:50]}")
                
                # Store in Redis if available
                if self.redis_provider and self.redis_provider.is_available():
                    issue.id = issue_id
                    self.redis_provider.store_issue(issue)
            else:
                logger.error(f"Failed to create issue in Firebase: {title[:50]}")
        
        except Exception as e:
            logger.error(f"Error processing issue: {e}", exc_info=True)


# Global consumer instance
_consumer_instance: Optional[IssueTrackerConsumer] = None


def get_consumer() -> Optional[IssueTrackerConsumer]:
    """Get global consumer instance"""
    return _consumer_instance


def start_consumer(
    queue_consumer=None,
    cache_client=None,
    firebase_provider=None,
    redis_provider=None
):
    """
    Start the global consumer.
    
    Args:
        queue_consumer: Optional QueueConsumer instance. If None, creates default from factory.
        cache_client: Optional CacheClient instance. If None, RedisHelper creates default.
        firebase_provider: Optional FirebaseHelperProvider instance. If None, creates default.
        redis_provider: Optional RedisHelperProvider instance. If None, creates default.
    """
    global _consumer_instance
    if _consumer_instance is None:
        _consumer_instance = IssueTrackerConsumer(
            queue_consumer=queue_consumer,
            cache_client=cache_client,
            firebase_provider=firebase_provider,
            redis_provider=redis_provider
        )
        _consumer_instance.start()
    return _consumer_instance


def stop_consumer():
    """Stop the global consumer"""
    global _consumer_instance
    if _consumer_instance:
        _consumer_instance.stop()
        _consumer_instance = None

