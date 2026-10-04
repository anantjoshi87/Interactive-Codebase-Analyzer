from pathlib import Path

from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_dockerfile(file_path: str | Path, code_bytes: bytes):

    raw = decode_bytes(code_bytes)

    return [
        ConfigUnit(
            id=f"{file_path}::<config>",
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="dockerfile",
            metadata={},
            code_content=raw,
        )
    ]
