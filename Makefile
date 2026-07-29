.PHONY: dev test lint mypy clean db-upgrade db-migrate

# ─── 开发 ───

dev:  ## 启动完整开发环境
	docker compose up -d

dev-logs:  ## 查看日志
	docker compose logs -f

dev-stop:  ## 停止开发环境
	docker compose down

dev-rebuild:  ## 重建容器
	docker compose build --no-cache

# ─── 依赖 ───

install:  ## 安装所有依赖
	pip install -e ".[dev]"

install-bge:  ## 安装 BGE 模型依赖
	pip install -e ".[bge]"

# ─── 测试 ───

test:  ## 运行所有测试
	python -m pytest tests/ -v --tb=short --cov=packages

test-unit:  ## 仅单元测试
	python -m pytest tests/unit/ -v --tb=short

test-integration:  ## 仅集成测试
	python -m pytest tests/integration/ -v --tb=short

# ─── 代码质量 ───

lint:  ## 代码检查
	ruff check packages/ apps/ tests/

format:  ## 代码格式化
	ruff format packages/ apps/ tests/

mypy:  ## 类型检查
	mypy packages/ apps/api/

# ─── 数据库 ───

db-upgrade:  ## 执行数据库迁移
	alembic -c infra/db/alembic.ini upgrade head

db-downgrade:  ## 回退迁移
	alembic -c infra/db/alembic.ini downgrade -1

db-migrate:  ## 生成新迁移（需提供 msg）
	alembic -c infra/db/alembic.ini revision --autogenerate -m "$(msg)"

db-reset:  ## 重置数据库
	alembic -c infra/db/alembic.ini downgrade base
	alembic -c infra/db/alembic.ini upgrade head

# ─── 清理 ───

clean:  ## 清理缓存
	rm -rf `find . -type d -name __pycache__`
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf .venv

# ─── 帮助 ───

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
