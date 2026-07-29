# DeepDocs

全格式、可追溯、DeepSeek 优先的私有文档研究工作台。

## 快速开始

```bash
# 克隆仓库
git clone <repo-url> deepdocs
cd deepdocs

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key

# 启动开发环境
docker compose up -d

# 查看 API
open http://localhost:8000/docs
```

## 系统架构

```
Web (Next.js) → FastAPI API → PostgreSQL (元数据)
                              ├── MinIO (原始文件)
                              ├── Redis (任务队列)
                              └── Qdrant (向量索引)

Worker: Celery/Dramatiq → Parser Registry → BGE-M3 Embedding → Qdrant
                                              └── DeepSeek API → 问答 + 引用
```

## 项目目录

```
apps/
  api/          FastAPI 应用层
  web/          Next.js 前端（TODO）
workers/
  ingestion/    异步文档摄取
packages/
  core/         核心数据模型与配置
  parsers/      格式解析器注册表
  providers/    LLM / Embedding / Reranker 适配器
  retrieval/    检索引擎（混合检索 + 上下文构建 + 引用校验）
infra/
  db/           Alembic 数据库迁移
tests/
  unit/         单元测试
  integration/  集成测试
  corpus/       测试文档样本
  eval/         RAG 评测集
```

## 支持格式

| 格式 | 解析方式 | 状态 |
|------|---------|------|
| PDF | Docling + PyMuPDF + PaddleOCR（扫描件） | 🔜 |
| DOCX | python-docx | 🔜 |
| PPTX | python-pptx | 🔜 |
| XLSX | openpyxl | 🔜 |
| TXT/MD | 编码检测 + 标题提取 | 🔜 |
| HTML | trafilatura + BeautifulSoup | 🔜 |
| CSV/JSON | 标准库 | 🔜 |
| PNG/JPG/TIFF | PaddleOCR | 🔜 |

## Tech Stack

- **API**: FastAPI + SQLAlchemy (async) + PostgreSQL
- **向量**: Qdrant (Dense + Sparse 混合检索)
- **嵌入**: BGE-M3（本地） / 云端备选
- **重排**: BGE Reranker（本地）
- **LLM**: DeepSeek Chat / Reasoner
- **队列**: Dramatiq + Redis
- **存储**: MinIO / S3
- **解析**: Docling + 格式专用适配器
- **前端**: Next.js + TypeScript（TODO）

## 开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 数据库迁移
alembic -c infra/db/alembic.ini upgrade head

# 运行测试
pytest

# 代码检查
ruff check .
mypy packages/
```
