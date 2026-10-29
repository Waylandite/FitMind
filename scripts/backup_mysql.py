"""Create a portable SQL backup of the database configured for FitMind.

Run from any directory with: python3 scripts/backup_mysql.py
The connection URL is read from FITMIND_DATABASE_URL or agent/.env. Passwords
are never included in the command line or written to the backup script.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "database" / "backups"


def database_url() -> str:
    if value := os.environ.get("FITMIND_DATABASE_URL"):
        return value

    env_file = PROJECT_ROOT / "agent" / ".env"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("FITMIND_DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"\'')
    raise RuntimeError(f"FITMIND_DATABASE_URL was not found in {env_file}")


def dump_executable() -> str:
    candidates = [
        shutil.which("mysqldump"),
        "/usr/local/mysql/bin/mysqldump",
        "/opt/homebrew/opt/mysql-client/bin/mysqldump",
        "/opt/homebrew/opt/mysql/bin/mysqldump",
        *glob.glob("/usr/local/mysql-*/bin/mysqldump"),
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("mysqldump was not found; install the MySQL client tools")


def main() -> int:
    parsed = urlsplit(database_url())
    database = unquote(parsed.path.lstrip("/"))
    if not parsed.scheme.startswith("mysql") or not database or not parsed.username:
        raise RuntimeError("FITMIND_DATABASE_URL is not a valid MySQL database URL")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(BACKUP_DIR, 0o700)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = BACKUP_DIR / f"{database}_{timestamp}.sql"
    command = [
        dump_executable(),
        "--protocol=TCP",
        f"--host={parsed.hostname or '127.0.0.1'}",
        f"--port={parsed.port or 3306}",
        f"--user={unquote(parsed.username)}",
        "--single-transaction",
        "--quick",
        "--routines",
        "--events",
        "--triggers",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        "--set-gtid-purged=OFF",
        "--no-tablespaces",
        "--databases",
        database,
    ]
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = unquote(parsed.password or "")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{database}_{timestamp}_", suffix=".tmp", dir=BACKUP_DIR,
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            os.chmod(temporary_path, 0o600)
            result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=environment)
        if result.returncode:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"mysqldump failed: {message}")
        temporary_path.replace(destination)
        print(destination)
        print(f"Size: {destination.stat().st_size:,} bytes")
        return 0
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Backup failed: {error}", file=sys.stderr)
        sys.exit(1)
