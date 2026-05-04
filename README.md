# OmniResolve

**Unified Omnichannel E-Commerce Dispute Intelligence System**

LangGraph stateful agents · GraphRAG over Neo4j · Claude Sonnet 4.6 · Whisper STT · XGBoost classifier · Consumer Rights Act 2015

---

## The Problem

E-commerce customers repeat themselves across every channel. A customer emails a complaint, calls the next day, then chats — three agents see three disconnected conversations. Resolution is slow, inconsistent, and legally undefendable.

OmniResolve fixes this by maintaining a single, persistent case memory across voice, chat, email, and documents simultaneously — grounded in UK consumer law and a live Neo4j knowledge graph of every past dispute.

---

## Architecture

```
                         ┌─────────────────────────────────────────┐
  Voice ─── Whisper ─►   │          CHANNEL NORMALISER              │
  Chat  ─── WS ──────►   │   strips PII · unifies event format      │
  Email ─── IMAP ────►   │   appends to CaseState.channel_history   │
  Docs  ─── Upload ──►   └──────────────┬──────────────────────────┘
                                         │
                         ┌───────────────▼──────────────────────────┐
                         │         CUSTOMER RESOLVER                 │
                         │  Neo4j lookup · cross-channel identity    │
                         └───────────────┬──────────────────────────┘
                                         │
                         ┌───────────────▼──────────────────────────┐
                         │         DISPUTE CLASSIFIER                │
                         │  Claude structured output                 │
                         │  fraud · damage · non_delivery · other    │
                         └────────┬────────────────┬────────────────┘
                                  │                │
              ┌───────────────────▼───┐    ┌───────▼────────────────┐
              │    POLICY RETRIEVAL   │    │   EVIDENCE ANALYSER    │
              │  GraphRAG 3-mode      │    │   Claude Vision        │
              │  subgraph + RRF +     │    │   damage_score         │
              │  Cohere rerank        │    │   validity_score       │
              └───────────┬───────────┘    └───────┬────────────────┘
                          │                        │
                          └──────────┬─────────────┘
                                     │
                         ┌───────────▼──────────────────────────────┐
                         │          PRECEDENT AGENT                  │
                         │  Neo4j SIMILAR_TO traversal               │
                         │  top-5 resolved cases by similarity       │
                         └───────────────┬──────────────────────────┘
                                         │
                         ┌───────────────▼──────────────────────────┐
                         │         RESOLUTION ENGINE                 │
                         │  XGBoost on 13 graph features             │
                         │  Claude synthesises brief + CRA citations │
                         └──────────┬──────────────┬────────────────┘
                                    │              │
                          confidence ≥ 0.65    confidence < 0.65
                          low-value order      high-value / fraud
                                    │              │
                         ┌──────────▼──┐   ┌───────▼──────────────┐
                         │ AUTO-RESOLVE │   │  HUMAN ESCALATION    │
                         │  audit log  │   │  LangGraph interrupt  │
                         └─────────────┘   │  caseworker dashboard │
                                           └──────────────────────┘
```

### GraphRAG — Three Retrieval Modes

Standard RAG retrieves text chunks similar to the query. GraphRAG retrieves connected subgraphs — entities, their relationships, and the context surrounding them.

