"""Add document management tables.

Revision ID: add_document_management
Revises: 
Create Date: 2024-05-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_document_management"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create document management tables."""

    # Create template table
    op.create_table(
        "template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("placeholders", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_template_category"), "template", ["category"])
    op.create_index(op.f("ix_template_is_active"), "template", ["is_active"])
    op.create_index(op.f("ix_template_name"), "template", ["name"])

    # Create template_versions table
    op.create_table(
        "template_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["template.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_template_versions_template_id"), "template_versions", ["template_id"])
    op.create_index(op.f("ix_template_versions_version"), "template_versions", ["version"])

    # Create document table
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="generated"),
        sa.Column("access_level", sa.String(), nullable=False, server_default="internal"),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False, server_default="application/pdf"),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_document_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("encryption_key_id", sa.String(), nullable=True),
        sa.Column("is_readonly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_title"), "document", ["title"])
    op.create_index(op.f("ix_document_template_id"), "document", ["template_id"])
    op.create_index(op.f("ix_document_doc_type"), "document", ["doc_type"])
    op.create_index(op.f("ix_document_status"), "document", ["status"])
    op.create_index(op.f("ix_document_created_at"), "document", ["created_at"])

    # Create document_access_log table
    op.create_table(
        "document_access_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_access_log_document_id"), "document_access_log", ["document_id"])
    op.create_index(op.f("ix_document_access_log_user_id"), "document_access_log", ["user_id"])
    op.create_index(op.f("ix_document_access_log_action"), "document_access_log", ["action"])
    op.create_index(op.f("ix_document_access_log_accessed_at"), "document_access_log", ["accessed_at"])


def downgrade() -> None:
    """Drop document management tables."""
    op.drop_index(op.f("ix_document_access_log_accessed_at"), table_name="document_access_log")
    op.drop_index(op.f("ix_document_access_log_action"), table_name="document_access_log")
    op.drop_index(op.f("ix_document_access_log_user_id"), table_name="document_access_log")
    op.drop_index(op.f("ix_document_access_log_document_id"), table_name="document_access_log")
    op.drop_table("document_access_log")

    op.drop_index(op.f("ix_document_created_at"), table_name="document")
    op.drop_index(op.f("ix_document_status"), table_name="document")
    op.drop_index(op.f("ix_document_doc_type"), table_name="document")
    op.drop_index(op.f("ix_document_template_id"), table_name="document")
    op.drop_index(op.f("ix_document_title"), table_name="document")
    op.drop_table("document")

    op.drop_index(op.f("ix_template_versions_version"), table_name="template_versions")
    op.drop_index(op.f("ix_template_versions_template_id"), table_name="template_versions")
    op.drop_table("template_versions")

    op.drop_index(op.f("ix_template_is_active"), table_name="template")
    op.drop_index(op.f("ix_template_category"), table_name="template")
    op.drop_index(op.f("ix_template_name"), table_name="template")
    op.drop_table("template")
