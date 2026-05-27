"""Adapter de persistência para `AlertEvent` em SQLite.

Implementa o port `services.domain.EventStore`. Mantém o schema
atual da tabela `events` e o formato de dict retornado por
`list_recent` — esse dict é contrato público consumido por
`/events` e pelo `dashboard.js`.
"""

import sqlite3

from services.domain import AlertEvent


class EventRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def init(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_time TEXT,
                label TEXT,
                confidence REAL,
                image_path TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def save(self, event: AlertEvent) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO events (id, event_time, label, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_time,
                event.label,
                event.confidence,
                event.image_path,
            ),
        )
        conn.commit()
        conn.close()

    def list_recent(self, limit: int = 50) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, event_time, label, confidence, image_path
            FROM events
            ORDER BY event_time DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "event_time": r[1],
                "label": r[2],
                "confidence": r[3],
                "image_path": r[4],
            }
            for r in rows
        ]

    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events")
        total = cur.fetchone()[0]
        conn.close()
        return int(total)
