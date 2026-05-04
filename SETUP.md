# OmniResolve — Setup Guide

Complete step-by-step instructions using **uv** as the package manager.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | [python.org](https://python.org) or `winget install Python.Python.3.12` |
| uv | latest | `pip install uv` or `winget install astral-sh.uv` |
| Docker Desktop | latest | [docker.com](https://docker.com/products/docker-desktop) |
| Git | any | [git-scm.com](https://git-scm.com) |

Verify:

```bash
python --version       # Python 3.12.x
uv --version           # uv 0.x.x
docker --version       # Docker version 27.x
```

---

## Step 1 — Clone and install dependencies

```bash
git clone <your-repo-url>
cd omni-resolve

# Create virtual environment and install all dependencies
uv sync

# Install dev dependencies (pytest, ruff)
uv sync --extra dev
```

`uv sync` reads `pyproject.toml`, creates `.venv/` automatically, and installs everything. You do not need to activate the environment manually — prefix commands with `uv run`.

To activate manually if needed:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

---

## Step 2 — API keys

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
# Required — get from console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# Required — get from platform.openai.com (used for embeddings only)
OPENAI_API_KEY=sk-...

# Required — get from dashboard.cohere.com
COHERE_API_KEY=...

# These stay as-is if you use docker-compose
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=omni-resolve-secret
POSTGRES_URL=postgresql://omni:omni-resolve-secret@localhost:5432/omnidb

# Optional — get from smith.langchain.com for trace monitoring
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=omni-resolve
```

**Minimum required keys to run:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `COHERE_API_KEY`.

---

## Step 3 — Start databases

```bash
docker-compose up neo4j postgres -d
```

This starts:
- **Neo4j 5.x Enterprise** with the GDS plugin on ports `7474` (browser) and `7687` (Bolt)
- **PostgreSQL 16** for LangGraph checkpoints on port `5432`

Wait for Neo4j to be ready (takes ~30 seconds on first start):

```bash
docker-compose logs -f neo4j
# Wait for: "Remote interface available at http://localhost:7474/"
```

Open the Neo4j browser at [http://localhost:7474](http://localhost:7474) and log in with `neo4j` / `omni-resolve-secret` to verify it's running.

---

## Step 4 — Generate synthetic data

This step requires **no API keys** — it runs entirely locally and writes JSON files to `data/`.

```bash
uv run python scripts/generate_data.py
```

Output:

```
data/customers.json    100 UK customers with names, emails, risk scores
data/sellers.json       20 sellers with dispute/fraud rates
data/products.json      31 named products (Sony, Apple, LEGO, Dyson...)
data/disputes.json     500 disputes with paragraph-length descriptions
data/policies.json      20 seller return policies citing CRA 2015
```

The dispute descriptions are full narrative paragraphs — not one-liners — so embeddings are semantically meaningful for RAG.

---

## Step 5 — Load data into Neo4j

This step **requires your API keys** (OpenAI for embeddings) and **Neo4j running**:

```bash
uv run python scripts/load_to_neo4j.py
```

What it does, in order:

1. Applies Neo4j schema — constraints and vector indexes
2. Loads 100 customers, 20 sellers, 31 products
3. Ingests all 8 Consumer Rights Act 2015 clauses (with embeddings)
4. Ingests 20 seller policies (with embeddings)
5. Embeds and loads 500 disputes in batches of 25
6. Creates `RESOLVED_BY` edges linking disputes to policies
7. Computes `SIMILAR_TO` edges between semantically similar disputes (requires Neo4j GDS)

Expected time: **5–10 minutes** (dominated by 500 OpenAI embedding calls).

To skip the similarity edge step if GDS is unavailable:

```bash
uv run python scripts/load_to_neo4j.py --skip-sim
```

To load only the legal clauses (useful for testing):

```bash
uv run python scripts/load_to_neo4j.py --only laws
```

---

## Step 6 — Build community summaries (optional but recommended)

This runs GDS Louvain community detection on the graph, then uses Claude to generate a natural-language summary for each community cluster. These summaries power Mode 2 of GraphRAG retrieval.

```bash
uv run python main.py communities
```

Requires Neo4j GDS plugin (included in the docker-compose `neo4j:5.26-enterprise` image).

---

## Step 7 — Run the API

```bash
uv run python main.py api
```

Or directly with uvicorn:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: [http://localhost:8000](http://localhost:8000)
- Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

## Step 8 — Run the dashboard

In a separate terminal:

```bash
uv run python main.py dashboard
```

Or directly:

```bash
uv run streamlit run dashboard/app.py --server.port 8501
```

Dashboard: [http://localhost:8501](http://localhost:8501)

Tabs:
- **Active Cases** — live resolution log from `logs/audit.jsonl`, escalation queue with human decision form
- **Submit Case** — enter a dispute, upload evidence, see the full resolution brief
- **Analytics** — category breakdown, resolution distribution, confidence histogram, daily volume
- **Systemic Alerts** — high-defect products and seller fraud heatmap from live Neo4j

---

## Step 9 — Run a demo case end-to-end

```bash
uv run python main.py run-case
```

This runs a pre-built demo case through the full pipeline and prints the resolution brief with legal citations.

---

## Step 10 — Run tests

```bash
uv run pytest
```

Run a specific file:

```bash
uv run pytest tests/test_graphrag.py -v
uv run pytest tests/test_agents.py -v
uv run pytest tests/test_resolution.py -v
```

The test suite is fully mocked — no API keys or database needed to run tests.

---

## Full Docker stack (optional)

To run the entire stack including the API and dashboard in Docker:

```bash
# Build and start everything
docker-compose up --build

# Services:
#   neo4j      → localhost:7474 (browser), 7687 (bolt)
#   postgres   → localhost:5432
#   api        → localhost:8000
#   dashboard  → localhost:8501
```

---

## All `main.py` commands

```bash
uv run python main.py api          Start FastAPI server (port 8000)
uv run python main.py dashboard    Start Streamlit dashboard (port 8501)
uv run python main.py seed         Apply schema + load CRA clauses + seed from JSON
uv run python main.py ingest-laws  Load Consumer Rights Act 2015 clauses only
uv run python main.py communities  Run GDS Louvain + generate community summaries
uv run python main.py run-case     Run a demo dispute through the full pipeline
```

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude Sonnet 4.6 — classification, resolution, vision |
| `OPENAI_API_KEY` | Yes | `text-embedding-3-small` embeddings |
| `COHERE_API_KEY` | Yes | `rerank-v3.5` cross-encoder reranking |
| `NEO4J_URI` | Yes | Bolt URI, e.g. `bolt://localhost:7687` |
| `NEO4J_USER` | Yes | Default: `neo4j` |
| `NEO4J_PASSWORD` | Yes | Default: `omni-resolve-secret` |
| `POSTGRES_URL` | Yes | PostgreSQL DSN for LangGraph checkpoints |
| `LANGCHAIN_API_KEY` | No | LangSmith trace monitoring |
| `LANGCHAIN_TRACING_V2` | No | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | LangSmith project name |
| `WHISPER_MODEL` | No | Whisper model size, default `large-v3` |
| `DISKCACHE_DIR` | No | Cache directory, default `.cache/omni_resolve` |
| `UPLOAD_DIR` | No | Evidence upload directory, default `uploads` |
| `IMAP_HOST` | No | IMAP server for email polling |
| `IMAP_USER` | No | IMAP login |
| `IMAP_PASSWORD` | No | IMAP password |
| `WEBHOOK_SECRET` | No | HMAC secret for webhook signature verification |

---

## Typical workflow on a fresh machine

```bash
# 1. Install
uv sync --extra dev

# 2. Configure
cp .env.example .env
# edit .env with your keys

# 3. Databases
docker-compose up neo4j postgres -d

# 4. Data (no keys needed)
uv run python scripts/generate_data.py

# 5. Load (needs keys + Neo4j running)
uv run python scripts/load_to_neo4j.py

# 6. Optional community summaries
uv run python main.py communities

# 7. Run everything
uv run python main.py api          # terminal 1
uv run python main.py dashboard    # terminal 2

# 8. Test
uv run pytest
```

---

## Troubleshooting

**`Neo4j connection refused`**
Neo4j takes ~30s to start. Run `docker-compose logs neo4j` and wait for the "Remote interface available" message. If it never appears, check that port 7687 is not in use: `netstat -an | findstr 7687`.

**`OPENAI_API_KEY not set` during data load**
You must fill in `.env` before running `load_to_neo4j.py`. The generator (`generate_data.py`) needs no keys.

**`GDS procedure not found` during similarity edges**
The docker-compose image includes GDS but it needs the license acceptance env var. Ensure `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes` is set (it is in the provided `docker-compose.yml`). Alternatively run with `--skip-sim`.

**`ModuleNotFoundError`**
Make sure you ran `uv sync` and are prefixing commands with `uv run`. Or activate the venv manually: `.venv\Scripts\Activate.ps1` (Windows) then run commands directly.

**Whisper is slow on CPU**
Set `WHISPER_MODEL=base` or `WHISPER_MODEL=small` in `.env` for faster (lower-accuracy) transcription during development.

**`psycopg2` install fails on Windows**
The `requirements.txt` and `pyproject.toml` use `psycopg2-binary` which includes compiled wheels — no system PostgreSQL install needed.

**LangSmith traces not appearing**
Set both `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true` in `.env`. The project name in `LANGCHAIN_PROJECT` must match what you created in the LangSmith UI.
