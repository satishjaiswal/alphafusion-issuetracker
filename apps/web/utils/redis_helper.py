#!/usr/bin/env python3
"""
Redis Helper for Issue Tracker
Stores recent issues in Redis with TTL for fast access
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

try:
    from alphafusion.storage.cache_factory import get_default_cache_client
    from alphafusion.storage.cache_interface import CacheClient
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    CacheClient = None

from apps.web.models import Issue

logger = logging.getLogger(__name__)


class RedisHelper:
    """Helper class for Redis operations - stores recent issues with TTL"""
    
    # Redis key prefixes
    ISSUE_KEY_PREFIX = "issuetracker:issue:"
    ISSUE_LIST_KEY = "issuetracker:issues:recent"  # Sorted set with timestamp as score
    TTL_SECONDS = 3600  # 1 hour
    
    def __init__(self, cache_client=None):
        """
        Initialize Redis helper.
        
        Args:
            cache_client: Optional CacheClient instance. If None, creates default from factory.
        """
        self.cache_client: Optional[CacheClient] = None
        self._initialize(cache_client=cache_client)
    
    def _initialize(self, cache_client=None):
        """Initialize Redis cache client"""
        try:
            if cache_client is not None:
                # Use provided cache client
                from alphafusion.storage.cache_interface import CacheClient
                if isinstance(cache_client, CacheClient):
                    self.cache_client = cache_client
                    if self.cache_client.is_connected():
                        logger.info("Redis helper initialized with provided cache client")
                    else:
                        logger.warning("Provided cache client is not connected")
                        self.cache_client = None
                else:
                    logger.warning(f"Provided cache_client does not implement CacheClient interface. Type: {type(cache_client)}")
                    self.cache_client = None
            elif REDIS_AVAILABLE:
                # Create default cache client
                self.cache_client = get_default_cache_client(use_pool=True)
                if self.cache_client and self.cache_client.is_connected():
                    logger.info("Redis helper initialized successfully")
                else:
                    logger.warning("Redis cache client not connected")
                    self.cache_client = None
            else:
                logger.warning("Redis not available - install alphafusion-core")
                self.cache_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Redis helper: {e}")
            self.cache_client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self.cache_client is not None and self.cache_client.is_connected()
    
    def store_issue(self, issue: Issue) -> bool:
        """
        Store issue in Redis with TTL.
        Also adds to recent issues sorted set.
        
        Args:
            issue: Issue object to store
        
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Store individual issue
            issue_key = f"{self.ISSUE_KEY_PREFIX}{issue.id}"
            issue_dict = issue.to_dict()
            issue_dict['id'] = issue.id
            # Convert datetime objects to ISO format strings for JSON serialization
            for key, value in issue_dict.items():
                if isinstance(value, datetime):
                    issue_dict[key] = value.isoformat()
            issue_json = json.dumps(issue_dict, default=str)
            
            # Store with TTL
            self.cache_client.set(issue_key, issue_json, ttl_seconds=self.TTL_SECONDS)
            
            # Add to recent issues sorted set (score = timestamp)
            # Use negative timestamp so newest issues have highest scores
            timestamp = issue.created_at.timestamp() if issue.created_at else datetime.now().timestamp()
            score = -timestamp  # Negative so newest first
            
            # Add to sorted set
            self.cache_client.zadd(self.ISSUE_LIST_KEY, {issue.id: score})
            
            # Set TTL on sorted set (refresh on each add)
            self.cache_client.expire(self.ISSUE_LIST_KEY, self.TTL_SECONDS)
            
            return True
        except Exception as e:
            logger.error(f"Failed to store issue in Redis: {e}", exc_info=True)
            return False
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """
        Get issue from Redis.
        
        Args:
            issue_id: Issue ID
        
        Returns:
            Issue object or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            issue_key = f"{self.ISSUE_KEY_PREFIX}{issue_id}"
            issue_data = self.cache_client.get(issue_key)
            
            if not issue_data:
                return None
            
            # RedisCacheClient.get() automatically deserializes JSON and returns dict
            # If it's still a string/bytes, parse it manually
            if isinstance(issue_data, dict):
                issue_dict = issue_data
            elif isinstance(issue_data, bytes):
                issue_dict = json.loads(issue_data.decode('utf-8'))
            elif isinstance(issue_data, str):
                issue_dict = json.loads(issue_data)
            else:
                logger.warning(f"Unexpected data type from Redis: {type(issue_data)}")
                return None
            
            # Issue.from_dict expects issue_id as first parameter
            issue_id = issue_dict.pop('id', None)
            if not issue_id:
                return None
            return Issue.from_dict(issue_id, issue_dict)
        except Exception as e:
            logger.error(f"Failed to get issue from Redis: {e}", exc_info=True)
            return None
    
    def list_recent_issues(self, limit: int = 100) -> List[Issue]:
        """
        List recent issues from Redis (sorted by creation time, newest first).
        
        Args:
            limit: Maximum number of issues to return
        
        Returns:
            List of Issue objects
        """
        if not self.is_available():
            return []
        
        try:
            # Get issue IDs from sorted set (highest scores first = newest)
            issue_ids = self.cache_client.zrange(
                self.ISSUE_LIST_KEY,
                0,
                limit - 1,
                withscores=False
            )
            
            if not issue_ids:
                return []
            
            # Decode bytes if needed
            if issue_ids and isinstance(issue_ids[0], bytes):
                issue_ids = [id.decode('utf-8') if isinstance(id, bytes) else id for id in issue_ids]
            
            # Fetch issues
            issues = []
            for issue_id in issue_ids:
                issue = self.get_issue(issue_id)
                if issue:
                    issues.append(issue)
            
            return issues
        except Exception as e:
            logger.error(f"Failed to list recent issues from Redis: {e}", exc_info=True)
            return []
    
    def update_issue(self, issue: Issue) -> bool:
        """
        Update issue in Redis (same as store_issue, but for updates).
        
        Args:
            issue: Updated issue object
        
        Returns:
            True if updated successfully, False otherwise
        """
        return self.store_issue(issue)
    
    def delete_issue(self, issue_id: str) -> bool:
        """
        Delete issue from Redis.
        
        Args:
            issue_id: Issue ID to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Remove from individual storage
            issue_key = f"{self.ISSUE_KEY_PREFIX}{issue_id}"
            self.cache_client.delete(issue_key)
            
            # Note: We don't remove from sorted set as CacheClient doesn't have zrem.
            # The sorted set entry will expire naturally with TTL (1 hour).
            # This is acceptable since we're only tracking recent issues.
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete issue from Redis: {e}", exc_info=True)
            return False

