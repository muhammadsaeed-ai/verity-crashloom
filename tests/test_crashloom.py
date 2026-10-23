import json
import tempfile
import unittest
from pathlib import Path

from crashloom import (
    FlightCollector,
    FlightStorage,
    SafeSerializer,
    SecretRedactor,
    capture,
    diff_flights,
)
from crashloom.models import FlightRecord, FrameSnapshot, SerializedValue


class TestCrashLoom(unittest.TestCase):
    def test_redaction(self):
        redactor = SecretRedactor()
        self.assertTrue(redactor.is_sensitive_identifier("api_key"))
        serialized = SafeSerializer(redactor).serialize("not-for-logs", "api_key")
        self.assertTrue(serialized.redacted)
        self.assertNotIn("not-for-logs", serialized.repr_str)
        clean, changed = redactor.redact_string("connect(api_key='super-secret-value')")
        self.assertTrue(changed)
        self.assertNotIn("super-secret-value", clean)


    def test_generic_token_identifiers_are_redacted(self):
        redactor = SecretRedactor()
        for identifier in ("token", "id_token", "apiToken", "jwt"):
            with self.subTest(identifier=identifier):
                self.assertTrue(redactor.is_sensitive_identifier(identifier))
                serialized = SafeSerializer(redactor).serialize("opaque-private-value", identifier)
                self.assertTrue(serialized.redacted)
                self.assertNotIn("opaque-private-value", serialized.repr_str)
        clean, changed = redactor.redact_string("token=opaque-private-value")
        self.assertTrue(changed)
        self.assertNotIn("opaque-private-value", clean)

    def test_nested_structures_redact_sensitive_keys(self):
        serialized = SafeSerializer().serialize({"config": {"api_key": "sensitive-value", "enabled": True}})
        self.assertTrue(serialized.redacted)
        self.assertNotIn("sensitive-value", serialized.repr_str)
        self.assertNotIn("sensitive-value", json.dumps(serialized.to_dict()))


    def test_non_finite_float_expressions_are_valid_and_json_safe(self):
        serializer = SafeSerializer()
        cases = [
            (float("nan"), "float('nan')", "nan"),
            (float("inf"), "float('inf')", "inf"),
            (float("-inf"), "float('-inf')", "-inf"),
        ]
        for value, expression, summary in cases:
            with self.subTest(value=summary):
                serialized = serializer.serialize(value)
                self.assertTrue(serialized.is_reconstructible)
                self.assertEqual(serialized.python_expr, expression)
                self.assertEqual(serialized.summary, summary)
                compile(serialized.python_expr, "<crashloom-expression>", "eval")
                json.dumps(serialized.to_dict(), allow_nan=False)

    def test_capture_reraises_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "flights.db"
            with self.assertRaises(ZeroDivisionError):
                with capture(db_path=database, reraise=True) as records:
                    _ = 1 / 0
            # The context manager stores the record before propagating the failure.
            stored = FlightStorage(database).list_recent()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0].exception_type, "ZeroDivisionError")

    def test_diff_reports_changed_arguments(self):
        def frame(value: int) -> FrameSnapshot:
            return FrameSnapshot(
                filename="app.py", module_name="app", function_name="run",
                qualname="run", lineno=12, source_line="raise ValueError()",
                context_lines=[], ast_node_type="Raise", ast_canonical_expr="Raise()",
                bound_arguments={"value": SerializedValue("int", str(value), True, str(value), summary=value)},
                local_variables={},
            )

        def flight(identifier: str, value: int) -> FlightRecord:
            return FlightRecord(
                flight_id=identifier, fingerprint="same-fingerprint", timestamp_utc="2026-01-01T00:00:00+00:00",
                exception_type="ValueError", exception_module="builtins", exception_message="bad value",
                python_version="3.11", platform_info="test", cwd=".", command_argv=[], safe_env={}, frames=[frame(value)],
            )

        report = diff_flights(flight("left", 1), flight("right", 2))
        self.assertTrue(report.same_fingerprint)
        self.assertFalse(report.exception_changed)
        self.assertEqual(report.argument_deltas[0].change_type, "changed")
        decoded = json.loads(report.to_json())
        self.assertEqual(decoded["left_flight_id"], "left")
        self.assertEqual(decoded["argument_deltas"][0]["name"], "value")

    def test_capture_redacts_sensitive_values_from_stored_flight(self):
        try:
            api_key = "sk_live_sensitivevalue123"
            raise RuntimeError(f"invalid api_key={api_key}")
        except RuntimeError as exc:
            record = FlightCollector().collect_exception(type(exc), exc, exc.__traceback__)
        payload = record.to_json()
        self.assertNotIn("sk_live_sensitivevalue123", payload)
        self.assertTrue(any(frame.is_user_code for frame in record.frames))

    def test_flight_record_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "flights.db"
            with self.assertRaises(ZeroDivisionError):
                with capture(db_path=database):
                    _ = 1 / 0
            record = FlightStorage(database).list_recent()[0]
            restored = FlightRecord.from_dict(record.to_dict())
            self.assertEqual(restored.flight_id, record.flight_id)
            self.assertEqual(restored.exception_type, record.exception_type)


if __name__ == "__main__":
    unittest.main()
