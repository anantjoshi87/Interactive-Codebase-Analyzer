# BaseExtractor abstract class

from abc import ABC, abstractmethod
from typing import List, Optional
from tree_sitter import Node
from app.schemas import (
    ImportReference,
    GlobalVariable,
    CallReference,
)
from app.services.ingestion.grammars.config import LanguageConfig


class BaseExtractor(ABC):
    def __init__(self, code_bytes: bytes, lang_config: LanguageConfig):
        self.code_bytes = code_bytes
        self.lang_config = lang_config

    def _node_text(self, node: Node) -> str:
        """Helper to safely decode byte ranges of an AST node."""
        return (
            self.code_bytes[node.start_byte : node.end_byte]
            .decode("utf-8", errors="ignore")
            .strip()
        )

    @abstractmethod
    def get_node_name(self, node: Node) -> Optional[str]:
        pass

    @abstractmethod
    def extract_imports(self, node: Node) -> List[ImportReference]:
        pass

    @abstractmethod
    def extract_globals(self, node: Node) -> List[GlobalVariable]:
        pass

    @abstractmethod
    def extract_calls(self, node: Node) -> Optional[CallReference]:
        pass
