from enum import Enum
from pydantic import BaseModel
from tree_sitter import Language


class LanguageConfig(BaseModel):
    language: Language
    query: str

    model_config = {"arbitrary_types_allowed": True}


class UnitType(str, Enum):
    CODE = "code"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    TEXT = "text"


class BaseUnit(BaseModel):
    file_path: str
    unit_type: UnitType
    code_content: str

    is_ast_parsed: bool = True


class CodeUnit(BaseUnit):
    symbol_name: str | None = None
    symbol_kind: str
    ast_node_type: str

    start_line: int
    end_line: int

    start_byte: int
    end_byte: int


class ConfigUnit(BaseUnit):
    config_type: str

    metadata: dict

    is_ast_parsed: bool = False
