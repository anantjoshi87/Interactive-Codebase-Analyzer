import json
from pathlib import Path

from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_package_json(file_path: str | Path, code_bytes: bytes):

    raw = decode_bytes(code_bytes)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return [
        ConfigUnit(
            id=f"{file_path}::<config>",
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="package_json",
            metadata={
                "dependencies": data.get("dependencies", {}),
                "devDependencies": data.get("devDependencies", {}),
                "scripts": data.get("scripts", {}),
            },
            code_content=raw,
        )
    ]
