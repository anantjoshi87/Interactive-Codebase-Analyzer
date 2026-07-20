from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Enum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.models import IndexingStatus

if TYPE_CHECKING:
    from app.models import Repository


class RepositoryIndex(Base):
    __tablename__ = "repository_indexes"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    embedding_model: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    parser_version: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus, name="indexing_status"),
        default=IndexingStatus.PENDING,
        nullable=False,
    )

    total_chunks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_nodes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_edges: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    indexed_commit: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    repository: Mapped["Repository"] = relationship(
        back_populates="repository_index",
    )

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<RepositoryIndex(repo='{self.repository_id}', status='{self.status.value}')>"