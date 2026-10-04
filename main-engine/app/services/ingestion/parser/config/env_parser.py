from pathlib import Path

from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_env(file_path: str | Path, code_bytes: bytes):

    raw = decode_bytes(code_bytes)

    env = {}

    for line in raw.splitlines():

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        env[key] = value

    return [
        ConfigUnit(
            id=f"{file_path}::<config>",
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="env",
            metadata=env,
            code_content=raw,
        )
    ]
