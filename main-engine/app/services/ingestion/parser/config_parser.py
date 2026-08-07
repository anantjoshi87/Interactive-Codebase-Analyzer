from pathlib import Path

from app.services.ingestion.models import ConfigUnit
from .config import (
    parse_package_json,
    parse_env,
    parse_requirements,
    parse_dockerfile,
    parse_pyproject,
    parse_docker_compose,
)


class ConfigParser:

    PARSERS = {
        "package.json": parse_package_json,
        "pyproject.toml": parse_pyproject,
        "requirements.txt": parse_requirements,
        "Dockerfile": parse_dockerfile,
        "docker-compose.yml": parse_docker_compose,
        "docker-compose.yaml": parse_docker_compose,
        ".env": parse_env,
        ".env.example": parse_env,
    }

    @classmethod
    def supports(cls, file_path: Path) -> bool:
        return file_path.name in cls.PARSERS

    @classmethod
    def parse(cls, file_path: Path, code_bytes: bytes):
        # Convert string to Path object to access .name safely
        path_obj = Path(file_path)

        parser = cls.PARSERS.get(path_obj.name)
        if parser is None:
            return []

        return parser(file_path, code_bytes)
