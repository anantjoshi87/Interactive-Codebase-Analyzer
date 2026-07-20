# app/db/models/user.py

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import List

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models import Workspace


class User(Base):
    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Clerk User ID",
    )

    email: Mapped[str] = mapped_column(
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
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Debug Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', email='{self.email}')>"
