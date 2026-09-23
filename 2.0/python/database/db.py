from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS cards (
 id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT UNIQUE NOT NULL,
 owner_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', notes TEXT,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS drawers (
 id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, pos_x_mm REAL,
 pos_y_mm REAL, pos_z_mm REAL, calibrated BOOLEAN NOT NULL DEFAULT 0, notes TEXT,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS card_drawer_permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER NOT NULL, drawer_id INTEGER NOT NULL,
 UNIQUE(card_id, drawer_id), FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
 FOREIGN KEY(drawer_id) REFERENCES drawers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS drawer_inventory (
 id INTEGER PRIMARY KEY AUTOINCREMENT, drawer_id INTEGER NOT NULL,
 item_name TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0,
 notes TEXT, UNIQUE(drawer_id, item_name),
 FOREIGN KEY(drawer_id) REFERENCES drawers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS machine_config (
 id INTEGER PRIMARY KEY CHECK (id = 1), drawer_count INTEGER NOT NULL DEFAULT 18,
 steps_per_mm_x REAL NOT NULL DEFAULT 1, steps_per_mm_y REAL NOT NULL DEFAULT 1,
 steps_per_mm_z REAL NOT NULL DEFAULT 1, step_delay_us INTEGER NOT NULL DEFAULT 1000,
 comm_timeout_ms INTEGER NOT NULL DEFAULT 5000, accel_enabled BOOLEAN NOT NULL DEFAULT 0,
 accel_steps_per_s2 REAL
);
CREATE TABLE IF NOT EXISTS network_config (
 id INTEGER PRIMARY KEY CHECK (id = 1), esp32_host TEXT, esp32_port INTEGER DEFAULT 80,
 device_name TEXT
);
CREATE TABLE IF NOT EXISTS sync_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, version_hash TEXT NOT NULL,
 synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL, detail TEXT
);
"""

class Database:
    def __init__(self, path: str | Path = "smartstock.db") -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.execute("INSERT OR IGNORE INTO machine_config (id) VALUES (1)")
        self.connection.execute("INSERT OR IGNORE INTO network_config (id, esp32_host) VALUES (1, 'smartstock.local')")
        self.connection.commit()

    def rows(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(query, params).fetchall()]

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        cursor = self.connection.execute(query, params)
        self.connection.commit()
        return int(cursor.lastrowid or 0)

    def card_payload(self) -> list[dict[str, Any]]:
        cards = self.rows("SELECT id, uid, owner_name, status, notes FROM cards ORDER BY id")
        for card in cards:
            card["drawer_ids"] = [row["drawer_id"] for row in self.connection.execute(
                "SELECT drawer_id FROM card_drawer_permissions WHERE card_id = ? ORDER BY drawer_id", (card["id"],)
            )]
        return cards

    def drawer_inventory(self, drawer_id: int) -> list[dict[str, Any]]:
        return self.rows("SELECT item_name, quantity, notes FROM drawer_inventory WHERE drawer_id = ? ORDER BY item_name", (drawer_id,))

    def authorized_owners(self, drawer_id: int) -> list[str]:
        rows = self.rows(
            "SELECT c.owner_name FROM cards c JOIN card_drawer_permissions p ON p.card_id = c.id "
            "WHERE p.drawer_id = ? AND c.status = 'active' ORDER BY c.owner_name", (drawer_id,)
        )
        return [row["owner_name"] for row in rows]

    def export_payload(self) -> dict[str, Any]:
        machine = self.rows("SELECT drawer_count, steps_per_mm_x, steps_per_mm_y, steps_per_mm_z, step_delay_us, comm_timeout_ms, accel_enabled, accel_steps_per_s2 FROM machine_config WHERE id=1")[0]
        config = {
            "drawer_count": machine["drawer_count"],
            "steps_per_mm": {"x": machine["steps_per_mm_x"], "y": machine["steps_per_mm_y"], "z": machine["steps_per_mm_z"]},
            "step_delay_us": machine["step_delay_us"], "comm_timeout_ms": machine["comm_timeout_ms"],
            "accel_enabled": machine["accel_enabled"], "accel_steps_per_s2": machine["accel_steps_per_s2"],
        }
        drawers = self.rows("SELECT id, label, pos_x_mm AS x_mm, pos_y_mm AS y_mm, pos_z_mm AS z_mm, calibrated, notes FROM drawers ORDER BY id")
        for drawer in drawers:
            drawer["items"] = self.drawer_inventory(drawer["id"])
            drawer["authorized_owners"] = self.authorized_owners(drawer["id"])
        return {"machine_config": config, "drawers": drawers, "cards": self.card_payload()}

    def close(self) -> None:
        self.connection.close()
