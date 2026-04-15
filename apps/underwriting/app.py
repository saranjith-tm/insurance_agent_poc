"""
Underwriting Checklist Application
Checklist state is persisted per-application in SQLite.
When the underwriter submits (Proceed to Next Screen / Complete), the case status
in the cases table is updated automatically.
Runs on port 5002.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask
from flask_cors import CORS
from config import UNDERWRITING_PORT
import database as db
from apps.underwriting.router import underwriting_bp

app = Flask(__name__)
CORS(app)

# Initialise DB (idempotent — safe to call multiple times)
db.init_db()

app.register_blueprint(underwriting_bp)

if __name__ == "__main__":
    app.run(port=UNDERWRITING_PORT, debug=False)
