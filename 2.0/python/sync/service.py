from __future__ import annotations

import hashlib
import json
from typing import Any

from api.client import DeviceClient, DeviceError
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
        self.database.set_sync_state("pending", payload["version_hash"])
        try:
            result = self.device.sync(payload)
            if not isinstance(result, dict) or result.get("ok") is not True:
                raise DeviceError("ESP32 did not confirm synchronization")
        except Exception as exc:
            self.database.set_sync_state("failed", payload["version_hash"], str(exc))
            raise
        self.database.set_sync_state("success", payload["version_hash"], json.dumps(result))
        self.database.execute("INSERT INTO sync_log (version_hash, status, detail) VALUES (?, ?, ?)", (payload["version_hash"], "success", json.dumps(result)))
        return result

    def pull_from_device(self) -> dict[str, Any]:
        remote = self.device.config()
        cards = remote.get("cards", [])
        drawers = remote.get("drawers", [])
        with self.database.connection:
            self.database.set_machine_config(remote.get("machine_config", {}))
            self.database.connection.execute("DELETE FROM card_drawer_permissions")
            self.database.connection.execute("DELETE FROM drawer_inventory")
            self.database.connection.execute("DELETE FROM cards")
            self.database.connection.execute("DELETE FROM drawers")
            for drawer in drawers:
                position = drawer.get("position", {})
                self.database.connection.execute(
                    "INSERT INTO drawers (id, label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated) VALUES (?, ?, ?, ?, ?, ?)",
                    (drawer["id"], drawer["label"], position.get("x_mm"), position.get("y_mm"), position.get("z_mm"), int(drawer.get("calibrated", False))),
                )
                for item in drawer.get("inventory", []):
                    self.database.connection.execute(
                        "INSERT INTO drawer_inventory (drawer_id, item_name, quantity) VALUES (?, ?, ?)",
                        (drawer["id"], item["item_name"], item.get("quantity", 0)),
                    )
            for card in cards:
                self.database.connection.execute(
                    "INSERT INTO cards (uid, owner_name, status, attributes_json) VALUES (?, ?, ?, ?)",
                    (card["uid"], card.get("owner_name", ""), card.get("status", "active"), json.dumps(card.get("attributes", {}), ensure_ascii=False)),
                )
                card_id = self.database.connection.execute("SELECT id FROM cards WHERE uid = ?", (card["uid"],)).fetchone()[0]
                for drawer_id in card.get("drawer_ids", []):
                    self.database.connection.execute(
                        "INSERT OR IGNORE INTO card_drawer_permissions (card_id, drawer_id) VALUES (?, ?)",
                        (card_id, drawer_id),
                    )
        return {"ok": True, "drawers": len(drawers), "cards": len(cards)}