```
Mode 1  Local subgraph traversal
        Customer → Disputes → Orders → Products → Sellers

Mode 2  Community summary retrieval
        GDS Louvain communities → LLM summaries → vector similarity
        (Microsoft GraphRAG pattern applied to typed domain entities)

Mode 3  Node-level vector similarity
        CALL db.index.vector.queryNodes('dispute-embeddings', ...)

All three modes fused via Reciprocal Rank Fusion → Cohere rerank-v3.5
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent orchestration | LangGraph 0.2+ | Stateful persistent case workflows with PostgreSQL checkpoints |
| Graph database | Neo4j 5.x + GDS | Entity and relationship store, vector indexes |
| GraphRAG retrieval | Neo4j Vector + Cypher fusion | Subgraph-aware RAG with 3-mode retrieval |
| LLM | Claude Sonnet 4.6 | Reasoning, generation, vision, structured output |
| Voice STT | Whisper large-v3 | Real-time audio transcription |
| Embeddings | text-embedding-3-small | 1536-dim node and chunk embeddings |
| Reranking | Cohere rerank-v3.5 | Cross-encoder precision layer |
| Classifier | XGBoost | Resolution decision from 13 graph features |
| Backend | FastAPI + WebSocket | REST and live streaming endpoints |
| Checkpoints | PostgreSQL | LangGraph state persistence and recovery |
| Cache | DiskCache 24hr | Zero redundant LLM calls (MD5-keyed) |
| Rate limiting | Token bucket + tenacity | API stability under load |
| Observability | LangSmith | Agent trace monitoring |
| Frontend | Streamlit | Caseworker and operations dashboard |

---

## Project Structure

```
omni-resolve/
├── agents/
│   ├── orchestrator.py          LangGraph StateGraph + CaseState TypedDict
│   ├── channel_normaliser.py    PII stripping, event unification
│   ├── customer_resolver.py     Neo4j cross-channel identity lookup
│   ├── dispute_classifier.py    Claude structured output classifier
│   ├── policy_retrieval.py      GraphRAG node (3-mode + RRF + Cohere)
│   ├── evidence_analyser.py     Claude Vision damage scoring
│   ├── precedent_agent.py       SIMILAR_TO traversal + SKU defect detection
│   ├── resolution_engine.py     XGBoost + Claude resolution brief
│   └── human_escalation.py      LangGraph interrupt/resume node
├── graphrag/
│   ├── neo4j_client.py          Async driver with session pooling
│   ├── graph_schema.py          Pydantic node/relationship models + Cypher schema
│   ├── subgraph_retriever.py    Three-mode retrieval implementation
│   ├── community_builder.py     GDS Louvain + LLM community summaries
│   ├── rrf_fusion.py            Reciprocal Rank Fusion
│   └── graph_serialiser.py      Subgraph → structured LLM prompt context
├── channels/
│   ├── voice_handler.py         Whisper STT pipeline
│   ├── chat_handler.py          WebSocket message normalisation
│   ├── email_handler.py         IMAP polling and attachment extraction
│   └── document_handler.py      File upload handling and type detection
├── ingestion/
│   ├── policy_ingester.py       Consumer Rights Act 2015 + seller policies
│   ├── case_ingester.py         Case ingestion + JSON loader
│   ├── embedder.py              Batched OpenAI embeddings
│   └── deduplicator.py          MD5 hash deduplication
├── production/
│   ├── cache.py                 DiskCache 24hr wrapper with @cached decorator
│   ├── rate_limiter.py          Token bucket + exponential backoff
│   ├── audit_logger.py          Structured JSON decision log (JSONL)
│   └── monitoring.py            LangSmith trace hooks
├── api/
│   ├── main.py                  FastAPI app with lifespan schema setup
│   ├── routes/cases.py          Case CRUD, evidence upload, human decision
│   ├── routes/channels.py       Email poll, voice transcription endpoints
│   ├── routes/webhooks.py       Shopify and generic webhooks
│   └── websocket.py             Live chat and voice WebSocket endpoints
├── dashboard/
│   └── app.py                   Streamlit caseworker dashboard
├── scripts/
│   ├── generate_data.py         Synthetic data generator (no API keys needed)
│   └── load_to_neo4j.py         Embed + load all JSON data into Neo4j
├── data/                        Generated JSON data files (gitignored)
├── tests/
│   ├── test_graphrag.py
│   ├── test_agents.py
│   └── test_resolution.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## CaseState — What Persists Across Channels

```python
class CaseState(TypedDict):
    case_id: str
    customer_id: str
    order_id: str
    session_id: str
    channel_history: list[dict]      # append-only, all channels merged
    documents: list[dict]            # uploaded photos, receipts, PDFs
    evidence_scores: dict            # {doc_id: {damage_score, validity_score}}
    dispute_category: str            # fraud | damage | non_delivery | other
    policy_findings: list[dict]      # {clause, source, relevance_score}
    legal_citations: list[str]       # Consumer Rights Act 2015 clauses
    precedent_cases: list[dict]      # {case_id, similarity, resolution}
    graph_subgraph: dict             # serialised Neo4j subgraph
    resolution_recommendation: str  # refund | replace | reject | escalate
    confidence_score: float
    requires_human: bool
```

