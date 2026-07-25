"""
RepoMind Production Server Launcher.
Starts FastAPI backend server and serves built production React frontend on http://127.0.0.1:8000.
"""

import sys
import os
import uvicorn

backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app

if __name__ == "__main__":
    print("=" * 65)
    print("Starting RepoMind Production Server on http://127.0.0.1:8000")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=backend_path)
