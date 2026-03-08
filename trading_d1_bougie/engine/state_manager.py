# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/state_manager.py
# DESCRIPTION  : Persistance SQLite — positions + état journalier
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : Sprint 7
# ============================================================
"""StateManager — persiste l’état du bot dans SQLite.

Permet au bot de survivre aux redémarrages sans perte de positions
ou de compteurs journaliers.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

DB_PATH = Path("trading_d1_bougie/data/state.db")


class StateManager:
    """Persiste l’état du bot dans SQLite pour survivre aux redémarrages."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS open_positions (
                pair        TEXT PRIMARY KEY,
                order_id    INTEGER NOT NULL,
                direction   TEXT NOT NULL,
                entry_price REAL NOT NULL,
                sl_price    REAL NOT NULL,
                tp_price    REAL NOT NULL,
                lot_size    REAL NOT NULL,
                opened_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS daily_state (
                trade_date   TEXT PRIMARY KEY,
                equity_start REAL NOT NULL,
                trade_counts TEXT NOT NULL  -- JSON {"EURUSD": 1, ...}
            );
        """)
        self._conn.commit()

    def save_position(self, pair: str, order_id: int, spec: Any) -> None:
        """Persiste une position ouverte."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO open_positions
                (pair, order_id, direction, entry_price, sl_price, tp_price, lot_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pair,
                order_id,
                spec.direction,
                spec.entry_price,
                spec.sl_price,
                spec.tp_price,
                spec.lot_size,
            ),
        )
        self._conn.commit()

    def remove_position(self, pair: str) -> None:
        """Supprime une position clôturée."""
        self._conn.execute("DELETE FROM open_positions WHERE pair = ?", (pair,))
        self._conn.commit()

    def load_positions(self) -> dict[str, int]:
        """Retourne {pair: order_id} des positions persistées."""
        cur = self._conn.execute("SELECT pair, order_id FROM open_positions")
        return {row[0]: row[1] for row in cur.fetchall()}

    def save_daily_state(
        self,
        trade_date: date,
        equity_start: float,
        trade_counts: dict[str, int],
    ) -> None:
        """Persiste l’état journalier (equity de début + compteurs)."""
        self._conn.execute(
            "INSERT OR REPLACE INTO daily_state VALUES (?, ?, ?)",
            (str(trade_date), equity_start, json.dumps(trade_counts)),
        )
        self._conn.commit()

    def load_daily_state(
        self, trade_date: date
    ) -> tuple[float, dict[str, int]] | None:
        """Charge l’état journalier persisté pour une date donnée.

        Returns:
            (equity_start, trade_counts) ou None si pas de données.
        """
        cur = self._conn.execute(
            "SELECT equity_start, trade_counts FROM daily_state WHERE trade_date = ?",
            (str(trade_date),),
        )
        row = cur.fetchone()
        if row:
            return row[0], json.loads(row[1])
        return None

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        self._conn.close()
