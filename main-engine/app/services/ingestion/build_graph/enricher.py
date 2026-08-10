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

from app.core.config import Settings
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

        # Primary LLM (Mistral)
        primary_llm = ChatMistralAI(
            model=Settings.MISTRAL_LLM_MODEL,
            api_key=Settings.MISTRAL_API_KEY,
            temperature=0,
        )

        # Secondary Backup LLM (Groq)
        fallback_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=Settings.GROQ_API_KEY,
            temperature=0,
        )

        # 2. Attach Fallback: If primary_llm fails, automatically try fallback_llm
        self.llm_with_fallback = primary_llm.with_fallbacks([fallback_llm])

        # Embedding model
        self.embeddings = MistralAIEmbeddings(
            model=Settings.MISTRAL_EMBEDDING_MODEL,
            api_key=Settings.MISTRAL_API_KEY,
        )

        self.summary_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert static analysis engine generating dense summaries for indexing.\n\n"
                    "Generate a technical summary optimized for semantic vector retrieval. "
                    "Adhere strictly to these rules:\n"
                    "1. Output exactly 2-3 dense sentences in plain text.\n"
                    "2. State the core purpose, key configuration or logic, and operational effects.\n"
                    "3. Mention explicit technical keywords.\n"
                    "4. NEVER use fluff or intro phrases ('This function...', 'This module...').\n"
                    "5. Do NOT use markdown headers, bullet points, or code blocks.",
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
                "code_content": code_content[
                    :4000
                ],  # Truncate to prevent token overflow
            }
        )
        return response.content.strip()

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
        embeddings_list = await self.embeddings.aembed_documents(list(summaries))

        # 3. Construct unit-specific payloads according to type
        enriched_payloads = []
        for unit, summary, embedding in zip(units, summaries, embeddings_list):

            # --- CODE UNIT PAYLOAD ---
            if isinstance(unit, CodeUnit):
                calls = [
                    {"target_id": c.target_unit_id, "method": c.method, "line": c.line}
                    for c in unit.metadata.calls
                    if c.target_unit_id
                ]
                imports = [
                    {"target_id": i.target_unit_id, "imported_name": i.imported_name}
                    for i in unit.metadata.imports
                    if i.target_unit_id
                ]

                # --- NEW: Extract Inheritance and Overrides ---
                # We use getattr() safely in case they are stored as strings
                # instead of objects in your AST parser output.
                inheritance = [
                    getattr(i, "target_unit_id", i)
                    for i in unit.metadata.inheritance
                    if getattr(i, "target_unit_id", i)
                ]

                overrides = [
                    getattr(o, "target_unit_id", o)
                    for o in unit.metadata.overrides
                    if getattr(o, "target_unit_id", o)
                ]
                # ----------------------------------------------

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
                    "inheritance": inheritance,  # Added to payload
                    "overrides": overrides,  # Added to payload
                }

            # --- CONFIG UNIT PAYLOAD ---
            elif isinstance(unit, ConfigUnit):
                payload = {
                    "unit_type": UnitType.CONFIG.value,
                    "id": f"{unit.file_path}::<config>",
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
                    "id": f"{unit.file_path}::<doc>",
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
