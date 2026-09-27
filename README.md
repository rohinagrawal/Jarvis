# Jarvis

An agentic RAG (Retrieval-Augmented Generation) personal assistant, built from first principles in Python to understand GenAI systems end to end.

The goal is not just a working assistant, but one where every design choice (chunk size, retrieval strategy, agent flow) is made deliberately and can be defended, rather than inherited from a framework's defaults.

> **Status:** Work in progress. See [Roadmap](#roadmap) for what is built and what is planned.

## Architecture

```
            ┌──────────────┐
 Documents ─▶  Chunking    │  hierarchical: ## headers → paragraphs → token-limit cuts
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │  Embeddings  │──▶ Vector DB
            └──────┬───────┘
                   ▼
            ┌──────────────┐
 Query ────▶│  Retrieval   │  hybrid (BM25 + dense) + cross-encoder reranking
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │  Agent loop  │  LangGraph: tools, short-term memory,
            │              │  human-in-the-loop guardrail
            └──────┬───────┘
                   ▼
                Answer (Gemini)
```

## Roadmap

| Phase | Component | Status |
|---|---|---|
| 0 | Setup: environment, LLM provider (Gemini), first API call | ✅ Done |
| 1 | Corpus & hierarchical chunking | 🚧 In progress |
| 2 | Embeddings + vector store | ⏳ Planned |
| 3 | Hybrid search (BM25 + dense) + reranking | ⏳ Planned |
| 4 | Basic RAG loop | ⏳ Planned |
| 5 | Agent loop in LangGraph with 2-3 tools | ⏳ Planned |
| 6 | Memory (short-term) | ⏳ Planned |
| 7 | Guardrail: human confirmation before side-effecting actions | ⏳ Planned |
| 8 | Evaluation set (10-15 queries) | ⏳ Planned |
| 9 | Polish | ⏳ Planned |

## Design decisions

Every non-trivial decision is recorded with its reasoning and the alternatives rejected, and every failure with its root cause, in the **Decisions Log** and **Failure Log** in [BUILD_GUIDE.md](BUILD_GUIDE.md).

Highlights so far:
- **Chunking:** recursive/hierarchical split on `##` headers, then paragraphs, then a hard token-limit cut. Overlap is applied only at token-limit cuts, since header boundaries are already deliberate topic boundaries.
- **LLM provider:** Google Gemini, after GitHub Models (the first choice) turned out to be retired mid-build.

## Tech stack

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/)
- Google Gemini API (`google-genai`)
- Planned: a vector database, BM25, a cross-encoder reranker, LangGraph

## Getting started

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), and a [Gemini API key](https://aistudio.google.com/apikey).

1. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/rohinagrawal/Jarvis.git
   cd Jarvis
   uv sync
   ```
2. Create a `dev.env` file in the project root (it is git-ignored):
   ```
   GEMINI_API_KEY=your-key-here
   ```
3. Run:
   ```bash
   uv run python main.py
   ```

## Repository layout

| Path | Purpose |
|---|---|
| `Jarvis/` | Project source |
| `main.py` | Entry point |
| `BUILD_GUIDE.md` | Phase-by-phase build plan, Decisions Log and Failure Log |
| `LEARN.md` | GenAI concept notes; also the corpus Jarvis retrieves over |

## License

[MIT](LICENSE)
