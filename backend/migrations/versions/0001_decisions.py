"""Initial decision briefs and immutable hypothesis versions.

Revision ID: 0001_decisions
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_decisions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # SQLite accepts deferred references to tables created later in this transaction.
    op.create_table("sessions",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.String, nullable=False), sa.Column("updated_at", sa.String, nullable=False),
        sa.CheckConstraint("revision >= 1"),
        sa.ForeignKeyConstraint(["id", "revision"], ["brief_versions.session_id", "brief_versions.revision"], deferrable=True, initially="DEFERRED"))
    op.create_table("brief_versions",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), primary_key=True),
        sa.Column("revision", sa.Integer, primary_key=True), sa.Column("brief", sa.JSON, nullable=False),
        sa.Column("reason", sa.String, nullable=False), sa.Column("created_at", sa.String, nullable=False),
        sa.CheckConstraint("revision >= 1"))
    op.create_table("hypotheses",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False), sa.Column("created_at", sa.String, nullable=False),
        sa.CheckConstraint("revision >= 1"), sa.UniqueConstraint("id", "session_id"),
        sa.ForeignKeyConstraint(["id", "revision"], ["hypothesis_versions.hypothesis_id", "hypothesis_versions.revision"], deferrable=True, initially="DEFERRED"))
    op.create_index("ix_hypotheses_session_id", "hypotheses", ["session_id"])
    op.create_table("hypothesis_versions",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("hypothesis_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False), sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("previous_revision", sa.Integer), sa.Column("previous_version_id", sa.String(36)),
        sa.Column("brief_revision", sa.Integer, nullable=False), sa.Column("type", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False), sa.Column("content", sa.JSON, nullable=False),
        sa.Column("reason", sa.String, nullable=False), sa.Column("created_at", sa.String, nullable=False),
        sa.UniqueConstraint("hypothesis_id", "revision"), sa.UniqueConstraint("hypothesis_id", "revision", "id"),
        sa.CheckConstraint("revision >= 1 AND brief_revision >= 1"),
        sa.CheckConstraint("(revision = 1 AND previous_revision IS NULL AND previous_version_id IS NULL) OR (revision > 1 AND previous_revision = revision - 1 AND previous_version_id IS NOT NULL)"),
        sa.CheckConstraint("type IN ('factual','causal','comparative','predictive','diagnostic','normative')"),
        sa.CheckConstraint("status IN ('proposed','under_investigation','supported','challenged','revised','resolved','inconclusive')"),
        sa.ForeignKeyConstraint(["hypothesis_id", "session_id"], ["hypotheses.id", "hypotheses.session_id"]),
        sa.ForeignKeyConstraint(["session_id", "brief_revision"], ["brief_versions.session_id", "brief_versions.revision"]),
        sa.ForeignKeyConstraint(["hypothesis_id", "previous_revision", "previous_version_id"], ["hypothesis_versions.hypothesis_id", "hypothesis_versions.revision", "hypothesis_versions.id"]))
    for table in ("brief_versions", "hypothesis_versions"):
        for action in ("UPDATE", "DELETE"):
            op.execute(f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable version history'); END")


def downgrade():
    raise RuntimeError("Destructive downgrade is intentionally unavailable. Preserve the database and restore a verified backup if needed.")
