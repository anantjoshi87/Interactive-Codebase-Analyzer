from enum import Enum
from typing import Literal, Any, Type
from pydantic import BaseModel
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
    file_path: str
    unit_type: UnitType
    code_content: str
    is_ast_parsed: bool


class ImportReference(BaseModel):
    module: str
    imported_name: str | None = None
    alias: str | None = None
    target_unit_id: str | None = None


class GlobalVariable(BaseModel):
    name: str
    declaration_type: str | None = None
    value: str | None = None
    line: int | None = None


class Reference(BaseModel):
    name: str
    kind: str | None = None
    target_unit_id: str | None = None


class CallReference(BaseModel):
    receiver: str | None = None
    method: str
    callee: str
    target_unit_id: str | None = None
    confidence: str = "LOW"
    call_type: str = "FUNCTION_CALL"
    line: int | None = None
    column: int | None = None


class CodeMetadata(BaseModel):
    imports: list[ImportReference] = []
    globals: list[GlobalVariable] = []

    parent_class: str | None = None
    # docstring: str | None = None
    calls: list[CallReference] = []
    # references: list[Reference] = []
    overrides: list[str] = []
    # annotations: list[str] = []

    # Function / Method
    decorators: list[str] = []
    returns: str | None = None
    exceptions: list[str] = []

    # Class
    inheritance: list[str] = []


class CodeUnit(BaseUnit):
    id: str  # e.g., app.py::<module> or app.py::A::B

    symbol_name: str | None = "<module>"  # Defaults to <module> for script files
    symbol_kind: str  # "module", "class", "function", "method"
    ast_node_type: str

    parent_symbol_id: str | None = None  # Enables tree-based resolution in GraphDB

    start_line: int
    end_line: int

    start_byte: int
    end_byte: int

    metadata: CodeMetadata = CodeMetadata()


class ConfigUnit(BaseUnit):
    config_type: str

    metadata: dict

    is_ast_parsed: bool = False


class DocumentUnit(BaseUnit):
    unit_type: Literal[UnitType.DOCUMENT] = UnitType.DOCUMENT

    document_type: str
    title: str | None = None
