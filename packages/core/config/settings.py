"""全局应用配置 —— 从环境变量和 .env 文件加载。"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── 运行环境 ───
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    debug: bool = False

    # ─── DeepSeek ───
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # ─── 数据库 ───
    postgres_server: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "deepdocs"
    postgres_password: str = "deepdocs_secret"
    postgres_db: str = "deepdocs"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    # ─── Redis ───
    redis_url: str = "redis://localhost:6379/0"

    # ─── Qdrant ───
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_https: bool = False

    @property
    def qdrant_url(self) -> str:
        if self.qdrant_https:
            return f"https://{self.qdrant_host}:{self.qdrant_port}"
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    # ─── MinIO ───
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "deepdocs"
    minio_secret_key: str = "deepdocs_secret"
    minio_bucket: str = "deepdocs-files"
    minio_secure: bool = False

    # ─── 认证 ───
    jwt_secret: str = "change-this-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # ─── 嵌入模型 ───
    bge_model_path: str = "./models/bge-m3"
    reranker_model_path: str = "./models/bge-reranker-v2-m3"

    # 云端嵌入备选
    openai_api_key: str = ""
    siliconflow_api_key: str = ""
    dashscope_api_key: str = ""

    # ─── 上传 ───
    upload_max_size_mb: int = 100
    default_locale: str = "zh-CN"

    # ─── 模型默认值 ───
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"
    default_reasoner_model: str = "deepseek-reasoner"
    default_embedding_provider: str = "bge-m3"
    default_reranker_provider: str = "bge-reranker"

    # ─── 检索默认值 ───
    default_top_k: int = 10
    default_similarity_threshold: float = 0.6
    default_rerank_top_k: int = 6
    max_context_tokens: int = 32000

    @property
    def upload_max_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024


# 全局单例
settings = Settings()
