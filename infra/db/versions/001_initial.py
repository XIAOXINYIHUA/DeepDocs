"""初始迁移：创建所有核心表。

Revision ID: 001
Revises:
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── 用户 ───
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ─── 工作区 ───
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_id", "workspaces", ["id"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # ─── 知识库 ───
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh-CN"),
        sa.Column("retrieval_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding_signature", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_bases_id", "knowledge_bases", ["id"])
    op.create_index(
        "ix_knowledge_bases_workspace_id", "knowledge_bases", ["workspace_id"]
    )

    # ─── 文档 ───
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "parsing", "ready", "error", "deleted", name="document_status"
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parser_version", sa.String(32), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_kb_id", "documents", ["kb_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # ─── 文档版本 ───
    op.create_table(
        "document_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("parser_version", sa.String(32), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_versions_document_id", "document_versions", ["document_id"]
    )
    op.create_index(
        "ix_document_versions_file_hash", "document_versions", ["file_hash"]
    )

    # ─── Block ───
    op.create_table(
        "blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("parent_block_id", sa.UUID(), nullable=True),
        sa.Column(
            "block_type",
            sa.Enum(
                "title", "heading", "paragraph", "list", "list_item",
                "table", "table_row", "image", "caption", "header",
                "footer", "formula", "code", "quote", "separator", "other",
                name="block_type",
            ),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("heading_path", sa.String(512), nullable=True),
        sa.Column("heading_level", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("text_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("table_data", postgresql.JSONB(), nullable=True),
        sa.Column("image_ref", sa.String(1024), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_block_id"], ["blocks.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blocks_document_id", "blocks", ["document_id"])
    op.create_index("ix_blocks_version_id", "blocks", ["version_id"])
    op.create_index("ix_blocks_block_type", "blocks", ["block_type"])

    # ─── Chunk ───
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column(
            "block_type",
            sa.Enum(
                "title", "heading", "paragraph", "list", "list_item",
                "table", "table_row", "image", "caption", "header",
                "footer", "formula", "code", "quote", "separator", "other",
                name="block_type",
            ),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("heading_path", sa.String(512), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_chunk_id", sa.UUID(), nullable=True),
        sa.Column("chunk_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("qdrant_point_id", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_chunk_id"], ["chunks.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_version_id", "chunks", ["version_id"])
    op.create_index("ix_chunks_kb_id", "chunks", ["kb_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])

    # ─── Index Profile ───
    op.create_table(
        "index_profiles",
        sa.Column("kb_id", sa.UUID(), nullable=False),
        sa.Column("embedding_provider", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=True),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("distance_metric", sa.String(16), nullable=False, server_default="cosine"),
        sa.Column("chunk_strategy", sa.String(32), nullable=False, server_default="structure_aware"),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="512"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="64"),
        sa.Column("sparse_index_version", sa.String(16), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["kb_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("kb_id"),
    )

    # ─── 对话会话 ───
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("kb_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_kb_id", "chat_sessions", ["kb_id"])

    # ─── 对话消息 ───
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(32), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # ─── 引用 ───
    op.create_table(
        "citations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("message_index", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("heading_path", sa.String(512), nullable=True),
        sa.Column("block_type", sa.String(32), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("excerpt_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("answer_start", sa.Integer(), nullable=True),
        sa.Column("answer_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_session_id", "citations", ["session_id"])
    op.create_index("ix_citations_document_id", "citations", ["document_id"])


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("index_profiles")
    op.drop_table("chunks")
    op.drop_table("blocks")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
    op.drop_table("workspaces")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS block_type")
