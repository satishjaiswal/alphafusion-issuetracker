#!/bin/bash
# Entrypoint script for Issue Tracker container
# Credentials are now in container filesystem (encrypted), not mounted

set -e

# Disable core dumps for security (prevents credential exposure in core files)
ulimit -c 0

# Execute the main command
exec "$@"

