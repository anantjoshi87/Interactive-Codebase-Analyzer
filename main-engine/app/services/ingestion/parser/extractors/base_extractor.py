# app/services/ingestion/parsers/extractors/base_extractor.py

from __future__ import annotations
from abc import ABC, abstractmethod
from tree_sitter import Node

from app.services.ingestion.models import (
    ImportReference,
    GlobalVariable,
    CallReference,
    Reference,
    LanguageConfig,
)


class BaseExtractor(ABC):
    """
    Base class for all language extractors.
    """

    def __init__(
        self,
        code_bytes: bytes,
        lang_config: LanguageConfig,
    ):
        self.code = code_bytes
        self.config = lang_config
        self.language = lang_config.language

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def node_text(self, node: Node) -> str:
        if not node:
            return ""
        return self.code[node.start_byte : node.end_byte].decode(
            "utf-8",
            errors="ignore",
        )

    # -------------------------------------------------
    # Metadata Extraction Defaults
    # -------------------------------------------------

    def extract_imports(self, root: Node) -> list[ImportReference]:
        return []

    def extract_globals(self, root: Node) -> list[GlobalVariable]:
        return []

    def extract_calls(self, node: Node) -> list[CallReference]:
        return []

    def extract_references(self, node: Node) -> list[Reference]:
        return []

    def extract_docstring(self, node: Node) -> str | None:
        return None

    def extract_parent_class(self, node: Node) -> str | None:
        return None

    def extract_decorators(self, node: Node) -> list[str]:
        return []

    def extract_inheritance(self, node: Node) -> list[str]:
        return []

    def extract_overrides(self, node: Node) -> list[str]:
        return []

    def extract_annotations(self, node: Node) -> list[str]:
        return []

    def extract_exceptions(self, node: Node) -> list[str]:
        return []

    def extract_returns(self, node: Node) -> str | None:
        return None
