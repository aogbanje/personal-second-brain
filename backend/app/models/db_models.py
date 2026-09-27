"""ORM models mirroring infra/init.sql.

init.sql owns the schema (generated columns, HNSW/GIN indexes). These classes
exist for CRUD; retrieval uses hand-written SQL in services/retrieval.
"""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String)
    source_ref: Mapped[str | None] = mapped_column(Text, default=None)
    raw_text: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(String, default="pending")
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime]


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"))
    workspace_id: Mapped[UUID]
    ordinal: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int]
    char_end: Mapped[int]
    page_number: Mapped[int | None] = mapped_column(Integer, default=None)
    embedding_model: Mapped[str] = mapped_column(Text)
    embedding_dim: Mapped[int]
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), default=None)
    created_at: Mapped[datetime]
