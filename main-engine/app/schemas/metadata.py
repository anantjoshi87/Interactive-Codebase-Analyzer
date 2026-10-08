from typing import Optional
from pydantic import BaseModel, Field


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
