from typing import Any, Type
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
