"""知识库 CRUD 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.knowledge_base import KnowledgeBase
from packages.core.models.user import User
from packages.core.models.workspace import Workspace
from ..dependencies.auth import get_current_user
from ..dependencies.database import get_db

router = APIRouter(tags=["knowledge-bases"])


class KnowledgeBaseCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    language: str = "zh-CN"


class KnowledgeBaseResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    language: str
    document_count: int = 0
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """获取知识库列表（可按工作区过滤）。"""
    query = select(KnowledgeBase).where(KnowledgeBase.is_active.is_(True))
    if workspace_id:
        query = query.where(KnowledgeBase.workspace_id == workspace_id)
    query = query.order_by(KnowledgeBase.created_at.desc())
    result = await db.execute(query)
    kbs = result.scalars().all()

    # 注入文档数量
    response = []
    for kb in kbs:
        resp = KnowledgeBaseResponse.model_validate(kb)
        resp.document_count = len(kb.documents) if hasattr(kb, "documents") else 0
        response.append(resp)
    return response


@router.post(
    "", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBase:
    """创建新知识库。"""
    # 验证工作区存在
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == req.workspace_id,
            Workspace.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    kb = KnowledgeBase(
        workspace_id=req.workspace_id,
        name=req.name,
        description=req.description,
        language=req.language,
    )
    db.add(kb)
    await db.flush()

    return kb


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBase:
    """获取知识库详情。"""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.is_active.is_(True),
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """软删除知识库。"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    kb.is_active = False
    await db.flush()
