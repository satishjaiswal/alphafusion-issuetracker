#!/usr/bin/env python3
"""
Pytest configuration and fixtures for alphafusion-issuetracker tests.
"""

import sys
from pathlib import Path

# Add apps directory to Python path
project_root = Path(__file__).parent.parent
apps_dir = project_root / "apps"
if str(apps_dir) not in sys.path:
    sys.path.insert(0, str(apps_dir))

