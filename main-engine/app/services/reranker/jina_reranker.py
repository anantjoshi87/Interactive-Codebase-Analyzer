# app/services/reranker.py
from typing import List, Optional
import httpx
from langchain_core.documents import Document

from app.core.config import settings


class JinaAPIReranker:

    def __init__(
        self,
        model: str = "jina-reranker-v2-base-multilingual",
        top_n: int = 5,
        min_score: float = 0.50,
        timeout: float = 30.0,
    ):
        self.api_key = settings.JINA_API_KEY
        if not self.api_key:
            raise ValueError("JINA_API_KEY environment variable is not set.")

        self.model = model
        self.default_top_n = top_n
        self.default_min_score = min_score
        self.timeout = timeout
        self.url = "https://api.jina.ai/v1/rerank"

    async def rerank_documents(
        self,
        query: str,
        documents: List[Document],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Document]:
        """Reranks LangChain Document objects using Jina API.

        Discards documents whose relevance_score falls below min_score.
        """
        if not documents:
            return []

        n = top_n if top_n is not None else self.default_top_n
        n = min(n, len(documents))
        cutoff = min_score if min_score is not None else self.default_min_score

        doc_texts = [doc.page_content for doc in documents]

        payload = {
            "model": self.model,
            "query": query,
            "documents": doc_texts,
            "top_n": n,
            "return_documents": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(self.url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                print(f"⚠️ Jina Reranker API Error: {e.response.text}")
                return documents[:n]
            except Exception as e:
                print(f"⚠️ Jina Reranker Network Error: {e}")
                return documents[:n]

        reranked_docs: List[Document] = []
        for result in data.get("results", []):
            score = float(result["relevance_score"])

            # -------------------------------------------------------------
            # Threshold Filter: Skip items that do not meet the minimum score
            # -------------------------------------------------------------
            if score < cutoff:
                continue

            idx = result["index"]
            original_doc = documents[idx]

            updated_metadata = dict(original_doc.metadata)
            updated_metadata["rerank_score"] = score

            reranked_docs.append(
                Document(
                    page_content=original_doc.page_content,
                    metadata=updated_metadata,
                )
            )

        return reranked_docs
