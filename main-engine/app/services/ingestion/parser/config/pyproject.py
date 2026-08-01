import tomllib

from app.services.ingestion.models import ConfigUnit, UnitType
from .utils import decode_bytes

def parse_pyproject(file_path, content):

    data = tomllib.loads(decode_bytes(content))

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="pyproject",
            metadata=data,
            code_content=content.decode(),
        )
    ]
