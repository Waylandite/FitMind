from __future__ import annotations

from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from sqlalchemy import create_engine
from sqlalchemy import text

from fitmind_agent.core.config import get_settings


def _build_server_level_url(database_url: str) -> tuple[str, str]:
    parsed = urlsplit(database_url)
    database_name = parsed.path.lstrip("/")
    query = dict(parse_qsl(parsed.query))

    server_level_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            "/mysql",
            urlencode(query),
            parsed.fragment,
        )
    )
    return server_level_url, database_name


def init_mysql_database() -> None:
    settings = get_settings()
    server_level_url, database_name = _build_server_level_url(settings.database_url)

    engine = create_engine(server_level_url, future=True)

    with engine.connect() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
            )
        )
        connection.commit()


if __name__ == "__main__":
    init_mysql_database()
