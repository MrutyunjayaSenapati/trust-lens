from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str


class Entities(BaseModel):
    kind: Literal["job_offer", "seller", "deal", "property", "other"] = "other"
    company: Optional[str] = None
    role: Optional[str] = None
    city: Optional[str] = None
    claimed_address: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    product: Optional[str] = None
    claimed_price: Optional[float] = None
    claimed_original_price: Optional[float] = None
    payment_requested: bool = False
    summary: str = ""
    transcript: str = ""  # verbatim text read from a screenshot, so text red-flags can run on it


class Evidence(BaseModel):
    id: str
    engine: str
    title: str
    detail: str
    signal: Literal["positive", "negative", "neutral"] = "neutral"
    weight: int = 0  # points added to the trust score (negative lowers it)
    sources: List[Source] = Field(default_factory=list)


class Contradiction(BaseModel):
    id: str
    title: str
    detail: str
    evidence_ids: List[str] = Field(default_factory=list)
    weight: int = 0


class InvestigateRequest(BaseModel):
    text: str = ""
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None
    image_url: Optional[str] = None  # public URL, enables Google Lens check


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["subject", "engine", "evidence", "contradiction"]
    signal: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str = "link"


class Result(BaseModel):
    score: int
    verdict: Literal["likely_genuine", "verify", "suspicious", "likely_scam"]
    confidence: Literal["low", "medium", "high"]
    entities: Entities
    evidence: List[Evidence]
    contradictions: List[Contradiction]
    explanation: str
    next_steps: List[str]
    warning_en: str
    warning_hi: str
    explanation_hi: str = ""
    next_steps_hi: List[str] = Field(default_factory=list)
    source_note: Optional[str] = None  # how a pasted link was resolved
    graph_nodes: List[GraphNode]
    graph_edges: List[GraphEdge]
    engines_used: List[str]
    live_calls: int
    cache_hits: int
