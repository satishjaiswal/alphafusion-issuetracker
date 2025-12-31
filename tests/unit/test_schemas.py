#!/usr/bin/env python3
"""
Unit tests for validation schemas.
"""

import pytest
from marshmallow import ValidationError
from apps.web.schemas import (
    IssueCreateSchema, IssueUpdateSchema, CommentCreateSchema,
    IssueQuerySchema, IssuePathSchema, UserCreateSchema,
    validate_json_body, validate_path_params, validate_query_params
)


class TestIssueCreateSchema:
    """Tests for IssueCreateSchema."""
    
    def test_valid_issue_data(self):
        """Test validating valid issue data."""
        schema = IssueCreateSchema()
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "type": "bug",
            "priority": "high",
            "reporter_id": "user1",
            "tags": ["bug", "critical"]
        }
        
        result = schema.load(data)
        
        assert result["title"] == "Test Issue"
        assert result["description"] == "Test description"
        assert result["type"] == "bug"
        assert result["priority"] == "high"
        assert result["reporter_id"] == "user1"
        assert len(result["tags"]) == 2
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        schema = IssueCreateSchema()
        data = {
            "description": "Test description"
            # Missing title and reporter_id
        }
        
        with pytest.raises(ValidationError):
            schema.load(data)
    
    def test_invalid_status(self):
        """Test validation with invalid status."""
        schema = IssueCreateSchema()
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1",
            "status": "invalid_status"
        }
        
        with pytest.raises(ValidationError):
            schema.load(data)
    
    def test_default_values(self):
        """Test that default values are applied."""
        schema = IssueCreateSchema()
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1"
        }
        
        result = schema.load(data)
        
        assert result["status"] == "open"
        assert result["priority"] == "medium"
        assert result["type"] == "task"
        assert result["tags"] == []


class TestIssueUpdateSchema:
    """Tests for IssueUpdateSchema."""
    
    def test_partial_update(self):
        """Test partial update (all fields optional)."""
        schema = IssueUpdateSchema()
        data = {
            "status": "in-progress"
        }
        
        result = schema.load(data)
        
        assert result["status"] == "in-progress"
        assert "title" not in result
    
    def test_empty_update(self):
        """Test empty update (should be valid)."""
        schema = IssueUpdateSchema()
        data = {}
        
        result = schema.load(data)
        
        assert result == {}


class TestCommentCreateSchema:
    """Tests for CommentCreateSchema."""
    
    def test_valid_comment_data(self):
        """Test validating valid comment data."""
        schema = CommentCreateSchema()
        data = {
            "content": "Test comment",
            "author_id": "user1"
        }
        
        result = schema.load(data)
        
        assert result["content"] == "Test comment"
        assert result["author_id"] == "user1"
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        schema = CommentCreateSchema()
        data = {
            "author_id": "user1"
            # Missing content
        }
        
        with pytest.raises(ValidationError):
            schema.load(data)


class TestIssueQuerySchema:
    """Tests for IssueQuerySchema."""
    
    def test_valid_query_params(self):
        """Test validating valid query parameters."""
        schema = IssueQuerySchema()
        data = {
            "status": "open",
            "priority": "high",
            "type": "bug",
            "limit": 50
        }
        
        result = schema.load(data)
        
        assert result["status"] == "open"
        assert result["priority"] == "high"
        assert result["type"] == "bug"
        assert result["limit"] == 50
    
    def test_default_limit(self):
        """Test that default limit is applied."""
        schema = IssueQuerySchema()
        data = {}
        
        result = schema.load(data)
        
        assert result["limit"] == 100


class TestValidationHelpers:
    """Tests for validation helper functions."""
    
    def test_validate_json_body_success(self):
        """Test successful JSON body validation."""
        data = {
            "title": "Test Issue",
            "description": "Test description",
            "reporter_id": "user1"
        }
        
        result = validate_json_body(IssueCreateSchema, data)
        
        assert result["title"] == "Test Issue"
    
    def test_validate_json_body_failure(self):
        """Test JSON body validation failure."""
        data = {
            "description": "Test description"
            # Missing required fields
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_json_body(IssueCreateSchema, data)
        
        assert "Validation error" in str(exc_info.value)
    
    def test_validate_path_params_success(self):
        """Test successful path parameter validation."""
        data = {"issue_id": "test-123"}
        
        result = validate_path_params(IssuePathSchema, data)
        
        assert result["issue_id"] == "test-123"
    
    def test_validate_path_params_failure(self):
        """Test path parameter validation failure."""
        data = {"issue_id": ""}  # Empty string
        
        with pytest.raises(ValueError):
            validate_path_params(IssuePathSchema, data)
    
    def test_validate_query_params_success(self):
        """Test successful query parameter validation."""
        data = {
            "status": "open",
            "limit": 50
        }
        
        result = validate_query_params(IssueQuerySchema, data)
        
        assert result["status"] == "open"
        assert result["limit"] == 50

