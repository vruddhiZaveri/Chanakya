from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    JSON,
    LargeBinary,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from app.db.tables import metadata

documents = Table(
    "documents",
    metadata,
    Column("id", String, primary_key=True),
    Column("version_id", String, nullable=False, unique=True),
    Column("session_id", String, ForeignKey("sessions.id"), nullable=False),
    Column("filename", String, nullable=False),
    Column("media_type", String, nullable=False),
    Column("sha256", String, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("raw", LargeBinary, nullable=False),
    Column("pages", JSON, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint("session_id", "sha256"),
    UniqueConstraint("id", "session_id"),
)
passages = Table(
    "passages",
    metadata,
    Column("id", String, primary_key=True),
    Column("document_id", String, nullable=False),
    Column("session_id", String, nullable=False),
    Column("page", Integer, nullable=False),
    Column("start_char", Integer, nullable=False),
    Column("end_char", Integer, nullable=False),
    Column("excerpt", String, nullable=False),
    ForeignKeyConstraint(
        ["document_id", "session_id"], ["documents.id", "documents.session_id"]
    ),
)
retrievals = Table(
    "retrieval_snapshots",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("brief_revision", Integer, nullable=False),
    Column("result", JSON, nullable=False),
    ForeignKeyConstraint(
        ["session_id", "brief_revision"],
        ["brief_versions.session_id", "brief_versions.revision"],
    ),
)
