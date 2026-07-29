"""DeepDocs API —— FastAPI 应用入口。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.core.config.settings import settings

from .dependencies.database import check_db_connection
from .routers import auth, chat, documents, health, knowledge_bases, workspaces

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用启动/关闭生命周期。"""
    logger.info(
        "Starting DeepDocs API",
        environment=settings.environment,
        debug=settings.debug,
    )
    db_ok = await check_db_connection()
    if not db_ok:
        logger.warning("Database connection failed at startup")
    else:
        logger.info("Database connection OK")
    yield
    logger.info("Shutting down DeepDocs API")


app = FastAPI(
    title="DeepDocs API",
    description="全格式、可追溯、DeepSeek 优先的私有文档研究工作台",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.environment != "production" and ["*"] or [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 路由注册 ───
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(
    knowledge_bases.router, prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"]
)
app.include_router(
    documents.router, prefix="/api/v1", tags=["documents"]
)
app.include_router(chat.router, prefix="/api/v1", tags=["research"])
