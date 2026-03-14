"""WSGI entry point for PythonAnywhere.

PythonAnywhere looks for a variable called `application` in this file.
Point your PythonAnywhere web app's WSGI config to this file.
"""

import os
import sys

# Add the project directory to the path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import app as application  # noqa: E402
from database import init_db  # noqa: E402

# Initialize database on first load
init_db()
