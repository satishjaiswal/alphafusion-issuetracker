#!/usr/bin/env python3
"""
Entry point for running the Flask app as a module
"""

from apps.web.app import create_app

app = create_app()

if __name__ == "__main__":
    port = app.config.get('FLASK_PORT', 6001)
    debug = app.config.get('FLASK_DEBUG', False)
    app.run(host='0.0.0.0', port=port, debug=debug)

