import re
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from langchain_mistralai import MistralAIEmbeddings

from app.core.config import settings
from app.db.neo4j.neo4j_repository import CodebaseRepository
from app.services.reranker import JinaAPIReranker


class HybridCodeSearch:
    def __init__(
        self,
        repository: CodebaseRepository,
        reranker: Optional[JinaAPIReranker] = None,
    ):
        self.repository = repository
        self.reranker = reranker or JinaAPIReranker()
        self.embeddings = MistralAIEmbeddings(
            model=settings.MISTRAL_EMBEDDING_MODEL,
            api_key=settings.MISTRAL_API_KEY,
        )

    @staticmethod
    def _sanitize_lucene_query(text: str) -> str:
        """
        Strips Lucene special operators and formats terms with OR logic
        to prevent syntax exceptions on natural language queries.
        """
        # Remove Lucene reserved syntax characters: + - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
        cleaned = re.sub(r"[\+\-\&\|\!\(\)\{\}\[\]\^\"~*\?\:\\/]", " ", text)
        words = [w.strip() for w in cleaned.split() if len(w.strip()) > 1]
        if not words:
            return "*"
        # Join as an OR query: 'find OR user OR profile'
        return " OR ".join(words)

    async def search(
        self,
        query: str,
        top_k: int = 8,
    ) -> List[Dict[str, Any]]:
        # Candidate pool: pull 2x-3x top_k to give the cross-encoder sufficient candidates
        candidate_k = max(top_k * 3, 15)

        # 1. Embed query
        query_embedding = await self.embeddings.aembed_query(query)

        # 2. Vector search in Neo4j
        vector_results = self.repository.vector_search(
            embedding=query_embedding,
            top_k=candidate_k,
        )

        # 3. Lucene Fulltext search in Neo4j
        safe_keyword_query = self._sanitize_lucene_query(query)
        keyword_results = self.repository.keyword_search(
            query_text=safe_keyword_query,
            top_k=candidate_k,
        )

        # 4. Stage 1: Fast Heuristic Fusion (RRF) to deduplicate & select top candidate pool
        rrf_candidates = self._rrf_merge(
            vector_results=vector_results,
            keyword_results=keyword_results,
            k=60,
        )

        if not rrf_candidates:
            return []

        # 5. Stage 2: Neural Cross-Encoder Reranking via Jina
        # Convert candidates to LangChain Documents for the reranker
        documents_to_rerank = [
            Document(
                page_content=(
                    f"Symbol: {c['qualified_name']} ({c['symbol_kind']})\n"
                    f"File: {c['file_path']}\n"
                    f"Summary: {c['summary'] or ''}"
                ),
                metadata=c,
            )
            for c in rrf_candidates[:candidate_k]
        ]

        reranked_docs = await self.reranker.rerank_documents(
            query=query,
            documents=documents_to_rerank,
            top_n=top_k,
            min_score=0.40,  # Filter out low-confidence hallucinations
        )

        # Format final output
        final_results = []
        for doc in reranked_docs:
            meta = doc.metadata
            final_results.append(
                {
                    "id": meta.get("id"),
                    "qualified_name": meta.get("qualified_name"),
                    "symbol_name": meta.get("symbol_name"),
                    "file_path": meta.get("file_path"),
                    "symbol_kind": meta.get("symbol_kind"),
                    "summary": meta.get("summary"),
                    "score": meta.get("rerank_score", meta.get("score", 0.0)),
                }
            )

        return final_results

    @staticmethod
    def _rrf_merge(
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        scores: Dict[str, float] = {}
        nodes: Dict[str, Dict[str, Any]] = {}

        def process_results(results: List[Dict[str, Any]]):
            for rank, result in enumerate(results, start=1):
                raw_node = result.get("node")
                if not raw_node:
                    continue
                node = dict(raw_node)
                node_id = node.get("id")
                if not node_id:
                    continue

                scores[node_id] = scores.get(node_id, 0.0) + (1.0 / (k + rank))
                nodes[node_id] = node

        process_results(vector_results)
        process_results(keyword_results)

        ranked_ids = sorted(scores, key=scores.get, reverse=True)

        return [
            {
                "id": nodes[node_id].get("id"),
                "qualified_name": nodes[node_id].get("qualified_name"),
                "symbol_name": nodes[node_id].get("symbol_name"),
                "file_path": nodes[node_id].get("file_path"),
                "symbol_kind": nodes[node_id].get("symbol_kind"),
                "summary": nodes[node_id].get("summary"),
                "score": scores[node_id],
            }
            for node_id in ranked_ids
        ]
