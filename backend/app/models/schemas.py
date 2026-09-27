from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProgressInfo(BaseModel):
    status: str
    step: str
    pct: int
    message: str | None = None


class DocumentSummary(BaseModel):
    id: UUID
    title: str
    source_type: str
    source_ref: str | None
    status: str
    page_count: int | None
    chunk_count: int
    entity_count: int
    error: str | None
    created_at: datetime
    queued: bool | None = None


class IngestTextRequest(BaseModel):
    title: str
    text: str


class IngestUrlRequest(BaseModel):
    url: str


class Citation(BaseModel):
    """A span of a source document that the model quoted.

    char_start/char_end are offsets into `documents.raw_text` -- the model
    reports offsets relative to the chunk it was given, and the answer layer
    rebases them onto the full document so the frontend can highlight in situ.
    """

    document_id: UUID
    document_title: str
    chunk_id: UUID
    page_number: int | None
    cited_text: str
    char_start: int
    char_end: int


class AnswerSegment(BaseModel):
    """One run of answer text plus whatever it cites.

    The model returns the answer as alternating cited/uncited spans; keeping
    that structure lets the UI attach citation cards inline instead of dumping
    a bibliography at the end.
    """

    text: str
    citations: list[Citation]


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    segments: list[AnswerSegment]
    citations: list[Citation]
    retrieved_chunk_ids: list[UUID]


class GraphNode(BaseModel):
    id: UUID
    name: str
    entity_type: str | None
    degree: int


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    relation: str
    chunk_id: UUID | None
    document_id: UUID | None
    document_title: str | None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EntityEvidence(BaseModel):
    """The passage an edge was extracted from, so a graph claim is checkable."""

    relation: str
    other_name: str
    direction: str = Field(description="'out' or 'in' relative to this entity")
    chunk_id: UUID | None
    document_id: UUID | None
    document_title: str | None
    page_number: int | None
    char_start: int | None
    char_end: int | None
    excerpt: str | None


class EntityDetail(BaseModel):
    id: UUID
    name: str
    entity_type: str | None
    evidence: list[EntityEvidence]
