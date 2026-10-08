# RepoMind

RepoMind is an **investigation engine, not an AI that magically fixes bugs**. It is a triage tool designed to help you quickly understand large codebases. The agent investigates issues, cites evidence, and verifies hypotheses with tests, leaving the final judgment to the human developer.

## Architecture

```text
+-------------------+      +---------------------------------+
|                   |      |                                 |
|  React + Vite UI  |<---->|   FastAPI Backend               |
|  (Frontend)       |      |   (app.main)                    |
|                   |      +---------------------------------+
+-------------------+               |             |
                                    v             v
                           +----------------+  +-----------------+
                           |                |  |                 |
                           | LangGraph      |  | SQLite Database |
                           | Agent          |  |                 |
                           +----------------+  +-----------------+
                                    |
                                    v
                           +-------------------+
                           |                   |
                           | LiteLLM Gateway   |
                           | (Zero-Cost)       |
                           +-------------------+
```

## Quickstart (Zero-Config)

You can run RepoMind without Docker or complex configuration.

1. Clone the repository
2. Install Python dependencies:
   ```bash
   cd backend
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   # source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Run the backend and frontend:
   ```bash
   # In backend/
   python run.py
   
   # In frontend/ (in a separate terminal)
   npm install
   npm run dev
   ```

## Features
- **Vectorless Retrieval:** Uses Tree-sitter for AST parsing and BM25 for text search to find symbols and files without needing a vector database.
- **Agentic Triage Workflow:** Built on LangGraph to investigate and verify patches.
- **Automated Patch Verification:** Applies AI-generated patches to a temporary copy of the codebase.
- **Targeted Test Selection:** Infers which tests to run based on the symbols modified in a unified diff.
- **Zero-Cost LLM Gateway:** Integrated LiteLLM allows using free-tier models (Groq/Gemini).
- **Security Scanning:** Scans for dangerous patterns (e.g. `eval`, `exec`, shell injections) before applying code changes.
- **Digest Generation:** Generates a ranked morning triage report over open issues (severity × confidence, duplicate flags).
- **Architecture Overview:** Generates an architecture overview for onboarding a newcomer.
- **Local Model Context Protocol (MCP) Server:** Exposes investigation capabilities to AI IDEs like Cursor and Claude Desktop.

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check to verify API status. |
| `/api/ingest` | POST | Ingests a repository via `ingest_repo`. |
| `/api/repos` | GET | Returns a list of available ingested repositories. |
| `/api/triage` | POST | Kicks off a background LangGraph agent triage task for an issue. |
| `/api/stream/{thread_id}` | GET | Streams agent execution logs via Server-Sent Events (SSE). |
| `/api/approve` | POST | Resumes graph execution based on human approval/rejection of a patch. |
| `/api/followup` | POST | Adds a human message to the thread history and resumes the graph. |
| `/api/state/{thread_id}` | GET | Retrieves the current state, patches, and logs of a thread. |
| `/api/pr` | POST | Creates a draft pull request using the verified patch. |
| `/api/digest` | POST | Generates a digest report of ranked open issues. |
| `/api/digest/{digest_id}` | GET | Retrieves a previously generated digest report. |
| `/api/explain` | POST | Generate an architecture overview for onboarding a newcomer. |
| `/api/history` | GET | Retrieves all past triage runs from the SQLite database. |

## MCP Server Usage

RepoMind includes an MCP server that you can integrate with tools like Claude Desktop or Cursor to search and analyze code directly from your editor.

**Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "repomind": {
      "command": "python",
      "args": ["-m", "app.mcp_server", "--repo", "<YOUR_REPO_ID>"],
      "env": {
         "PYTHONPATH": "path/to/repomind/backend"
      }
    }
  }
}
```
