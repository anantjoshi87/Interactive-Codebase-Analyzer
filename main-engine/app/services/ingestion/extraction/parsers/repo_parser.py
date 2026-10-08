# Walks file tree and delegates to sub-parsers

from pathlib import Path
import os
import traceback
from typing import Optional

from app.services.ingestion.extraction.parsers import (
    TreeSitterParser,
    FallbackChunker,
    ConfigParser,
    DocumentParser,
)
from app.services.ingestion.grammars import (
    LanguageRegistry,
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_EXTS,
)
from app.schemas import BaseUnit


class RepoParser:
    """Walks a repository and delegates parsing to the appropriate parser."""

    def __init__(
        self,
        ignored_dirs: Optional[set[str]] = None,
        ignored_extensions: Optional[set[str]] = None,
    ):
        self.ignored_dirs = ignored_dirs or DEFAULT_IGNORED_DIRS
        self.ignored_extensions = ignored_extensions or DEFAULT_IGNORED_EXTS

        self.registry = LanguageRegistry.get()
        self.ast_parser = TreeSitterParser()
        self.config_parser = ConfigParser()
        self.document_parser = DocumentParser()
        self.fallback_parser = FallbackChunker()

    def parse_repository(self, repo_path: str) -> list[BaseUnit]:

        # 1. Convert the repo_path to an absolute path immediately
        abs_repo_path = Path(repo_path).resolve()

        extracted_units = []

        # 2. Walk the absolute path
        for root, _, files in os.walk(abs_repo_path):

            if any(ignored in root for ignored in self.ignored_dirs):
                continue

            for file in files:

                # file_path is now an absolute path (e.g., /Users/name/repo/service.py)
                file_path = Path(root) / file
                extension = file_path.suffix.lower()

                if extension in self.ignored_extensions:
                    continue

                # You can still compute the relative path if you need it for clean IDs
                relative_path = str(file_path.relative_to(abs_repo_path))

                # If you want to use the absolute path in your parsers, cast it to string:
                # abs_file_path_str = str(file_path)

                try:
                    with open(file_path, "rb") as f:
                        code = f.read()

                    config = self.registry.get(extension)

                    if config:
                        extracted_units.extend(
                            self.ast_parser.parse(
                                relative_path=relative_path,
                                code_bytes=code,
                                lang_config=config,
                            )
                        )
                    elif self.config_parser.supports(file_path):
                        extracted_units.extend(
                            self.config_parser.parse(
                                file_path=relative_path,
                                code_bytes=code,
                            )
                        )
                    elif self.document_parser.supports(file_path):
                        extracted_units.extend(
                            self.document_parser.parse(
                                file_path=relative_path,
                                content=code,
                            )
                        )

                    # else:
                    #     extracted_units.extend(
                    #         self.fallback_parser.parse(
                    #             relative_path,
                    #             code.decode("utf-8", errors="ignore"),
                    #         )
                    #     )

                except Exception:
                    print(f"\nError parsing {relative_path}")
                    traceback.print_exc()

        return extracted_units
