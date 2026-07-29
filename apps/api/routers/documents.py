"""文档管理路由 —— 上传、列表、删除。"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config.settings import settings
from packages.core.models.block import BlockType
from packages.core.models.document import Document, DocumentStatus
from packages.core.models.user import User
from packages.core.models.workspace import Workspace
from packages.parsers import registry as parser_registry
from packages.parsers.chunker import chunk_document

from ..dependencies.auth import get_current_user
from ..dependencies.database import get_db
from ..dependencies.storage import FileStorage

router = APIRouter(tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    error_message: str | None
    current_version: int
    created_at: str

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    task_id: str | None = None
    message: str


ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".txt", ".md", ".markdown",
    ".html", ".htm",
    ".csv", ".json",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif",
}


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    kb_id: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """上传文档到知识库。

    流程：保存到 MinIO → 创建 Document 记录 → 触发异步摄取
    """
    # 1. 验证文件扩展名
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 2. 验证文件大小
    content = await file.read()
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {settings.upload_max_size_mb}MB",
        )
    await file.seek(0)

    # 3. 保存到 MinIO
    storage = FileStorage()
    storage.ensure_bucket()

    object_name = f"{kb_id}/{uuid.uuid4()}_{file.filename}"
    mime_type = file.content_type or "application/octet-stream"
    storage.upload_bytes(content, object_name, content_type=mime_type)

    # 4. 创建 Document 记录
    doc = Document(
        kb_id=kb_id,
        filename=file.filename or "unknown",
        file_type=ext.lstrip("."),
        mime_type=mime_type,
        file_size=len(content),
        storage_path=object_name,
        owner_id=current_user.id,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()

    # 5. 触发异步摄取
    try:
        from workers.ingestion.tasks.ingest import ingest_document

        ingest_document.send(str(doc.id))
        task_id = str(doc.id)
    except Exception as e:
        task_id = None

    return DocumentUploadResponse(
        id=str(doc.id),
        filename=doc.filename,
        status=doc.status.value,
        task_id=task_id,
        message="Document uploaded. Ingestion started.",
    )


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents(
    kb_id: str,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Document]:
    """列出知识库中的文档。"""
    query = (
        select(Document)
        .where(Document.kb_id == kb_id)
        .where(Document.status != DocumentStatus.DELETED)
    )
    if status_filter:
        query = query.where(Document.status == status_filter)
    query = query.order_by(Document.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    response_model=DocumentResponse,
)
async def get_document(
    kb_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    """获取文档详情。"""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.kb_id == kb_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return doc


@router.delete(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    kb_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除文档（软删除 + 异步清理向量）。"""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.kb_id == kb_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    doc.status = DocumentStatus.DELETED
    await db.flush()

    # 异步清理向量
    try:
        from workers.ingestion.tasks.ingest import delete_document_vectors

        delete_document_vectors.send(doc_id, kb_id)
    except Exception:
        pass
