from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.ingestion.models import CodeUnit


class BaseResolver(ABC):
    """
    Base class for symbol resolvers across different languages.

    Resolvers mutate CodeUnit instances in-place by resolving
    ImportReference and CallReference target IDs across the codebase graph.
    """

    @abstractmethod
    def resolve_imports(
        self,
        units: list[CodeUnit],
    ) -> None:
        """
        Resolves raw import statements to actual target CodeUnit IDs.
        Mutates ImportReference.target_unit_id in-place.
        """
        pass

    @abstractmethod
    def resolve_calls(
        self,
        units: list[CodeUnit],
    ) -> None:
        """
        Resolves function/method call expressions to actual target CodeUnit IDs.
        Mutates CallReference.target_unit_id in-place.
        """
        pass
