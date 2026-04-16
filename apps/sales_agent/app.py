"""
Sales Agent Application - Mykroft Business Solutions underwriting frontend.
All case data is persisted in SQLite. Status updates from the underwriting
app are reflected here in real-time.
Runs on port 5001.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from flask import Flask
from flask_cors import CORS
from config import SALES_AGENT_PORT
import database as db
from apps.sales_agent.router import sales_agent_bp

app = Flask(__name__)
CORS(app)

# Initialise DB on startup (creates tables + seeds if empty)
db.init_db()

# Register routes
app.register_blueprint(sales_agent_bp)

if __name__ == "__main__":
    app.run(port=SALES_AGENT_PORT, debug=False)
