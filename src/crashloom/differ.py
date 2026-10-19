"""Compare two CrashLoom flight records."""

from __future__ import annotations

from typing import Mapping

from crashloom.models import (
    FlightDiffReport,
    FlightRecord,
    FrameSnapshot,
    SerializedValue,
    VariableDelta,
)


def _location(frame: FrameSnapshot | None) -> str:
    if frame is None:
        return ""
    return f"{frame.filename}:{frame.lineno} in {frame.function_name}"


def _variable_deltas(
    left: Mapping[str, SerializedValue],
    right: Mapping[str, SerializedValue],
) -> list[VariableDelta]:
    deltas: list[VariableDelta] = []
    for name in sorted(left.keys() | right.keys()):
        old = left.get(name)
        new = right.get(name)
        if old is None:
            deltas.append(VariableDelta(name, "added", None, new))
        elif new is None:
            deltas.append(VariableDelta(name, "removed", old, None))
        elif old != new:
            deltas.append(VariableDelta(name, "changed", old, new))
    return deltas


def diff_flights(left: FlightRecord, right: FlightRecord) -> FlightDiffReport:
    """Return a deterministic, JSON-serializable comparison of two flights."""
    left_frame = left.target_frame
    right_frame = right.target_frame
    left_args = left_frame.bound_arguments if left_frame else {}
    right_args = right_frame.bound_arguments if right_frame else {}
    left_locals = left_frame.local_variables if left_frame else {}
    right_locals = right_frame.local_variables if right_frame else {}

    return FlightDiffReport(
        left_flight_id=left.flight_id,
        right_flight_id=right.flight_id,
        same_fingerprint=(left.fingerprint == right.fingerprint),
        exception_changed=(left.exception_type != right.exception_type),
        left_exception=left.exception_type,
        right_exception=right.exception_type,
        left_location=_location(left_frame),
        right_location=_location(right_frame),
        argument_deltas=_variable_deltas(left_args, right_args),
        local_deltas=_variable_deltas(left_locals, right_locals),
    )
