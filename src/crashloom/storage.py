import sqlite3
import json
from pathlib import Path
from crashloom.models import FlightRecord

class FlightStorage:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else Path.cwd() / ".crashloom" / "flights.db"
        self._init_db()
    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS flights (flight_id TEXT PRIMARY KEY, fingerprint TEXT, timestamp_utc TEXT, exception_type TEXT, occurrence_count INT, payload_json TEXT)")
    def save(self, record: FlightRecord) -> FlightRecord:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO flights VALUES (?, ?, ?, ?, 1, ?)", (record.flight_id, record.fingerprint, record.timestamp_utc, record.exception_type, record.to_json()))
        return record
    def get(self, identifier: str) -> FlightRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT payload_json FROM flights WHERE flight_id = ? OR fingerprint = ?", (identifier, identifier)).fetchone()
        return FlightRecord.from_dict(json.loads(row[0])) if row else None
    def list_recent(self, limit=25):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT payload_json FROM flights ORDER BY timestamp_utc DESC LIMIT ?", (limit,)).fetchall()
        return [FlightRecord.from_dict(json.loads(r[0])) for r in rows]
