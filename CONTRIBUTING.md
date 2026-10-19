# Contributing to CrashLoom

Thanks for helping improve CrashLoom. Bug reports, focused fixes, security improvements, tests, and documentation updates are welcome.

## Development setup

- Python 3.10 or newer
- Git

```bash
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -e ".[dev]"
pytest
```

## Pull request checklist

1. Keep changes focused and explain the problem they solve.
2. Add or update tests for behavior changes, especially serialization and redaction.
3. Run `pytest` before opening a pull request.
4. Do not commit `.crashloom/` databases, captured flight records, real credentials, or customer data.
5. Document known limitations instead of claiming redaction or reproduction is perfect.

For substantial changes, open an issue first so the design can be discussed before implementation.
