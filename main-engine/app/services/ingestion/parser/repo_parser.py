import os
from pathlib import Path
import traceback
from typing import Optional

from .ast_parser import TreeSitterParser
from .fallback_chunker import FallbackChunker
from .language_registry import LanguageRegistry
from .config_parser import ConfigParser
from .document_parser import DocumentParser
from .constants import (
    DEFAULT_IGNORED_DIRS,
    DEFAULT_IGNORED_EXTS,
)

from .models import BaseUnit


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

        extracted_units = []

        for root, _, files in os.walk(repo_path):

            if any(ignored in root for ignored in self.ignored_dirs):
                continue

            for file in files:

                file_path = Path(root) / file
                extension = file_path.suffix.lower()

                if extension in self.ignored_extensions:
                    continue

                relative_path = str(file_path.relative_to(repo_path))

                try:
                    with open(file_path, "rb") as f:
                        code = f.read()

                    config = self.registry.get(extension)

                    if config:
                        extracted_units.extend(
                            self.ast_parser.parse(
                                relative_path,
                                code,
                                config,
                            )
                        )

                    elif self.config_parser.supports(file_path):

                        extracted_units.extend(
                            self.config_parser.parse(
                                file_path,
                                code,
                            )
                        )

                    elif self.document_parser.supports(file_path):
                        extracted_units.extend(
                            self.document_parser.parse(
                                file_path,
                                code,
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
