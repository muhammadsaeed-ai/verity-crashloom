import sys
import inspect
import platform
import linecache
import uuid
import datetime
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from crashloom.models import FlightRecord, FrameSnapshot
from crashloom.serializer import SafeSerializer
from crashloom.fingerprint import compute_crash_fingerprint, extract_ast_statement_info

def _is_user_code(filename: str) -> bool:
    """Exclude CrashLoom and the active Python installation from app frames."""
    try:
        path = Path(filename).resolve()
        package_root = Path(__file__).resolve().parent
        python_root = Path(sys.base_prefix).resolve()
        return not (path.is_relative_to(package_root) or path.is_relative_to(python_root))
    except (OSError, ValueError):
        return True


def _safe_argv(argv: list[str], redactor) -> list[str]:
    safe: list[str] = []
    redact_next = False
    for arg in argv:
        if redact_next:
            safe.append("<REDACTED_BY_CRASHLOOM>")
            redact_next = False
            continue
        clean, _ = redactor.redact_string(arg)
        safe.append(clean)
        option = arg.lstrip("-").split("=", 1)[0]
        if "=" not in arg and arg.startswith("-") and redactor.is_sensitive_identifier(option):
            redact_next = True
    return safe


class FlightCollector:
    def __init__(self, serializer: SafeSerializer | None = None):
        self.serializer = serializer or SafeSerializer()
    def collect_exception(self, exc_type, exc_value, exc_tb) -> FlightRecord:
        frames = []
        tb = exc_tb
        while tb is not None:
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            tb = tb.tb_next
            filename = frame.f_code.co_filename
            raw_source_line = linecache.getline(filename, lineno).rstrip("\r\n")
            source_line, _ = self.serializer.redactor.redact_string(raw_source_line)
            ast_type, ast_canon = extract_ast_statement_info(source_line)
            local_items = {k: v for k, v in frame.f_locals.items() if not k.startswith("__")}
            code = frame.f_code
            argument_count = code.co_argcount + code.co_kwonlyargcount
            if code.co_flags & inspect.CO_VARARGS:
                argument_count += 1
            if code.co_flags & inspect.CO_VARKEYWORDS:
                argument_count += 1
            argument_names = set(code.co_varnames[:argument_count])
            bound = {k: self.serializer.serialize(v, k) for k, v in local_items.items() if k in argument_names}
            local_variables = {k: self.serializer.serialize(v, k) for k, v in local_items.items() if k not in argument_names}
            frames.append(FrameSnapshot(
                filename=filename,
                module_name=frame.f_globals.get("__name__", "__main__"),
                function_name=frame.f_code.co_name,
                qualname=frame.f_code.co_name,
                lineno=lineno,
                source_line=source_line,
                context_lines=[(lineno, source_line)],
                ast_node_type=ast_type,
                ast_canonical_expr=ast_canon,
                bound_arguments=bound,
                local_variables=local_variables,
                is_user_code=_is_user_code(filename)
            ))
        target = frames[-1] if frames else None
        fp = compute_crash_fingerprint(exc_type.__qualname__, target.module_name if target else "main", target.function_name if target else "main", target.ast_canonical_expr if target else "") if target else "0000000000000000"
        return FlightRecord(
            flight_id=f"fl_{uuid.uuid4().hex[:12]}",
            fingerprint=fp,
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            exception_type=exc_type.__qualname__,
            exception_module=exc_type.__module__,
            exception_message=self.serializer.redactor.redact_string(str(exc_value))[0],
            python_version=sys.version.split()[0],
            platform_info=platform.platform(),
            cwd=str(Path.cwd()),
            command_argv=_safe_argv(sys.argv, self.serializer.redactor),
            safe_env={},
            frames=frames
        )

@contextmanager
def capture(db_path=None, reraise=True) -> Iterator[list[FlightRecord]]:
    from crashloom.storage import FlightStorage
    records = []
    try:
        yield records
    except BaseException:
        et, ev, etb = sys.exc_info()
        if et and ev:
            rec = FlightCollector().collect_exception(et, ev, etb)
            records.append(rec)
            FlightStorage(db_path).save(rec)
        if reraise:
            raise

def watch(func=None, *, db_path=None, reraise=True):
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except BaseException:
                et, ev, etb = sys.exc_info()
                if et and ev:
                    rec = FlightCollector().collect_exception(et, ev, etb)
                    from crashloom.storage import FlightStorage
                    FlightStorage(db_path).save(rec)
                if reraise:
                    raise
        return wrapper
    return decorator if func is None else decorator(func)
