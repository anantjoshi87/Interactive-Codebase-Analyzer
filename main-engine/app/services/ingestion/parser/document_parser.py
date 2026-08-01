from pathlib import Path

from app.services.ingestion.models import DocumentUnit


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
    def supports(cls, file_path: Path) -> bool:
        return (
            file_path.suffix.lower() in cls.SUPPORTED or file_path.name in cls.SUPPORTED
        )

    @classmethod
    def parse(
        cls,
        file_path: Path,
        content: bytes,
    ) -> list[DocumentUnit]:

        text = content.decode("utf-8", errors="ignore")

        title = cls._extract_title(text)

        return [
            DocumentUnit(
                file_path=str(file_path),
                document_type=cls._document_type(file_path),
                title=title,
                code_content=text,
                is_ast_parsed=False,
            )
        ]

    @staticmethod
    def _extract_title(text: str) -> str | None:
        """
        Returns the first markdown heading if present.
        """

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("#"):
                return line.lstrip("#").strip()

        return None

    @staticmethod
    def _document_type(file_path: Path) -> str:

        name = file_path.name.lower()

        if name.startswith("readme"):
            return "readme"

        if name.startswith("license"):
            return "license"

        if name.startswith("contributing"):
            return "contributing"

        if name.startswith("changelog"):
            return "changelog"

        if file_path.suffix.lower() == ".md":
            return "markdown"

        if file_path.suffix.lower() == ".rst":
            return "restructuredtext"

        if file_path.suffix.lower() == ".txt":
            return "text"

        return "document"
