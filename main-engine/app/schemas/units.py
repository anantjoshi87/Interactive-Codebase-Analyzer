from enum import Enum
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.metadata import CodeMetadata


class UnitType(str, Enum):
    CODE = "code"
    CONFIG = "config"
    DOCUMENT = "document"
    TEXT = "text"


class BaseUnit(BaseModel):
    id: str
    file_path: str  # Kept relative to repo root
    unit_type: UnitType
    code_content: str
    is_ast_parsed: bool = False


class CodeUnit(BaseUnit):
    unit_type: UnitType = UnitType.CODE
    symbol_name: str = "<module>"
    qualified_name: str = ""
    symbol_kind: str  # "module" | "class" | "function" | "method"
    ast_node_type: str

    parent_symbol_id: Optional[str] = None

    # 0-based lines and columns match SCIP definitions cleanly
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0
    start_byte: int
    end_byte: int

    metadata: CodeMetadata = Field(default_factory=CodeMetadata)


class ConfigUnit(BaseUnit):
    unit_type: UnitType = UnitType.CONFIG
    config_type: str
    metadata: dict = Field(default_factory=dict)


class DocumentUnit(BaseUnit):
    unit_type: Literal[UnitType.DOCUMENT] = UnitType.DOCUMENT
    document_type: str
    title: Optional[str] = None


AnyUnit = Union[CodeUnit, ConfigUnit, DocumentUnit]
