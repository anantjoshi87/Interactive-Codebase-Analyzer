from enum import Enum
from typing import Literal
from pydantic import BaseModel
from tree_sitter import Language


class LanguageConfig(BaseModel):
    language: Language

    symbol_query: str
    import_query: str
    global_query: str

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
    value: str | None = None
    line: int | None = None


class Reference(BaseModel):
    name: str
    kind: str | None = None
    target_unit_id: str | None = None


class CallReference(BaseModel):
    callee: str
    target_unit_id: str | None = None
    line: int | None = None
    column: int | None = None


class CodeMetadata(BaseModel):
    imports: list[ImportReference] = []
    globals: list[GlobalVariable] = []
    decorators: list[str] = []
    parent_class: str | None = None
    docstring: str | None = None
    calls: list[CallReference] = []
    references: list[Reference] = []
    inheritance: list[str] = []
    overrides: list[str] = []
    annotations: list[str] = []
    exceptions: list[str] = []
    returns: str | None = None


class CodeUnit(BaseUnit):
    id: str  # e.g. app/services/parser/repo_parser.py::RepoParser.parse_repository

    symbol_name: str | None = None
    symbol_kind: str
    ast_node_type: str

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
