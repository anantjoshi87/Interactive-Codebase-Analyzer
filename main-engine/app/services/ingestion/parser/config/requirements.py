from ..models import ConfigUnit, UnitType


def parse_requirements(file_path, content):

    raw = content.decode()

    packages = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.startswith("#")
    ]

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="requirements",
            metadata={"packages": packages},
            code_content=raw,
        )
    ]
