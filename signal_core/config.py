from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path("config/sources.yaml")


@dataclass
class SourceConfig:
    name: str
    type: str
    category: str
    url: str = ""


def load_sources(path: Path = DEFAULT_CONFIG_PATH) -> list[SourceConfig]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [
        SourceConfig(
            name=src["name"],
            type=src["type"],
            category=src["category"],
            url=src.get("url", ""),
        )
        for src in data["sources"]
    ]
