from pathlib import Path

from app.schemas import AnyUnit
from app.services.ingestion.extraction.parsers import RepoParser
from app.services.ingestion.resolution import RepoResolver
from app.services.ingestion.graph import CodeEnricher, GraphSync


class IngestionPipeline:
    """End-to-end ingestion pipeline for parsing the code from a repository, resolving SCIP symbols, and enriching with LLM summaries, embeddings, and cross-unit links, building a knowledge graph."""

    # will be built later wile implementing docker
    pass
