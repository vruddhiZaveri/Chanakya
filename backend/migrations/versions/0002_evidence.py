"""Local immutable documents, passages and retrieval snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0002_evidence"
down_revision = "0001_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("version_id", sa.String, nullable=False, unique=True),
        sa.Column(
            "session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False
        ),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("media_type", sa.String, nullable=False),
        sa.Column("sha256", sa.String, nullable=False),
        sa.Column("byte_size", sa.Integer, nullable=False),
        sa.Column("raw", sa.LargeBinary, nullable=False),
        sa.Column("pages", sa.JSON, nullable=False),
        sa.Column("created_at", sa.String, nullable=False),
        sa.UniqueConstraint("session_id", "sha256"),
        sa.UniqueConstraint("id", "session_id"),
    )
    op.create_table(
        "passages",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("document_id", sa.String, nullable=False),
        sa.Column("session_id", sa.String, nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("start_char", sa.Integer, nullable=False),
        sa.Column("end_char", sa.Integer, nullable=False),
        sa.Column("excerpt", sa.String, nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "session_id"], ["documents.id", "documents.session_id"]
        ),
    )
    op.create_index("ix_passages_session", "passages", ["session_id"])
    op.create_table(
        "retrieval_snapshots",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("session_id", sa.String, nullable=False),
        sa.Column("brief_revision", sa.Integer, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id", "brief_revision"],
            ["brief_versions.session_id", "brief_versions.revision"],
        ),
    )
    op.create_index("ix_retrieval_session", "retrieval_snapshots", ["session_id"])
    for table in ["documents", "passages", "retrieval_snapshots"]:
        for action in ["UPDATE", "DELETE"]:
            op.execute(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable evidence history'); END"
            )


def downgrade():
    raise RuntimeError(
        "Destructive evidence downgrade is unavailable; preserve your database."
    )
