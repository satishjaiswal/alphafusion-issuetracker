#!/usr/bin/env python3
"""
Flask extensions initialization
"""

from flask import request
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Use standard CSRFProtect - we'll exempt the API blueprint properly
# No need for custom class when using csrf.exempt()


# Initialize extensions (without app)
csrf = CSRFProtect()
talisman = Talisman()
limiter = Limiter(key_func=get_remote_address)

