from __future__ import annotations
import sys
from pathlib import Path
from types import TracebackType
from crashloom.collector import FlightCollector, capture, watch
from crashloom.differ import diff_flights
from crashloom.fingerprint import compute_crash_fingerprint
from crashloom.models import FlightDiffReport, FlightRecord, FrameSnapshot, SerializedValue, VariableDelta
from crashloom.redactor import REDACTED_MASK, SecretRedactor
from crashloom.serializer import SafeSerializer
from crashloom.storage import FlightStorage
from crashloom.synthesizer import ReproducerSynthesizer

__version__ = "0.1.0"
__all__ = [
    "FlightCollector", "FlightDiffReport", "FlightRecord", "FlightStorage",
    "FrameSnapshot", "REDACTED_MASK", "ReproducerSynthesizer", "SafeSerializer",
    "SecretRedactor", "SerializedValue", "VariableDelta", "capture",
    "compute_crash_fingerprint", "diff_flights", "install", "uninstall", "watch",
]

_ORIGINAL_EXCEPTHOOK = sys.excepthook

def install(db_path: str | Path | None = None) -> None:
    collector = FlightCollector()
    storage = FlightStorage(db_path=db_path)
    def _crashloom_excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            _ORIGINAL_EXCEPTHOOK(exc_type, exc_value, exc_tb)
            return
        try:
            record = collector.collect_exception(exc_type, exc_value, exc_tb)
            saved = storage.save(record)
            sys.stderr.write(f"\n[CrashLoom] Recorded flight {saved.flight_id}\n")
        except Exception as e:
            sys.stderr.write(f"[CrashLoom] Warning: {e}\n")
        _ORIGINAL_EXCEPTHOOK(exc_type, exc_value, exc_tb)
    sys.excepthook = _crashloom_excepthook

def uninstall() -> None:
    sys.excepthook = _ORIGINAL_EXCEPTHOOK
