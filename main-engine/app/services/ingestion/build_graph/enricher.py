import asyncio
from typing import List, Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_groq import ChatGroq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.services.ingestion.models import CodeUnit, ConfigUnit, DocumentUnit, UnitType

AnyUnit = Union[CodeUnit, ConfigUnit, DocumentUnit]


class CodeEnricher:
    """
    Enriches CodeUnit, ConfigUnit, and DocumentUnit objects by generating
    dense summaries and vector embeddings, returning clean, unit-specific payloads.
    Uses ChatGroq as a fallback if ChatMistralAI encounters rate limits or errors.
    """

    def __init__(self, max_concurrency: int = 3):
        # 1. Concurrency control semaphore
        self.semaphore = asyncio.Semaphore(max_concurrency)

        # Primary LLM (Groq)
        primary_llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )

        # Secondary Backup LLM
        fallback_llm = ChatMistralAI(
            model=settings.MISTRAL_LLM_MODEL,
            api_key=settings.MISTRAL_API_KEY,
            temperature=0,
        )

        # 2. Attach Fallback: If primary_llm fails, automatically try fallback_llm
        self.llm_with_fallback = primary_llm.with_fallbacks([fallback_llm])

        # Embedding model
        self.embeddings = MistralAIEmbeddings(
            model=settings.MISTRAL_EMBEDDING_MODEL,
            api_key=settings.MISTRAL_API_KEY,
        )

        self.summary_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a code intelligence indexing engine.\n\n"
                    "Generate a dense technical summary of the provided code unit for semantic retrieval.\n\n"
                    "Rules:\n"
                    "1. Output exactly 2-4 dense sentences in plain text.\n"
                    "2. Describe the unit's primary responsibility and important behavior.\n"
                    "3. Mention important inputs, outputs, side effects, dependencies, and data flow when applicable.\n"
                    "4. Preserve meaningful technical and domain-specific concepts that a developer might search for.\n"
                    "5. Include explicit technology, class, function, API, database, protocol, or framework names when present.\n"
                    "6. Prefer concrete terminology over generic descriptions.\n"
                    "7. Do not invent behavior that is not present in the code.\n"
                    "8. Do not use phrases such as 'This function', 'This class', or 'This module'.\n"
                    "9. Do not use markdown, bullets, headers, or code blocks.\n"
                    "10. Focus on information useful for answering questions about where and how functionality is implemented.",
                ),
                (
                    "user",
                    "Unit Type: {unit_type}\n"
                    "Name/Title: {symbol_name}\n\n"
                    "Content:\n"
                    "{code_content}\n",
                ),
            ]
        )

        # Build chain using the fallback-enabled LLM
        self.summary_chain = self.summary_prompt | self.llm_with_fallback

    @retry(
        wait=wait_exponential(min=2, max=30),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=False,
    )
    async def _call_llm_with_retry(
        self, unit_type: str, symbol_name: str, code_content: str
    ) -> str:
        """Invokes chain with automatic fallback (Mistral -> Groq) and retry backoff."""
        response = await self.summary_chain.ainvoke(
            {
                "unit_type": unit_type,
                "symbol_name": symbol_name,
                "code_content": code_content,
            }
        )
        return response.content.strip()

    def _build_semantic_text(self, unit: AnyUnit, summary: str) -> str:
        if isinstance(unit, CodeUnit):
            imports = [i.imported_name or i.module for i in unit.metadata.imports]

            inheritance = [str(i) for i in unit.metadata.inheritance]

            dependencies = [c.callee for c in unit.metadata.calls if c.callee]

            return "\n".join(
                [
                    f"Symbol: {unit.symbol_name or '<module>'}",
                    f"Qualified name: {unit.qualified_name}",
                    f"Symbol kind: {unit.symbol_kind}",
                    f"File: {unit.file_path}",
                    f"Summary: {summary}",
                    f"Imports: {', '.join(imports)}",
                    f"Dependencies: {', '.join(dependencies)}",
                    f"Inheritance: {', '.join(inheritance)}",
                ]
            )

        elif isinstance(unit, ConfigUnit):
            return "\n".join(
                [
                    f"Unit type: {unit.unit_type.value}",
                    f"Config type: {unit.config_type}",
                    f"File: {unit.file_path}",
                    f"Summary: {summary}",
                ]
            )

        elif isinstance(unit, DocumentUnit):
            return "\n".join(
                [
                    f"Unit type: {unit.unit_type.value}",
                    f"Title: {unit.title or ''}",
                    f"Document type: {unit.document_type}",
                    f"File: {unit.file_path}",
                    f"Summary: {summary}",
                ]
            )

        return summary

    async def _summarize_unit(self, unit: AnyUnit) -> str:
        unit_type = unit.unit_type.value
        symbol_name = (
            getattr(unit, "symbol_name", None)
            or getattr(unit, "title", None)
            or unit.file_path
        )
        content = unit.code_content or ""

        if not content.strip():
            return f"Empty {unit_type} unit at '{unit.file_path}'."

        async with self.semaphore:
            try:
                return await self._call_llm_with_retry(
                    unit_type=unit_type,
                    symbol_name=str(symbol_name),
                    code_content=content,
                )
            except Exception as e:
                print(
                    f"⚠️ Warning: Both Primary (Mistral) and Fallback (Groq) LLMs failed for {unit.file_path}: {e}"
                )
                return f"{unit_type} unit at '{unit.file_path}'."

    async def enrich_units(self, units: List[AnyUnit]) -> List[Dict[str, Any]]:
        if not units:
            return []

        # 1. Generate summaries concurrently across all units
        summary_tasks = [self._summarize_unit(unit) for unit in units]
        summaries = await asyncio.gather(*summary_tasks)

        # 2. Batch embed summaries
        semantic_texts = [
            self._build_semantic_text(unit, summary)
            for unit, summary in zip(units, summaries)
        ]

        embeddings_list = await self.embeddings.aembed_documents(semantic_texts)

        # 3. Construct unit-specific payloads according to type
        enriched_payloads = []
        for unit, summary, embedding in zip(units, summaries, embeddings_list):

            # --- CODE UNIT PAYLOAD ---
            if isinstance(unit, CodeUnit):
                # FIX 1: Use target_symbol_id, not target_unit_id
                calls = [
                    {
                        "target_id": c.target_symbol_id,
                        "method": c.method,
                        "callee": c.callee,
                        "line": c.line,
                        "status": c.resolution_status,
                    }
                    for c in unit.metadata.calls
                    if c.target_symbol_id and c.resolution_status == "RESOLVED"
                ]

                # External calls (e.g., standard library, third-party frameworks)
                external_calls = [
                    {
                        "target_symbol": c.target_symbol_id,
                        "method": c.method,
                        "callee": c.callee,
                        "line": c.line,
                    }
                    for c in unit.metadata.calls
                    if c.target_symbol_id and c.resolution_status == "EXTERNAL"
                ]

                imports = [
                    {
                        "target_id": i.target_unit_id,
                        "imported_name": i.imported_name,
                        "module": i.module,
                        "alias": i.alias,
                    }
                    for i in unit.metadata.imports
                    if i.target_unit_id
                ]

                globals_data = [
                    {
                        "name": g.name,
                        "value": (
                            (g.value[:100] + "...")
                            if g.value and len(g.value) > 100
                            else (g.value or "")
                        ),
                        "line": g.line,
                    }
                    for g in unit.metadata.globals
                ]

                payload = {
                    "unit_type": UnitType.CODE.value,
                    "id": unit.id,
                    "file_path": unit.file_path,
                    "symbol_name": unit.symbol_name or "<module>",
                    "qualified_name": unit.qualified_name,
                    "symbol_kind": unit.symbol_kind,
                    "ast_node_type": unit.ast_node_type,
                    "parent_symbol_id": unit.parent_symbol_id,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "summary": summary,
                    "embedding": embedding,
                    "imports": imports,
                    "globals": globals_data,
                    "calls": calls,
                    "external_calls": external_calls,
                    # Raw class base names extracted by Tree-sitter (e.g. ['User'])
                    "raw_inheritance": [str(i) for i in unit.metadata.inheritance],
                    "overrides": [str(o) for o in unit.metadata.overrides],
                }

            # --- CONFIG UNIT PAYLOAD ---
            elif isinstance(unit, ConfigUnit):
                payload = {
                    "unit_type": UnitType.CONFIG.value,
                    "id": unit.id,  # FIX 2: Use unit's native id
                    "file_path": unit.file_path,
                    "config_type": unit.config_type,
                    "summary": summary,
                    "embedding": embedding,
                    "metadata": unit.metadata,
                }

            # --- DOCUMENT UNIT PAYLOAD ---
            elif isinstance(unit, DocumentUnit):
                payload = {
                    "unit_type": UnitType.DOCUMENT.value,
                    "id": unit.id,  # FIX 2: Use unit's native id
                    "file_path": unit.file_path,
                    "document_type": unit.document_type,
                    "title": unit.title or "",
                    "summary": summary,
                    "embedding": embedding,
                }

            else:
                continue

            enriched_payloads.append(payload)

        return enriched_payloads
