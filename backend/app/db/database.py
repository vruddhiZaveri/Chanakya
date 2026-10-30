from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import URL, create_engine, event, text
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as PoolTimeoutError

from app.core.errors import BackendError

SCHEMA_REVISION = "0002_evidence"


def make_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)),
                           connect_args={"check_same_thread": False, "timeout": 5},
                           pool_size=4, max_overflow=0, pool_timeout=5, hide_parameters=True)

    @event.listens_for(engine, "connect")
    def configure(connection, _record):
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")

    @event.listens_for(engine, "begin")
    def begin(connection):
        connection.exec_driver_sql("BEGIN IMMEDIATE" if connection.info.get("write_transaction") else "BEGIN")

    return engine


class Database:
    def __init__(self, path: Path):
        self.engine = make_engine(path)

    def ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                return rows == [SCHEMA_REVISION]
        except (OperationalError, PoolTimeoutError):
            return False

    @contextmanager
    def transaction(self, write=False):
        if not self.ready():
            raise BackendError("storage_not_ready", "Run python -m app.db.migrate before using saved decisions.", 503)
        try:
            with self.engine.connect() as connection:
                connection.info["write_transaction"] = write
                try:
                    with connection.begin():
                        yield connection
                finally:
                    connection.info.pop("write_transaction", None)
        except (OperationalError, PoolTimeoutError) as error:
            raise BackendError("storage_unavailable", "Local storage is busy or unavailable. Retry after checking the database.", 503, True) from error
        except IntegrityError as error:
            raise BackendError("storage_integrity_error", "The storage consistency check failed. No partial write was saved.", 503) from error

    def close(self):
        self.engine.dispose()
