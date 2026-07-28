from ..models import ConfigUnit, UnitType


def parse_dockerfile(file_path, content):

    raw = content.decode()

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="dockerfile",
            metadata={},
            code_content=raw,
        )
    ]
