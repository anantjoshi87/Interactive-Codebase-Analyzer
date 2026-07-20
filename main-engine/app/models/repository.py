from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.models import Workspace
    from app.models import RepositoryIndex
    from app.models import GraphCache


class Repository(Base):
    __tablename__ = "repositories"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    github_url: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    current_commit: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="repository",
    )

    repository_index: Mapped["RepositoryIndex"] = relationship(
        back_populates="repository",
        uselist=False,
        cascade="all, delete-orphan",
    )

    graph_cache: Mapped["GraphCache"] = relationship(
        back_populates="repository",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Repository(url='{self.github_url}')>"
