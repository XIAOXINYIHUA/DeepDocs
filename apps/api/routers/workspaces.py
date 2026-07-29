"""工作区 CRUD 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.user import User
from packages.core.models.workspace import Workspace
from ..dependencies.auth import get_current_user
from ..dependencies.database import get_db

router = APIRouter(tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Workspace]:
    """获取当前用户的所有工作区。"""
    result = await db.execute(
        select(Workspace)
        .where(Workspace.owner_id == current_user.id)
        .where(Workspace.is_active.is_(True))
        .order_by(Workspace.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    req: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """创建新工作区。"""
    workspace = Workspace(
        name=req.name,
        description=req.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.flush()
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """获取工作区详情。"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id,
            Workspace.is_active.is_(True),
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """软删除工作区。"""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    workspace.is_active = False
    await db.flush()
