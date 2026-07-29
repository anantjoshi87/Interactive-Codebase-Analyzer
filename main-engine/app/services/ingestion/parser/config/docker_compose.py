from ..models import ConfigUnit, UnitType
import yaml
from .utils import decode_bytes

def parse_docker_compose(file_path, content):

    raw = decode_bytes(content)

    data = yaml.safe_load(raw)

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="docker_compose",
            metadata=data,
            code_content=raw,
        )
    ]