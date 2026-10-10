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


def test_upgrade_adds_delivery_fields_to_preexisting_tables(tmp_path):
    url = f"sqlite:///{(tmp_path / 'existing.sqlite3').as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alerts (id VARCHAR(36) PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE inventory (id VARCHAR(36) PRIMARY KEY, zone_id VARCHAR(36), product_id VARCHAR(36))"))
        connection.execute(text("INSERT INTO alerts (id) VALUES ('preserved')"))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = url
    try:
        command.stamp(config, "0002_normalized_user_email")
        command.upgrade(config, "head")
        assert {"active_key", "snoozed_until"} <= {c["name"] for c in inspect(engine).get_columns("alerts")}
        assert "outbox_events" in inspect(engine).get_table_names()
        assert "notification_deliveries" in inspect(engine).get_table_names()
        assert {"chat_conversations", "chat_turns"} <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id FROM alerts")).scalar() == "preserved"
    finally:
        settings.DATABASE_URL = original_url
        engine.dispose()


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
        assert "signup_pending" in {column["name"] for column in inspect(engine).get_columns("users")}
        assert _index_exists(engine)

        command.downgrade(config, "0001_existing_schema_baseline")
        assert not _index_exists(engine)

        command.upgrade(config, "head")
        assert _index_exists(engine)
    finally:
        settings.DATABASE_URL = original_url
        engine.dispose()


def test_signup_migration_preserves_disabled_existing_accounts(tmp_path):
    url = f"sqlite:///{(tmp_path / 'signup-existing.sqlite3').as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, is_active BOOLEAN NOT NULL)"))
        connection.execute(text("INSERT INTO users (id, is_active) VALUES ('disabled', 0), ('active', 1)"))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = url
    try:
        command.stamp(config, "0005_private_chat")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT is_active, signup_pending FROM users WHERE id = 'disabled'")).one() == (0, 0)
            assert connection.execute(text("SELECT is_active, signup_pending FROM users WHERE id = 'active'")).one() == (1, 0)
    finally:
        settings.DATABASE_URL = original_url
        engine.dispose()
