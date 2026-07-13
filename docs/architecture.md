# System Architecture

> Maverick — AI Agent Platform  
> Stack: FastAPI · MongoDB · Qdrant · React + Vite · TypeScript

---

## Overview

Maverick is a multi-provider AI agent builder. Users create agents with a role, goal, instructions, an LLM provider/model, optional memory, optional RAG knowledge bases, optional structured JSON output, and optional child agents (manager pattern). Agents can be queried through a REST chat endpoint or a real-time SSE stream.

---

## High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                       React Frontend                            │
│  pages: Agents, AgentDetail, RAGs, RAGDetail, Home              │
│  components: Layout, Sidebar                                    │
│  api.ts — all HTTP calls go through here                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend  :8001                       │
│                                                                 │
│  routes/                                                        │
│    agents.py      — CRUD + /message + /message/stream           │
│    agent_ws.py    — WebSocket trace streaming (legacy)          │
│    rag.py         — RAG CRUD + data insert + chat               │
│    llm_info.py    — provider/model catalogue                    │
│    structured.py  — structured output helpers                   │
│    docs.py        — Swagger/ReDoc customisation                 │
│                                                                 │
│  agents/                                                        │
│    registry.py    — PROVIDERS dict (provider → handler fn)      │
│    schemas.py     — all Pydantic models for agents              │
│    system_prompt.py — system prompt builders                    │
│    services/                                                    │
│      runner.py    — stream_agent_chat() async generator         │
│      agent_store.py — MongoDB CRUD + sessions + traces          │
│      openai_agent.py / google_agent.py / anthropic_agent.py     │
│      perplexity_agent.py / openai_compat.py                     │
│                                                                 │
│  rag/                                                           │
│    schemas.py     — RAG + chunk Pydantic models                 │
│    services/                                                    │
│      rag_store.py — RAG config CRUD (MongoDB)                   │
│      chunk_store.py — Qdrant vector ops                         │
│      embedder.py  — OpenAI / Gemini embedding calls             │
│      splitter.py  — text chunking                               │
│      retrieval.py — MMR, HyDE, time-aware retrieval             │
│                                                                 │
│  services/                                                      │
│    guardrails.py  — input injection check + PII redaction       │
│    structured.py  — JSON output parser                          │
│    llm_catalog.py — model/pricing metadata                      │
│                                                                 │
│  settings.py      — env config (Pydantic BaseSettings)          │
└────────┬─────────────────────────────┬───────────────────────────┘
         │ pymongo                      │ qdrant_client
         ▼                             ▼
    MongoDB                        Qdrant
    collections:                   collections (one per RAG):
      agents                         <rag_id>  — vectors + payload
      rags
      rag_chunks
      sessions
      traces
```

---

## Request Lifecycle — Agent Chat (SSE Stream)

```
POST /agents/message/stream
  body: { agent_id, message, session_id?, extra_prompt? }

1. check_input()          — hard-block injection, max 20k chars
2. redact_input()         — strip SSN, credit card, passport etc.
3. agent_store.get()      — fetch agent config from MongoDB
4. trace_store.create()   — open trace record in MongoDB
5. session_memory.get_history()   — if memory_enabled + session_id
6. build_*_system_prompt()        — role + goal + instructions (+ managed agents if manager)
7. append_extra_prompt()          — merge per-request key/values
8. _retrieve_rag()                — if rag_config set:
   a. embed_texts(query)          — OpenAI / Gemini embedding API
   b. chunk_store.search_scored() — Qdrant ANN search
   c. append context block to system
9. PROVIDERS[provider](AgentChatRequest, settings)  — call LLM
   OR: _stream_manager() — if managed_agents > 0
10. scrub_output()        — strip API keys from response
11. session_memory.add_turn()     — persist Q+A if memory enabled
12. trace_store.complete()        — store result + usage in MongoDB
13. yield SSE events → client
```

**SSE event types:**
| Event | When |
|---|---|
| `trace` / `trace_start` | Always first |
| `trace` / `memory_loaded` | When memory is on |
| `trace` / `rag_start` + `rag_result` | When RAG is configured |
| `trace` / `llm_start` | Non-manager agents |
| `trace` / `llm_end` | After LLM call completes |
| `trace` / `manager_routing` | Manager agents |
| `trace` / `manager_delegating` | When manager decides to delegate |
| `trace` / `manager_agent_call` | Each child agent called |
| `trace` / `manager_agent_result` | Each child agent result |
| `trace` / `manager_synthesis` | Final synthesis call |
| `response` | Final answer + structured_output + usage + trace_id |
| `done` | Stream end |
| `error` | Any failure |

---

## Manager Agent Pattern

When an agent has `managed_agents` configured, `runner.py` routes through `_stream_manager()`:

```
Manager receives user message
  │
  ├─ Routing call → manager LLM
  │    System prompt includes:  ## Available Agents + ## Routing Instructions
  │    Expected response:  {"delegate": [{"agent_id": "...", "task": "..."}]}
  │                        OR normal text response (no delegation)
  │
  ├─ If delegation: for each child agent → call child LLM → collect result
  │
  └─ Synthesis call → manager LLM combines all child results into final answer
```

---

## RAG System

Each RAG is an independent knowledge base with its own embedding model and vector collection.

```
Insert text/file:
  text → splitter.py (chunk_size / overlap) → embed_texts() → Qdrant upsert

