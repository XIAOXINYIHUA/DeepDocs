"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter

from ..dependencies.database import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """基础健康检查。"""
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
