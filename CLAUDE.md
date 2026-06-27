# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Adaptive RAG: an agentic RAG system. A FastAPI backend orchestrates a LangGraph
workflow that classifies each query and routes it to one of three pipelines —
indexed-document retrieval, a general LLM answer, or live web search. A Streamlit
app provides the chat UI and document upload. Chat history is persisted in MongoDB.

## Running the app

There is no build step, no test suite, and no lint config in the repo (the README
mentions `flake8 src/` aspirationally, but no config exists). Development is
manual: run the two processes and exercise them by hand.

```bash
pip install -r requirements.txt          # needs Python 3.9+

# Terminal 1 — FastAPI backend (port 8000)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Streamlit frontend (port 8501)
streamlit run streamlit_app/home.py
```

API docs at http://localhost:8000/docs. The two endpoints are
`POST /rag/query` (`{query, session_id}`) and `POST /rag/documents/upload`
(multipart `file` + `X-Description` header).

Required env (`.env` in repo root): `OPENAI_API_KEY`, `TAVILY_API_KEY`. Qdrant
and Mongo env vars exist but see caveats below.

## Architecture and control flow

The request path is: `src/api/routes.py` loads full chat history from Mongo →
invokes the compiled LangGraph `builder` → persists the assistant reply.

The graph is defined in **`src/rag/graph_builder.py`** — this is the heart of the
system. It contains both the node function bodies *and* the graph wiring at the
bottom of the file. The graph shape:

```
START → query_analysis → (routing_tool) ─┬─ general_llm → END
                                          ├─ web_search → generate → END
                                          └─ retriever → grade → (doc_tool) ─┬─ generate → END
                                                                             └─ rewrite → retriever (loop)
```

- `query_analysis` (`query_classifier`) embeds the question, retrieves context,
  and asks the LLM to label the route `index` / `general` / `search`.
- Routing decisions live in **`src/tools/graph_tools.py`**: `routing_tool` maps
  the label to a node; `doc_tool` sends graded-relevant docs to `generate` and
  irrelevant ones to `rewrite` (which loops back to `retriever`).
- The `retriever` node runs a ReAct agent (`src/rag/reAct_agent.py`), not a plain
  retriever, capped at `max_iterations=2`.

### Gotchas worth knowing before editing

- **`src/rag/nodes.py` is empty.** Despite the name and the README's structure
  diagram, all node logic lives in `graph_builder.py`. Don't go looking in
  `nodes.py`.
- **The vector store is FAISS, not Qdrant.** `src/rag/retriever_setup.py` has the
  Qdrant code commented out and uses an in-memory FAISS store held in a module
  global (`_faiss_vectorstore`). Consequences: the index is **process-local and
  not persisted** — it resets on restart, and the FastAPI worker that handled the
  upload is the only one that can retrieve it (don't run multiple workers). The
  README's Qdrant claims describe the disabled path.
- **`description.txt` is a runtime artifact**, not docs. Document upload writes an
  LLM-enhanced description there; `retriever_setup.py` and `reAct_agent.py` read
  it to scope the retriever tool. It is committed but gets overwritten on upload.
- **The ReAct agent and its retriever tool are built once at import time**
  (`reAct_agent.py` calls `get_retriever()` at module load). Tooling captured at
  startup; a fresh `get_retriever()` is also called inside `query_classifier` per
  request.
- **`verify_answer` in `graph_tools.py` is defined but not wired into the graph.**
- **Two unrelated config objects with confusingly similar names:**
  `src/config/settings.py` → `Config`, which loads prompt templates from
  `prompts.yaml`. `src/core/config.py` → `Settings`/`settings`, which loads env
  vars. They are not the same thing.
- **MongoDB connection is hardcoded** to `mongodb://localhost:27017` /
  `adaptive_rag` in `src/db/mongo_client.py`, ignoring the `MONGODB_URL` env var
  the README documents.
- **Streamlit auth depends on a separate Rust service** at
  `http://localhost:8080/api` (`create_user`/`login`/`init` in
  `streamlit_app/utils/api_client.py`). That service is **not in this repo**; the
  RAG endpoints themselves require no auth.

## Prompts and the LLM

All prompt templates live in **`src/config/prompts.yaml`** under a `prompts:` key,
fetched via `Config().prompt("<key>")`. Keys: `system_prompt`, `classify_prompt`,
`grading_prompt`, `rewrite_prompt`, `generate_prompt`, `verify_prompt`. Tweak
behavior here rather than in code where possible. The model is hardcoded to
`gpt-4o` in `src/llms/openai.py`; embeddings use OpenAI defaults.

Structured LLM outputs use Pydantic models in `src/models/` (`RouteIdentifier`,
`Grade`, `VerificationResult`) via `llm.with_structured_output(...)`.

## Conventions

`CODE_STYLE_GUIDE.md` documents the in-repo style: module docstring on every file,
Google-style docstrings on all functions (Args/Returns/Raises), PEP 8, snake_case.
Note that node functions currently use `print(...)` for tracing rather than the
logger in `src/core/logger.py` — match the surrounding file when editing.
