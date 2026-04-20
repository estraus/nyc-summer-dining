import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    rows = conn.execute("SELECT version FROM schema_versions").fetchall()
    return {r[0] for r in rows}


def _discover_migrations() -> list[tuple[int, Path]]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    out: list[tuple[int, Path]] = []
    for f in files:
        stem = f.stem
        version_str = stem.split("_", 1)[0]
        out.append((int(version_str), f))
    return out


def run_migrations(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        applied = _applied_versions(conn)
        for version, path in _discover_migrations():
            if version in applied:
                continue
            sql = path.read_text()
            conn.executescript("BEGIN;\n" + sql + "\nCOMMIT;")
            conn.execute("INSERT INTO schema_versions (version) VALUES (?)", (version,))
    finally:
        conn.close()
