#!/usr/bin/env python3
"""
Flask extensions initialization
"""

from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions (without app)
csrf = CSRFProtect()
talisman = Talisman()
limiter = Limiter(key_func=get_remote_address)

