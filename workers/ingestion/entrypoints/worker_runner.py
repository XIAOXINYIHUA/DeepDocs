"""DeepDocs 摄取 Worker 入口点。

启动:
    python -m workers.ingestion.worker

或:
    dramatiq workers.ingestion.tasks.ingest
"""

from __future__ import annotations

import structlog

from ...packages.core.config.settings import settings

logger = structlog.get_logger()


def main() -> None:
    """启动 Dramatiq Worker。"""
    logger.info(
        "Starting DeepDocs ingestion worker",
        redis_url=settings.redis_url.rsplit("@", 1)[-1] if "@" in settings.redis_url else settings.redis_url,
    )

    # dramatiq 会自动发现 @dramatiq.actor 装饰的任务
    # 这里显式导入以确保任务注册
    from .tasks import ingest  # noqa: F401

    # 使用 dramatiq CLI 启动时不需要以下代码
    # 直接运行本文件时需要
    import dramatiq
    from dramatiq.brokers.redis import RedisBroker

    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)

    worker = dramatiq.Worker(broker, worker_timeout=100)
    worker.run()


if __name__ == "__main__":
    main()
