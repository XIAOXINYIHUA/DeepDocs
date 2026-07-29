---
name: deepdocs-project-progress
description: DeepDocs 全格式文档研究工作台项目进度记录
metadata:
  type: project
---

# DeepDocs 项目进度

## 状态：工程底座完成，待 Docker 环境启动

### 已完成的全部工作

**后端（Python）** — 全部代码就绪
- 工程底座：docker-compose.yml（6 服务）+ Alembic 迁移（11 张表）
- 9 个 ORM 实体：User/Workspace/KB/Document/Version/Block/Chunk/IndexProfile/Citation
- 认证：JWT + bcrypt 注册登录
- API：16 个端点（health/auth/workspaces/knowledge-bases/documents/chat/summary）
- 9 个格式解析器：PDF(Docling+PyMuPDF) / DOCX / PPTX / XLSX / TXT / MD / HTML / CSV / JSON
- OCR 引擎：PaddleOCR + 失败回退
- 结构化分块：标题感知分组 + Token 预算 + 父子 Chunk + SHA-256 去重
- DeepSeek 适配器：Chat/Stream/Reasoner + 成本估算
- BGE-M3 Embedding + Reranker（本地）
- 混合检索：Qdrant Dense+Sparse + 索引签名保护
- 引用校验：CitationVerifier
- 摄取 Worker：Dramatiq 完整链路
- 30 个单元测试全部通过

**前端（Next.js）** — 核心骨架完成
- TypeScript 类型定义（与后端完全对齐）
- API 客户端封装（auth/projects/kb/documents/analysis）
- 三栏布局：Sidebar(文档树) + MainPanel(预览) + AnalysisPanel(AI分析)
- 项目列表页 + 项目工作台页（含流式问答/引用卡片/证据覆盖指示）

**14 天验证框架**
- tests/corpus/：4 份样本文档
- tests/eval/runner.py：三阶段指标评测

### 受阻原因
- Docker 无法启动：需在 BIOS 开启虚拟化（Intel VT-x / AMD-V）

### 下次继续要做的事
1. 重启进 BIOS 开启虚拟化 → 启动 Docker Desktop
2. `! docker compose up -d`
3. `! alembic -c infra/db/alembic.ini upgrade head`
4. 另一终端：`cd apps/web && npm install && npm run dev`

### 关键路径
C:\Users\ROG\Desktop\Github\DeepDocs