Every field is checkpointed to PostgreSQL after each node. If a session drops mid-pipeline it resumes from the last completed node.

---

## XGBoost Resolution Classifier

13 features extracted from the Neo4j subgraph at inference time:

| Feature | Source |
|---|---|
| dispute_category | encoded int |
| customer_dispute_count | Customer node |
| customer_fraud_risk_score | Customer node |
| seller_refund_rate | Seller node |
| seller_dispute_rate | Seller node |
| product_defect_rate | Product node |
| product_return_rate | Product node |
| evidence_damage_score | Claude Vision output |
| evidence_validity_score | Claude Vision output |
| policy_match_score | GraphRAG relevance score |
| precedent_similarity_score | SIMILAR_TO edge weight |
| order_value | Order node |
| days_since_purchase | computed |

Target: `refund | replace | reject | escalate`

The LLM handles reasoning and language. XGBoost handles the decision. Every outcome is auditable by feature importance — defensible to Trading Standards or a chargeback panel.

---

## GraphRAG vs Standard RAG — Evaluation Target

50 held-out dispute scenarios run through both systems.

| Metric | Standard RAG | GraphRAG target |
|---|---|---|
| Policy citation accuracy | baseline | +20% |
| Cross-case pattern detection | not possible | >80% |
| Seller fraud signal surfacing | not possible | >70% |
| Resolution correctness | baseline | +15% |
| Answer groundedness (RAGAS) | baseline | higher |

---

## API Reference

```
POST   /api/v1/cases/                    Submit a new dispute case
GET    /api/v1/cases/{case_id}           Get case status and resolution
POST   /api/v1/cases/{case_id}/evidence  Upload photo or receipt
POST   /api/v1/cases/{case_id}/human-decision  Resume after human review

POST   /api/v1/channels/email/poll       Poll IMAP inbox
POST   /api/v1/channels/voice/transcribe Transcribe audio upload

POST   /api/v1/webhooks/shopify/order-dispute
POST   /api/v1/webhooks/generic

WS     /ws/chat/{case_id}               Live chat streaming
WS     /ws/voice/{case_id}              Voice streaming → Whisper → pipeline

GET    /health
GET    /docs                             Swagger UI
```

---

## Quick Start

See [SETUP.md](SETUP.md) for the full step-by-step setup guide with uv.

```bash
# 1. Clone and install
git clone <repo>
cd omni-resolve
uv sync

# 2. Configure
cp .env.example .env
# fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, COHERE_API_KEY

# 3. Start databases
docker-compose up neo4j postgres -d

# 4. Generate and load data
uv run python scripts/generate_data.py
uv run python scripts/load_to_neo4j.py

# 5. Run
uv run python main.py api          # API → http://localhost:8000/docs
uv run python main.py dashboard    # UI  → http://localhost:8501
uv run python main.py run-case     # demo end-to-end
```

---

## What Is Genuinely New In This Stack

| Capability | Why it matters |
|---|---|
| **GraphRAG with Neo4j** | Subgraph retrieval fusing Cypher traversal + vector similarity + community summaries via RRF. Completely different retrieval paradigm from FAISS + BM25. |
| **LangGraph persistent checkpoints** | Stateful agents that pause mid-pipeline, wait for new documents or human input, and resume from exactly where they stopped. |
| **Real-time voice pipeline** | Whisper STT streaming directly into agent state. |
| **Claude Vision evidence scoring** | Damage photos return structured `damage_score`, `damage_type`, `validity_score` fields — not just a text description. |
| **GDS Louvain community detection** | Offline graph community detection + LLM-generated community summaries stored as graph nodes. The Microsoft GraphRAG pattern applied to a typed domain. |
| **Cross-case systemic intelligence** | Neo4j surfaces product defect patterns and seller fraud signals across thousands of cases simultaneously — impossible with flat retrieval. |

---

## License

MIT
