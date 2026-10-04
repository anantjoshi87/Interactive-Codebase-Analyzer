# Parses Markdown, READMEs, Docs

from pathlib import Path
from app.schemas import DocumentUnit, UnitType


class DocumentParser:
    """Parses documentation files into DocumentUnit objects."""

    SUPPORTED = {
        ".md",
        ".txt",
        ".rst",
        ".adoc",
        ".mdx",
        "LICENSE",
        "LICENSE.txt",
        "README",
        "README.md",
        "README.rst",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
    }

    @classmethod
    def supports(cls, file_path: str | Path) -> bool:
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        return (
            path_obj.suffix.lower() in cls.SUPPORTED or path_obj.name in cls.SUPPORTED
        )

    @classmethod
    def parse(
        cls,
        file_path: str | Path,
        content: bytes,
    ) -> list[DocumentUnit]:

        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        text = content.decode("utf-8", errors="ignore")
        title = cls._extract_title(text)

        return [
            DocumentUnit(
                id=f"{path_obj}::<doc>",
                file_path=str(path_obj),
                unit_type=UnitType.DOCUMENT,
                document_type=cls._document_type(path_obj),
                title=title,
                code_content=text,
                is_ast_parsed=False,
            )
        ]

    @staticmethod
    def _extract_title(text: str) -> str | None:
        """Returns the first markdown heading if present."""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return None

    @staticmethod
    def _document_type(file_path: str | Path) -> str:
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        name = path_obj.name.lower()

        if name.startswith("readme"):
            return "readme"
        if name.startswith("license"):
            return "license"
        if name.startswith("contributing"):
            return "contributing"
        if name.startswith("changelog"):
            return "changelog"

        suffix = path_obj.suffix.lower()
        if suffix == ".md":
            return "markdown"
        if suffix == ".rst":
            return "restructuredtext"
        if suffix == ".txt":
            return "text"

        return "document"
