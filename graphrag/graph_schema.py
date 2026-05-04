from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CustomerNode(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    dispute_count: int = 0
    fraud_risk_score: float = 0.0
    embedding: Optional[list[float]] = None

class OrderNode(BaseModel):
    id: str
    date: datetime
    total_value: float
    status: str
    channel: str

class ProductNode(BaseModel):
    sku: str
    name: str
    category: str
    defect_rate: float = 0.0
    return_rate: float = 0.0
    embedding: Optional[list[float]] = None

class SellerNode(BaseModel):
    id: str
    name: str
    dispute_rate: float = 0.0
    refund_rate: float = 0.0
    fraud_signals: int = 0

class DisputeNode(BaseModel):
    id: str
    category: str
    channel: str
    status: str
    resolution: Optional[str] = None
    confidence: float = 0.0
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PolicyNode(BaseModel):
    id: str
    source: str
    clause: str
    text: str
    embedding: Optional[list[float]] = None
    version_date: datetime

class LegalClauseNode(BaseModel):
    act: str
    section: str
    text: str
    embedding: Optional[list[float]] = None

class EvidenceNode(BaseModel):
    id: str
    type: str
    url: str
    damage_score: float = 0.0
    validity_score: float = 0.0
    description: str = ""

class CaseSummaryNode(BaseModel):
    community_id: int
    summary: str
    embedding: Optional[list[float]] = None
    case_count: int = 0

SCHEMA_CYPHER = """
CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT product_sku IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE;
CREATE CONSTRAINT seller_id IF NOT EXISTS FOR (s:Seller) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT dispute_id IF NOT EXISTS FOR (d:Dispute) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE;

CREATE VECTOR INDEX dispute_embeddings IF NOT EXISTS
  FOR (d:Dispute) ON (d.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX product_embeddings IF NOT EXISTS
  FOR (p:Product) ON (p.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX policy_embeddings IF NOT EXISTS
  FOR (p:Policy) ON (p.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX community_embeddings IF NOT EXISTS
  FOR (cs:CaseSummary) ON (cs.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX legal_embeddings IF NOT EXISTS
  FOR (l:LegalClause) ON (l.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};
"""
