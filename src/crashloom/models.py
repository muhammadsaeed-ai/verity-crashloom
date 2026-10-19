from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(frozen=True)
class SerializedValue:
    type_name: str
    repr_str: str
    is_reconstructible: bool
    python_expr: str | None = None
    redacted: bool = False
    truncated: bool = False
    summary: dict[str, Any] | list[Any] | str | int | float | bool | None = None
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SerializedValue:
        return cls(**data)

@dataclass(frozen=True)
class FrameSnapshot:
    filename: str
    module_name: str
    function_name: str
    qualname: str
    lineno: int
    source_line: str
    context_lines: list[tuple[int, str]]
    ast_node_type: str
    ast_canonical_expr: str
    bound_arguments: dict[str, SerializedValue]
    local_variables: dict[str, SerializedValue]
    is_user_code: bool = True
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bound_arguments"] = {k: v.to_dict() for k, v in self.bound_arguments.items()}
        d["local_variables"] = {k: v.to_dict() for k, v in self.local_variables.items()}
        return d
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrameSnapshot:
        data["bound_arguments"] = {k: SerializedValue.from_dict(v) for k, v in data.get("bound_arguments", {}).items()}
        data["local_variables"] = {k: SerializedValue.from_dict(v) for k, v in data.get("local_variables", {}).items()}
        return cls(**data)

@dataclass(frozen=True)
class FlightRecord:
    flight_id: str
    fingerprint: str
    timestamp_utc: str
    exception_type: str
    exception_module: str
    exception_message: str
    python_version: str
    platform_info: str
    cwd: str
    command_argv: list[str]
    safe_env: dict[str, str]
    frames: list[FrameSnapshot]
    entry_arguments_override: dict[str, SerializedValue] = field(default_factory=dict)
    occurrence_count: int = 1
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["frames"] = [f.to_dict() for f in self.frames]
        d["entry_arguments_override"] = {k: v.to_dict() for k, v in self.entry_arguments_override.items()}
        return d
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlightRecord:
        data["frames"] = [FrameSnapshot.from_dict(f) for f in data.get("frames", [])]
        data["entry_arguments_override"] = {k: SerializedValue.from_dict(v) for k, v in data.get("entry_arguments_override", {}).items()}
        return cls(**data)
    @property
    def target_frame(self) -> FrameSnapshot | None:
        user_frames = [f for f in self.frames if f.is_user_code]
        if user_frames:
            return user_frames[-1]
        return self.frames[-1] if self.frames else None


@dataclass(frozen=True)
class VariableDelta:
    """Describe how one serialized variable differs between two flights."""

    name: str
    change_type: str
    left_value: SerializedValue | None = None
    right_value: SerializedValue | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "change_type": self.change_type,
            "left_value": self.left_value.to_dict() if self.left_value else None,
            "right_value": self.right_value.to_dict() if self.right_value else None,
        }


@dataclass(frozen=True)
class FlightDiffReport:
    """Summary of the differences between two captured exception flights."""

    left_flight_id: str
    right_flight_id: str
    same_fingerprint: bool
    exception_changed: bool
    left_exception: str
    right_exception: str
    left_location: str
    right_location: str
    argument_deltas: list[VariableDelta] = field(default_factory=list)
    local_deltas: list[VariableDelta] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_flight_id": self.left_flight_id,
            "right_flight_id": self.right_flight_id,
            "same_fingerprint": self.same_fingerprint,
            "exception_changed": self.exception_changed,
            "left_exception": self.left_exception,
            "right_exception": self.right_exception,
            "left_location": self.left_location,
            "right_location": self.right_location,
            "argument_deltas": [item.to_dict() for item in self.argument_deltas],
            "local_deltas": [item.to_dict() for item in self.local_deltas],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
