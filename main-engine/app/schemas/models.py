from enum import Enum
from typing import Literal, Any, Type, Optional
from pydantic import BaseModel, Field
from tree_sitter import Language

class LanguageConfig(BaseModel):
    language: Language
    symbol_query: str
    import_query: str
    global_query: str
    extractor: Type[Any]

    model_config = {
        "arbitrary_types_allowed": True,
    }


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


class ImportReference(BaseModel):
    module: str
    imported_name: Optional[str] = None
    alias: Optional[str] = None
    target_unit_id: Optional[str] = None
    line: Optional[int] = None


class GlobalVariable(BaseModel):
    name: str
    declaration_type: Optional[str] = None
    value: Optional[str] = None
    line: Optional[int] = None


class CallReference(BaseModel):
    receiver: Optional[str] = None
    method: str
    callee: str
    target_symbol_id: Optional[str] = None
    resolution_status: str = "UNRESOLVED"
    resolver: Optional[str] = None
    call_type: str = "FUNCTION_CALL"
    line: Optional[int] = None
    column: Optional[int] = None


class SymbolReference(BaseModel):
    name: str
    kind: Optional[str] = None
    target_symbol_id: Optional[str] = None
    resolution_status: str = "UNRESOLVED"
    resolver: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None


class CodeMetadata(BaseModel):
    imports: list[ImportReference] = Field(default_factory=list)
    globals: list[GlobalVariable] = Field(default_factory=list)
    parent_class: Optional[str] = None
    calls: list[CallReference] = Field(default_factory=list)
    references: list[SymbolReference] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)
    decorators: list[str] = Field(default_factory=list)
    inheritance: list[str] = Field(default_factory=list)


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
