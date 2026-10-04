import tomllib
from pathlib import Path
from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_pyproject(file_path: str | Path, code_bytes: bytes):

    data = tomllib.loads(decode_bytes(code_bytes))

    return [
        ConfigUnit(
            id=f"{file_path}::<config>",
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="pyproject",
            metadata=data,
            code_content=code_bytes.decode("utf-8", errors="ignore"),
        )
    ]
