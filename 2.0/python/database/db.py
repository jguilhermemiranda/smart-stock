from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MACHINE_CONFIG = {
    "drawer_count": 18,
    "steps_per_mm": {"x": 1.0, "y": 1.0, "z": 1.0},
}


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.path = Path(path) if path is not None else base_dir / "database.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL UNIQUE,
                owner_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                attributes_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS drawers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL UNIQUE,
                pos_x_mm REAL,
                pos_y_mm REAL,
                pos_z_mm REAL,
                calibrated INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS drawer_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drawer_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                UNIQUE(drawer_id, item_name),
                FOREIGN KEY(drawer_id) REFERENCES drawers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS card_drawer_permissions (
                card_id INTEGER NOT NULL,
                drawer_id INTEGER NOT NULL,
                PRIMARY KEY(card_id, drawer_id),
                FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY(drawer_id) REFERENCES drawers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS machine_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state TEXT NOT NULL,
                version_hash TEXT,
                detail TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        card_columns = {row["name"] for row in self.rows("PRAGMA table_info(cards)")}
        if "attributes_json" not in card_columns:
            self.connection.execute("ALTER TABLE cards ADD COLUMN attributes_json TEXT NOT NULL DEFAULT '{}'")
        self._migrate_nullable_drawer_positions()
        self.connection.commit()

    def _migrate_nullable_drawer_positions(self) -> None:
        columns = {row["name"]: row for row in self.rows("PRAGMA table_info(drawers)")}
        if not columns or not any(columns[name]["notnull"] for name in ("pos_x_mm", "pos_y_mm", "pos_z_mm")):
            return
        self.connection.execute("PRAGMA foreign_keys = OFF")
        self.connection.execute("PRAGMA legacy_alter_table = ON")
        self.connection.execute("CREATE TABLE drawers_new (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL UNIQUE, pos_x_mm REAL, pos_y_mm REAL, pos_z_mm REAL, calibrated INTEGER NOT NULL DEFAULT 0)")
        self.connection.execute(
            "INSERT INTO drawers_new (id, label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated) "
            "SELECT id, label, CASE WHEN calibrated = 0 AND pos_x_mm = 0 AND pos_y_mm = 0 AND pos_z_mm = 0 THEN NULL ELSE pos_x_mm END, "
            "CASE WHEN calibrated = 0 AND pos_x_mm = 0 AND pos_y_mm = 0 AND pos_z_mm = 0 THEN NULL ELSE pos_y_mm END, "
            "CASE WHEN calibrated = 0 AND pos_x_mm = 0 AND pos_y_mm = 0 AND pos_z_mm = 0 THEN NULL ELSE pos_z_mm END, calibrated FROM drawers"
        )
        self.connection.execute("DROP TABLE drawers")
        self.connection.execute("ALTER TABLE drawers_new RENAME TO drawers")
        self.connection.execute("PRAGMA legacy_alter_table = OFF")
        self.connection.execute("PRAGMA foreign_keys = ON")

    def machine_config(self) -> dict[str, Any]:
        row = self.connection.execute("SELECT config_json FROM machine_config WHERE id = 1").fetchone()
        if not row: return json.loads(json.dumps(DEFAULT_MACHINE_CONFIG))
        try:
            config = json.loads(row["config_json"])
        except json.JSONDecodeError:
            config = {}
        steps = config.get("steps_per_mm", {})
        return {
            "drawer_count": config.get("drawer_count", 18),
            "steps_per_mm": {
                "x": config.get("steps_per_mm_x", steps.get("x", 1.0)),
                "y": config.get("steps_per_mm_y", steps.get("y", 1.0)),
                "z": config.get("steps_per_mm_z", steps.get("z", 1.0)),
            },
        }

    def set_machine_config(self, config: dict[str, Any]) -> None:
        steps = config.get("steps_per_mm", {})
        normalized = {
            "drawer_count": config.get("drawer_count", 18),
            "steps_per_mm": {
                "x": config.get("steps_per_mm_x", steps.get("x", 1.0)),
                "y": config.get("steps_per_mm_y", steps.get("y", 1.0)),
                "z": config.get("steps_per_mm_z", steps.get("z", 1.0)),
            },
        }
        self.connection.execute(
            "INSERT INTO machine_config (id, config_json) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET config_json = excluded.config_json",
            (json.dumps(normalized),),
        )
        self.connection.commit()

    def set_machine_config_pending(self, config: dict[str, Any], previous_drawer_count: int | None = None) -> None:
        steps = config.get("steps_per_mm", {})
        normalized = {
            "drawer_count": config.get("drawer_count", 18),
            "steps_per_mm": {
                "x": config.get("steps_per_mm_x", steps.get("x", 1.0)),
                "y": config.get("steps_per_mm_y", steps.get("y", 1.0)),
                "z": config.get("steps_per_mm_z", steps.get("z", 1.0)),
            },
        }
        with self.connection:
            self.connection.execute(
                "INSERT INTO machine_config (id, config_json) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET config_json = excluded.config_json",
                (json.dumps(normalized),),
            )
            if previous_drawer_count is not None and normalized["drawer_count"] > previous_drawer_count:
                for drawer_id in range(previous_drawer_count + 1, normalized["drawer_count"] + 1):
                    self.connection.execute(
                        "INSERT OR IGNORE INTO drawers (id, label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated) VALUES (?, ?, ?, ?, ?, 0)",
                        (drawer_id, f"Gaveta {drawer_id:02d}", None, None, None),
                    )
            self._set_sync_state_in_transaction("pending", None, "Local change pending synchronization")

    def insert_drawer_pending(self, label: str) -> int:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO drawers (label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated) VALUES (?, ?, ?, ?, 0)",
                (label, None, None, None),
            )
            self._set_sync_state_in_transaction("pending", None, "Local change pending synchronization")
            return int(cursor.lastrowid)

    def update_drawer_pending(self, drawer_id: int, label: str, position: tuple[float | None, float | None, float | None], calibrated: int) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE drawers SET label = ?, pos_x_mm = ?, pos_y_mm = ?, pos_z_mm = ?, calibrated = ? WHERE id = ?",
                (label, *position, calibrated, drawer_id),
            )
            self._set_sync_state_in_transaction("pending", None, "Local change pending synchronization")

    def _set_sync_state_in_transaction(self, state: str, version_hash: str | None, detail: str | None) -> None:
        self.connection.execute(
            "INSERT INTO sync_state (id, state, version_hash, detail, updated_at) VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(id) DO UPDATE SET state = excluded.state, version_hash = excluded.version_hash, detail = excluded.detail, updated_at = CURRENT_TIMESTAMP",
            (state, version_hash, detail),
        )

    def set_sync_state(self, state: str, version_hash: str | None = None, detail: str | None = None) -> None:
        if state not in {"pending", "success", "failed"}:
            raise ValueError("invalid sync state")
        with self.connection: self._set_sync_state_in_transaction(state, version_hash, detail)
        self.connection.commit()

    def sync_state(self) -> dict[str, Any]:
        row = self.connection.execute("SELECT state, version_hash, detail, updated_at FROM sync_state WHERE id = 1").fetchone()
        return dict(row) if row else {"state": "success", "version_hash": None, "detail": None, "updated_at": None}

    def execute(self, query: str, parameters: Iterable[Any] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(query, tuple(parameters))
        self.connection.commit()
        return cursor

    def rows(self, query: str, parameters: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(query, tuple(parameters)).fetchall())

    def drawer_inventory(self, drawer_id: int) -> list[sqlite3.Row]:
        return self.rows(
            "SELECT item_name, quantity FROM drawer_inventory WHERE drawer_id = ? ORDER BY item_name",
            (drawer_id,),
        )

    def authorized_owners(self, drawer_id: int) -> list[str]:
        rows = self.rows(
            """
            SELECT cards.owner_name
            FROM cards
            JOIN card_drawer_permissions permissions ON permissions.card_id = cards.id
            WHERE permissions.drawer_id = ?
            ORDER BY cards.owner_name
            """,
            (drawer_id,),
        )
        return [row["owner_name"] for row in rows]

    def card_drawer_ids(self, card_id: int) -> list[int]:
        rows = self.rows(
            "SELECT drawer_id FROM card_drawer_permissions WHERE card_id = ? ORDER BY drawer_id",
            (card_id,),
        )
        return [row["drawer_id"] for row in rows]

    def export_payload(self) -> dict[str, Any]:
        drawers = []
        for drawer in self.rows(
            "SELECT id, label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated FROM drawers ORDER BY id"
        ):
            position = {
                "x_mm": drawer["pos_x_mm"] if drawer["calibrated"] else None,
                "y_mm": drawer["pos_y_mm"] if drawer["calibrated"] else None,
                "z_mm": drawer["pos_z_mm"] if drawer["calibrated"] else None,
            }
            drawers.append(
                {
                    "id": drawer["id"],
                    "label": drawer["label"],
                    "position": position,
                    "x_mm": position["x_mm"],
                    "y_mm": position["y_mm"],
                    "z_mm": position["z_mm"],
                    "calibrated": bool(drawer["calibrated"]),
                    "inventory": [dict(item) for item in self.drawer_inventory(drawer["id"])],
                    "authorized_owners": self.authorized_owners(drawer["id"]),
                }
            )

        cards = []
        for row in self.rows("SELECT id, uid, owner_name, status, attributes_json FROM cards ORDER BY id"):
            try:
                attributes = json.loads(row["attributes_json"] or "{}")
            except json.JSONDecodeError:
                attributes = {}
            cards.append(
                {
                    "uid": row["uid"],
                    "owner_name": row["owner_name"],
                    "status": row["status"],
                    "attributes": attributes,
                    "drawer_ids": self.card_drawer_ids(row["id"]),
                }
            )
        return {
            "machine_config": self.machine_config(),
            "drawers": drawers,
            "cards": cards,
        }

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
