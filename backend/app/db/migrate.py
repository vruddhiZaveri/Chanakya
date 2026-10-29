"""Explicit, repeatable local schema upgrade. Never downloads or calls a model."""
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import Settings
from app.db.database import make_engine


def upgrade_database(path: Path):
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations").replace("%", "%%"))
    engine = make_engine(path)
    try:
        with engine.connect() as connection:
            # WAL is persistent and must be enabled outside a transaction.
            connection.connection.driver_connection.execute("PRAGMA journal_mode=WAL")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    upgrade_database(Settings().database_path)
    print("Local database schema is up to date.")
