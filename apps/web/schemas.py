#!/usr/bin/env python3
"""
Input validation schemas for Issue Tracker API endpoints using Marshmallow.
"""

from marshmallow import Schema, fields, validate, ValidationError


class IssueCreateSchema(Schema):
    """Schema for creating a new issue"""
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200),
        error_messages={"required": "Title is required", "invalid": "Title must be a string"}
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10000),
        error_messages={"required": "Description is required", "invalid": "Description must be a string"}
    )
    status = fields.Str(
        validate=validate.OneOf(["open", "in-progress", "resolved", "closed"]),
        load_default="open",
        allow_none=False
    )
    priority = fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"]),
        load_default="medium",
        allow_none=False
    )
    type = fields.Str(
        validate=validate.OneOf(["bug", "feature", "task", "enhancement"]),
        load_default="task",
        allow_none=False
    )
    reporter_id = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={"required": "Reporter ID is required"}
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    tags = fields.List(
        fields.Str(validate=validate.Length(min=1, max=50)),
        load_default=[],
        allow_none=False
    )


class IssueUpdateSchema(Schema):
    """Schema for updating an issue"""
    title = fields.Str(
        validate=validate.Length(min=1, max=200),
        allow_none=True
    )
    description = fields.Str(
        validate=validate.Length(min=1, max=10000),
        allow_none=True
    )
    status = fields.Str(
        validate=validate.OneOf(["open", "in-progress", "resolved", "closed"]),
        allow_none=True
    )
    priority = fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"]),
        allow_none=True
    )
    type = fields.Str(
        validate=validate.OneOf(["bug", "feature", "task", "enhancement"]),
        allow_none=True
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True
    )
    tags = fields.List(
        fields.Str(validate=validate.Length(min=1, max=50)),
        allow_none=True
    )


class CommentCreateSchema(Schema):
    """Schema for creating a comment"""
    content = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=5000),
        error_messages={"required": "Comment content is required", "invalid": "Content must be a string"}
    )
    author_id = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={"required": "Author ID is required"}
    )


class IssueQuerySchema(Schema):
    """Schema for querying issues"""
    status = fields.Str(
        validate=validate.OneOf(["open", "in-progress", "resolved", "closed"]),
        allow_none=True,
        load_default=None
    )
    priority = fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"]),
        allow_none=True,
        load_default=None
    )
    type = fields.Str(
        validate=validate.OneOf(["bug", "feature", "task", "enhancement"]),
        allow_none=True,
        load_default=None
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    reporter_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    limit = fields.Int(
        validate=validate.Range(min=1, max=1000),
        load_default=100,
        allow_none=False
    )


class IssuePathSchema(Schema):
    """Schema for issue ID path parameter"""
    issue_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        required=True
    )


class UserCreateSchema(Schema):
    """Schema for creating a user"""
    uid = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={"required": "UID is required"}
    )
    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required", "invalid": "Invalid email format"}
    )
    display_name = fields.Str(
        validate=validate.Length(min=1, max=200),
        allow_none=True,
        load_default=None
    )
    photo_url = fields.Str(
        validate=validate.URL(),
        allow_none=True,
        load_default=None
    )
    role = fields.Str(
        validate=validate.OneOf(["admin", "developer", "tester", "viewer", "service"]),
        load_default="viewer",
        allow_none=False
    )


class UserUpdateSchema(Schema):
    """Schema for updating a user"""
    display_name = fields.Str(
        validate=validate.Length(min=1, max=200),
        allow_none=True
    )
    photo_url = fields.Str(
        validate=validate.URL(),
        allow_none=True
    )
    role = fields.Str(
        validate=validate.OneOf(["admin", "developer", "tester", "viewer", "service"]),
        allow_none=True
    )


class BacklogCreateSchema(Schema):
    """Schema for creating a new backlog item"""
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200),
        error_messages={"required": "Title is required", "invalid": "Title must be a string"}
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10000),
        error_messages={"required": "Description is required", "invalid": "Description must be a string"}
    )
    category = fields.Str(
        validate=validate.OneOf(["feature-request", "suggestions", "improvement", "must-have", "critical"]),
        load_default="feature-request",
        allow_none=False
    )
    reporter_id = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={"required": "Reporter ID is required"}
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    tags = fields.List(
        fields.Str(validate=validate.Length(min=1, max=50)),
        load_default=[],
        allow_none=False
    )


class BacklogUpdateSchema(Schema):
    """Schema for updating a backlog item"""
    title = fields.Str(
        validate=validate.Length(min=1, max=200),
        allow_none=True
    )
    description = fields.Str(
        validate=validate.Length(min=1, max=10000),
        allow_none=True
    )
    category = fields.Str(
        validate=validate.OneOf(["feature-request", "suggestions", "improvement", "must-have", "critical"]),
        allow_none=True
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True
    )
    tags = fields.List(
        fields.Str(validate=validate.Length(min=1, max=50)),
        allow_none=True
    )


class BacklogQuerySchema(Schema):
    """Schema for querying backlog items"""
    category = fields.Str(
        validate=validate.OneOf(["feature-request", "suggestions", "improvement", "must-have", "critical"]),
        allow_none=True,
        load_default=None
    )
    assignee_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    reporter_id = fields.Str(
        validate=validate.Length(min=1, max=100),
        allow_none=True,
        load_default=None
    )
    limit = fields.Int(
        validate=validate.Range(min=1, max=1000),
        load_default=100,
        allow_none=False
    )


def validate_query_params(schema_class, data):
    """Validate query parameters using a schema"""
    schema = schema_class()
    try:
        return schema.load(data)
    except ValidationError as err:
        raise ValueError(f"Validation error: {err.messages}")


def validate_path_params(schema_class, data):
    """Validate path parameters using a schema"""
    schema = schema_class()
    try:
        return schema.load(data)
    except ValidationError as err:
        raise ValueError(f"Validation error: {err.messages}")


def validate_json_body(schema_class, data):
    """Validate JSON body using a schema"""
    schema = schema_class()
    try:
        return schema.load(data)
    except ValidationError as err:
        raise ValueError(f"Validation error: {err.messages}")

