from ..models import ConfigUnit, UnitType


def parse_env(file_path, content):

    raw = content.decode()

    env = {}

    for line in raw.splitlines():

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        env[key] = value

    return [
        ConfigUnit(
            file_path=str(file_path),
            unit_type=UnitType.CONFIG,
            config_type="env",
            metadata=env,
            code_content=raw,
        )
    ]
