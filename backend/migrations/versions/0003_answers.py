"""Immutable completed document-grounded model answers."""

from alembic import op
import sqlalchemy as sa

revision = "0003_answers"
down_revision = "0002_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_retrieval_context",
        "retrieval_snapshots",
        ["id", "session_id", "brief_revision"],
        unique=True,
    )
    op.create_table(
        "saved_answers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("session_id", sa.String, nullable=False),
        sa.Column("brief_revision", sa.Integer, nullable=False),
        sa.Column("snapshot_id", sa.String, nullable=False),
        sa.Column("idempotency_key", sa.String, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key"),
        sa.ForeignKeyConstraint(
            ["session_id", "brief_revision"],
            ["brief_versions.session_id", "brief_versions.revision"],
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "session_id", "brief_revision"],
            [
                "retrieval_snapshots.id",
                "retrieval_snapshots.session_id",
                "retrieval_snapshots.brief_revision",
            ],
        ),
    )
    op.create_index("ix_answers_session", "saved_answers", ["session_id"])
    for action in ["UPDATE", "DELETE"]:
        op.execute(
            f"CREATE TRIGGER answers_no_{action.lower()} BEFORE {action} ON saved_answers BEGIN SELECT RAISE(ABORT, 'Immutable answer history'); END"
        )


def downgrade():
    raise RuntimeError(
        "Destructive answer downgrade is unavailable; preserve your database."
    )
