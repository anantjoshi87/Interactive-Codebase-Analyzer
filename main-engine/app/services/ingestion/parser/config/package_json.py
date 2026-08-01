import json
from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_package_json(file_path, content):

    raw = decode_bytes(content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return [
        ConfigUnit(
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
