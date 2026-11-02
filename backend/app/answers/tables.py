from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    JSON,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from app.db.tables import metadata

answers = Table(
    "saved_answers",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("brief_revision", Integer, nullable=False),
    Column("snapshot_id", String, nullable=False),
    Column("idempotency_key", String, nullable=False),
    Column("result", JSON, nullable=False),
    UniqueConstraint("session_id", "idempotency_key"),
    ForeignKeyConstraint(
        ["session_id", "brief_revision"],
        ["brief_versions.session_id", "brief_versions.revision"],
    ),
    ForeignKeyConstraint(
        ["snapshot_id", "session_id", "brief_revision"],
        [
            "retrieval_snapshots.id",
            "retrieval_snapshots.session_id",
            "retrieval_snapshots.brief_revision",
        ],
    ),
)
