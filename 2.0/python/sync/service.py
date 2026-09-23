from __future__ import annotations

import hashlib
import json
from typing import Any

from api.client import DeviceClient
from database.db import Database

class SyncService:
    def __init__(self, database: Database, device: DeviceClient) -> None:
        self.database = database
        self.device = device

    @staticmethod
    def canonical_content(payload: dict[str, Any]) -> str:
        return "".join(json.dumps(payload[key], separators=(",", ":"), ensure_ascii=True) for key in ("machine_config", "drawers", "cards"))

    def build_payload(self) -> dict[str, Any]:
        payload = self.database.export_payload()
        payload["version_hash"] = hashlib.sha256(self.canonical_content(payload).encode()).hexdigest()
        return payload

    def synchronize(self) -> dict:
        payload = self.build_payload()
        result = self.device.sync(payload)
        self.database.execute("INSERT INTO sync_log (version_hash, status, detail) VALUES (?, ?, ?)", (payload["version_hash"], "success", json.dumps(result)))
        return result
