from alembic import context

from app.db.tables import metadata
from app.evidence import tables

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Use python -m app.db.migrate to migrate the configured local database.")
context.configure(connection=connection, target_metadata=metadata, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
