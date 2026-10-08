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
   pip install -r requirements.txt
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
- **Digest Generation:** Analyzes a repository to produce a summary markdown report of architecture and endpoints.
- **Local Model Context Protocol (MCP) Server:** Exposes investigation capabilities to AI IDEs like Cursor and Claude Desktop.

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/run` | POST | Submits an issue to the triage agent for investigation. |
| `/api/repo/ingest` | POST | Parses the repository and builds the search index. |
| `/api/search` | GET | Queries the codebase using BM25 and AST symbols. |
| `/api/digest` | POST | Generates an architectural digest report. |
| `/api/runs` | GET | Lists past agent investigation runs from SQLite. |

## MCP Server Usage

RepoMind includes an MCP server that you can integrate with tools like Claude Desktop or Cursor to search and analyze code directly from your editor.

**Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "repomind": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "env": {
         "PYTHONPATH": "path/to/repomind/backend"
      }
    }
  }
}
```
