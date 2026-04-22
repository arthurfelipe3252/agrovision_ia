import sqlite3
from datetime import datetime


class EventRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def init_db(self) -> None:
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

    def save_event(self, event_id: str, label: str, confidence: float, image_path: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO events (id, event_time, label, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), label, confidence, image_path),
        )
        conn.commit()
        conn.close()

    def list_events(self, limit: int = 50) -> list[dict]:
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

    def count_events(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events")
        total = cur.fetchone()[0]
        conn.close()
        return int(total)
