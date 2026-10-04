from pathlib import Path

from app.services.ingestion.models import ConfigUnit, UnitType
import yaml
from .utils import decode_bytes


def parse_docker_compose(file_path: str | Path, code_bytes: bytes):

    raw = decode_bytes(code_bytes)

    data = yaml.safe_load(raw)

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="docker_compose",
            metadata=data,
            code_content=raw,
        )
    ]
