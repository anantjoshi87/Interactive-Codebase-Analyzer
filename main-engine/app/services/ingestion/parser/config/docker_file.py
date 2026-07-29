from ..models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_dockerfile(file_path, content):

    raw = decode_bytes(content)

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="dockerfile",
            metadata={},
            code_content=raw,
        )
    ]
