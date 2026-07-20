from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.models import Repository


class GraphCache(Base):
    __tablename__ = "graph_caches"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    nodes_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    edges_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    repository: Mapped["Repository"] = relationship(
        back_populates="graph_cache",
    )

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<GraphCache(repository='{self.repository_id}')>"
