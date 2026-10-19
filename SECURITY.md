# Security Policy

## Data handling

CrashLoom is designed to operate locally and does not intentionally make network calls. Captured flight records can contain source paths, source lines, exception messages, variable names, and serialized values. The built-in redactor covers sensitive variable names and selected common token patterns, but it is **best-effort and not a guarantee**.

Do not upload or share a flight database, generated report, CI artifact, or traceback without reviewing it for credentials and personal or customer data. Store the `.crashloom/` directory as sensitive debugging data.

CrashLoom uses JSON and dataclass-based record models; it avoids unsafe object deserialization and dynamic code evaluation when loading captured records. Treat reports and generated reproducer templates as data to review before use.

## Reporting a vulnerability

Please do not post unredacted secrets or exploit details in a public issue. Contact the repository owner through their GitHub profile and include the affected version, impact, and a minimal reproduction that contains no real credentials. A response time is not guaranteed while this project is in early development.
