#!/bin/bash
# Entrypoint script for Issue Tracker container
# Credentials are mounted via volume at /app/.credentials, no copying needed

set -e

# Execute the main command
exec "$@"