Query:
  query → embed_texts() → chunk_store.search_scored()
    retrieval_type:
      basic      — cosine similarity
      mmr        — Maximal Marginal Relevance (relevance + diversity balance)
      hyde       — LLM generates a hypothetical doc, then searches by that
      time_aware — cosine score weighted by document recency

Retrieval result injected as:
  --- Relevant Context ---
  [1] (source: ...)
  chunk text
  --- End of Context ---
```

Embedding models supported:

| Provider | Models |
|---|---|
| OpenAI | text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002 |
| Gemini | gemini-embedding-001, gemini-embedding-2, text-embedding-004, embedding-001 |

---

## Memory System

Stored in MongoDB `sessions` collection, keyed by `session_id`.

- `get_history(session_id, max_messages)` — returns last N turns as `[{role, content}]`
- `add_turn(session_id, user_msg, assistant_msg)` — appends 2 messages
- History is passed as `history` in `AgentChatRequest` to the LLM provider
- Each provider formats history per its own API (OpenAI messages array, Gemini `contents`, etc.)

---

## Trace System

Stored in MongoDB `traces` collection, indexed by `(agent_id, created_at)`.

- Created at start of every chat request
- Completed with content + token usage at end
- Available via `GET /agents/{agent_id}/traces` and `GET /agents/{agent_id}/traces/{trace_id}`

---

## Guardrails

**Input layer (before LLM):**
- Prompt injection: 10 hard-block regex patterns → 400 response
- Length: max 20,000 characters
- PII redaction: SSN, credit card, passport, Aadhaar, bank account → replaced with `[REDACTED:TYPE]`

**Output layer (before client):**
- API key scrubbing: Anthropic, OpenAI, Google, Perplexity, generic secrets
- Max output: 50,000 characters

---

## LLM Providers

Registered in `agents/registry.py`:

| Provider | Key in `.env` | Handler file |
|---|---|---|
| `google` | `GOOGLE_API_KEY` | `google_agent.py` |
| `openai` | `OPENAI_API_KEY` | `openai_agent.py` |
| `anthropic` | `ANTHROPIC_API_KEY` | `anthropic_agent.py` |
| `perplexity` | `PERPLEXITY_API_KEY` | `perplexity_agent.py` |

All providers implement: `async def handler(req: AgentChatRequest, settings: Settings) -> AgentChatResponse`

---

## Data Stores

### MongoDB (pymongo sync, wrapped in asyncio.to_thread)
| Collection | Contents |
|---|---|
| `agents` | Agent configs (name, role, goal, instructions, model, provider, RAG config, managed agents, schema) |
| `rags` | RAG metadata (name, embedding model, vector store) |
| `rag_chunks` | Chunk metadata (not vectors — those live in Qdrant) |
| `sessions` | Conversation history per session_id |
| `traces` | Execution traces per agent/session |

### Qdrant
- One collection per RAG, named by `rag_id`
- Payload stored per point: `chunk_id`, `rag_id`, `name`, `source`, `data`, `created_at`, `metadata`

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB connection string |
| `MONGO_DATABASE` | No (default: `sales`) | Database name |
| `QDRANT_URL` | No (default: `http://localhost:6333`) | Qdrant instance |
| `QDRANT_API_KEY` | No | Qdrant Cloud key |
| `GOOGLE_API_KEY` | For Gemini/Google agents | Gemini LLM + embedding |
| `OPENAI_API_KEY` | For OpenAI agents | GPT models + embedding |
| `ANTHROPIC_API_KEY` | For Anthropic agents | Claude models |
| `PERPLEXITY_API_KEY` | For Perplexity agents | Sonar models |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/agents/` | Create agent |
| GET | `/agents/` | List all agents |
| GET | `/agents/agent-config/{id}` | Get agent config |
| PATCH | `/agents/{id}` | Update agent |
| DELETE | `/agents/{id}` | Delete agent |
| POST | `/agents/message` | Chat (collects full response, returns JSON) |
| POST | `/agents/message/stream` | Chat SSE stream (trace events + response) |
| GET | `/agents/{id}/traces` | List traces for agent |
| GET | `/agents/{id}/traces/{trace_id}` | Get single trace |
| POST | `/rags/` | Create RAG |
| GET | `/rags/` | List all RAGs |
| GET | `/rags/{id}` | Get RAG config |
| DELETE | `/rags/{id}` | Delete RAG |
| GET | `/rags/{id}/data` | List chunks |
| POST | `/rags/{id}/data/text` | Insert text |
| POST | `/rags/{id}/data/files` | Upload file |
| POST | `/rags/{id}/chat` | Query RAG (retrieval only, no LLM) |
| GET | `/llm-info/providers` | List all supported providers + models |

---

## Frontend Pages

| Page | Route | What it does |
|---|---|---|
| Home | `/` | Landing / dashboard |
| Agents | `/agents` | List all agents, create new |
| AgentDetail | `/agents/:id` | Edit agent config + live chat tab |
| RAGs | `/rags` | List knowledge bases |
| RAGDetail | `/rags/:id` | Manage chunks, insert data, test queries |

Chat uses SSE stream (`/agents/message/stream`), parsing `data: {...}\n\n` events live.

---

## Infrastructure

- `docker-compose.yml` — local MongoDB + Qdrant
- `Dockerfile` — backend container
- `Procfile` — Heroku/Railway process definition
- `sales-frontend/vercel.json` — SPA rewrite rule (all routes → index.html)
