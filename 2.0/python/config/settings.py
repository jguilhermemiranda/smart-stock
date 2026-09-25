from __future__ import annotations

import json
from pathlib import Path

class Settings:
    def __init__(self, path: str = "smartstock.json") -> None:
        self.path = Path(path)
        self.values = {"esp32_host": "smartstock.local", "esp32_port": 80, "bridge_host": "espbridge.local", "bridge_port": 8899, "role": "administrator"}
        if self.path.exists(): self.values.update(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
