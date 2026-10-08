# RepoMind Interview Notes

## 30-Second Pitch
RepoMind is an AI-powered triage agent designed to help developers quickly understand and navigate unfamiliar codebases. It automatically ingests code, builds a symbol-aware search index without expensive vector databases, investigates issues by retrieving exact file context, and verifies its own proposed fixes by running targeted tests—all while supporting free-tier LLM models via a zero-cost gateway. It is an investigation engine, not magic; it cites its evidence and leaves the final merge decision to the human.

## Why not just use Copilot?
Copilot is excellent for autocomplete and inline generation within the file you are actively editing, but it lacks the autonomy to investigate repository-wide issues independently. RepoMind acts as an autonomous triage engine that can search across the codebase, build call graphs to find affected tests, and verify its patches in an isolated sandbox before returning a verified report.

## Stack Defenses

- **Python + FastAPI:** Provides a robust, high-performance async backend that effortlessly integrates with modern AI/ML libraries and tooling in the Python ecosystem. (Tradeoff: Lacks the strict compile-time safety of typed languages like Rust or Go).
- **LangGraph:** Enables cyclic, stateful agentic workflows (like "propose patch -> verify -> retry") which are difficult to model cleanly with standard LangChain linear chains. (Tradeoff: Adds architectural complexity and a steeper learning curve).
- **LiteLLM Zero-Cost Gateway:** Abstracts away vendor-specific API differences, allowing seamless switching between models (e.g., Groq and Gemini) to optimize for speed and cost. (Tradeoff: Creates a dependency on a third-party abstraction layer that might lag behind new model features).
- **Tree-sitter + BM25:** Achieves high-precision code retrieval by combining syntax-aware AST parsing with proven text search, eliminating the cost and latency of vector embeddings. (Tradeoff: Struggles with semantic queries where keywords don't match the code exactly).
- **SQLite:** Delivers a zero-configuration, lightweight embedded database perfect for storing triage runs and repo metadata locally without deploying external infrastructure. (Tradeoff: Not suitable for high-concurrency, distributed production deployments without locking issues).
- **React + Vite:** Offers a blazing-fast development experience with Hot Module Replacement and an intuitive component-based UI architecture. (Tradeoff: Requires shipping a relatively large JavaScript bundle compared to server-rendered HTML approaches).
