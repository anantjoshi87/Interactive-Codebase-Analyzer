import json
from ..models import ConfigUnit, UnitType


def parse_package_json(file_path, content):

    raw = content.decode("utf-8", errors="ignore")

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
