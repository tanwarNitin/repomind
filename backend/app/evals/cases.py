import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
FIXTURE_REPO_DIR = os.path.join(BACKEND_DIR, "tests", "fixture_repo")
REPO_ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

RETRIEVAL_CASES = [
    {
        "query": "parse date from string",
        "expected_file": "utils.py",
        "repo_path": FIXTURE_REPO_DIR
    },
    {
        "query": "fetchdata",
        "expected_file": "api.ts",
        "repo_path": FIXTURE_REPO_DIR
    },
    {
        "query": "performLogin",
        "expected_file": "api.ts",
        "repo_path": FIXTURE_REPO_DIR
    },
    {
        "query": "requesthandler",
        "expected_file": "main.js",
        "repo_path": FIXTURE_REPO_DIR
    },
    {
        "query": "initializeApp",
        "expected_file": "main.js",
        "repo_path": FIXTURE_REPO_DIR
    },
    {
        "query": "search index builder bm25",
        "expected_file": "backend/app/core/search.py",
        "repo_path": REPO_ROOT_DIR
    },
    {
        "query": "apply unified diff patch",
        "expected_file": "backend/app/verify/patcher.py",
        "repo_path": REPO_ROOT_DIR
    },
    {
        "query": "select tests based on changed symbols call graph",
        "expected_file": "backend/app/verify/test_selector.py",
        "repo_path": REPO_ROOT_DIR
    }
]

PATCH_CASES = [
  {
    "repo_path": REPO_ROOT_DIR,
    "diff": "diff --git a/backend/app/core/config.py b/backend/app/core/config.py\n--- a/backend/app/core/config.py\n+++ b/backend/app/core/config.py\n@@ -1,4 +1,5 @@\n from pydantic_settings import BaseSettings\n+# AI comment\n from pydantic import ConfigDict\n \n class Settings(BaseSettings):\n",
    "expected_test_substr": ""
  },
  {
    "repo_path": REPO_ROOT_DIR,
    "diff": "diff --git a/backend/app/core/gateway.py b/backend/app/core/gateway.py\n--- a/backend/app/core/gateway.py\n+++ b/backend/app/core/gateway.py\n@@ -1,4 +1,5 @@\n import litellm\n+# AI comment\n import json\n from .config import settings\n from langchain_core.messages import AIMessage, ToolCall\n",
    "expected_test_substr": "test_gateway"
  },
  {
    "repo_path": REPO_ROOT_DIR,
    "diff": "diff --git a/backend/app/core/db.py b/backend/app/core/db.py\n--- a/backend/app/core/db.py\n+++ b/backend/app/core/db.py\n@@ -1,4 +1,5 @@\n from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime\n+# AI comment\n from sqlalchemy.orm import declarative_base, sessionmaker\n import datetime\n from datetime import timezone\n",
    "expected_test_substr": "test_db"
  },
  {
    "repo_path": REPO_ROOT_DIR,
    "diff": "diff --git a/backend/app/core/search.py b/backend/app/core/search.py\n--- a/backend/app/core/search.py\n+++ b/backend/app/core/search.py\n@@ -1,4 +1,5 @@\n import os\n+# AI comment\n from rank_bm25 import BM25Okapi\n from .ast_index import parse_file\n \n",
    "expected_test_substr": "test_search"
  },
  {
    "repo_path": REPO_ROOT_DIR,
    "diff": "diff --git a/backend/app/verify/patcher.py b/backend/app/verify/patcher.py\n--- a/backend/app/verify/patcher.py\n+++ b/backend/app/verify/patcher.py\n@@ -1,4 +1,5 @@\n import os\n+# AI comment\n import subprocess\n import re\n \n",
    "expected_test_substr": "test_verify"
  }
]
