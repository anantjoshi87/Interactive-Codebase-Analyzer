from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.ingestion.models import CodeUnit


class BaseResolver(ABC):

    def resolve_imports(
        self,
        units: list[CodeUnit],
    ) -> None:
        """
        Resolve ImportReference.target_unit_id.
        """
        ...

        return []

    def resolve_calls(
        self,
        units: list[CodeUnit],
    ) -> None:
        """
        Resolve CallReference.target_unit_id.
        """
        ...
