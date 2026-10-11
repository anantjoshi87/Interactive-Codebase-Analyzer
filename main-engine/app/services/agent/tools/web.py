import os
import asyncio
from typing import Any, Dict, List
from langchain_core.tools import tool
from app.core.config import settings

try:
    from langchain_tavily import TavilySearch

    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from ddgs import DDGS

    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False


class WebTools:
    """Agent-facing tools for searching external web sources."""

    def __init__(self):
        self.tavily_api_key = settings.TAVILY_API_KEY

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Executes a technical web search. Prefers Tavily if API key is configured,
        otherwise falls back to DuckDuckGo search.
        """
        max_results = min(max(1, max_results), 5)

        # 1. Tavily Search (Best for LLM context ingestion)
        if TAVILY_AVAILABLE and self.tavily_api_key:
            try:
                tavily = TavilySearch(
                    search_depth="advanced",
                    max_results=max_results,
                    include_answer=True,
                )
                response = await tavily.ainvoke({"query": query})
                results = []
                # Include quick direct answer if Tavily synthesized one
                if response.get("answer"):
                    results.append(
                        {
                            "title": "Direct Synthesis",
                            "url": "https://tavily.com",
                            "content": response["answer"],
                        }
                    )

                for item in response.get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                        }
                    )
                return results
            except Exception as e:
                print(f"⚠️ Tavily Search error, trying fallback: {e}")

        # 2. DuckDuckGo Fallback (Free, zero-config)
        if DDG_AVAILABLE:
            try:
                # DDGS is synchronous, so keep it off the async event loop.
                raw_results = await asyncio.to_thread(
                    lambda: list(DDGS().text(query, max_results=max_results))
                )
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "content": r.get("body", ""),
                    }
                    for r in raw_results
                ]
            except Exception as e:
                return [{"error": f"Web search failed: {str(e)}"}]

        return [
            {
                "error": "No search provider available. Install 'langchain-tavily' or 'ddgs'."
            }
        ]


def build_web_tools():
    """Creates LangChain tools for external web searches."""
    service = WebTools()

    return [
        tool(
            "web_search",
            description=(
                "Search the public web for official documentation, library guides, "
                "third-party API references, and open-source package issues. "
                "Use this for external tools, packages, or concepts not defined "
                "within the repository codebase."
            ),
        )(service.search_web)
    ]
