"""Alembic migrations run only against a disposable SQLite database."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


def _index_exists(engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='index' AND name='uq_users_email_normalized'"
            )
        ).first() is not None


def test_migration_upgrade_and_incremental_downgrade(tmp_path: Path):
    database_path = tmp_path / "migration.sqlite3"
    url = f"sqlite:///{database_path.as_posix()}"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = url
    engine = create_engine(url)
    try:
        command.upgrade(config, "head")
        assert "users" in inspect(engine).get_table_names()
        assert _index_exists(engine)

        command.downgrade(config, "0001_existing_schema_baseline")
        assert not _index_exists(engine)

        command.upgrade(config, "head")
        assert _index_exists(engine)
    finally:
        settings.DATABASE_URL = original_url
        engine.dispose()
