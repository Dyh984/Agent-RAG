# Agent + RAG 文档入库 MVP

当前版本实现第一阶段文档入库闭环：知识库持久化、PDF 上传、逐页解析、文本切片、处理状态、切片查询和安全删除。Embedding、向量检索、LLM 问答与 Agent 工作流将在后续阶段接入。

## 环境要求

- Python 3.13
- PostgreSQL 18
- Node.js（仅用于前端语法检查）

当前阶段不需要 Docker，也不依赖 pgvector。

## 安装

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

根据 `.env.example` 在本地配置应用环境变量。请使用权限受限的 PostgreSQL 应用账号，并通过安全的本地方式提供凭据；不要提交任何 `.env` 文件或真实密码。

数据库由管理员预先创建后，执行迁移：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

## 启动

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

服务启动后可访问 API 根地址。健康检查接口：

- `GET /api/health/live`：检查 API 进程。
- `GET /api/health`：检查 API 与数据库连接。

## 测试

```powershell
$env:PYTHONPATH='backend;.'
.\.venv\Scripts\python.exe -m pytest backend\tests tests -v
node --check frontend\api.js
```

测试应连接隔离的测试数据库，不能复用生产或日常开发数据。

## 当前支持范围

- 文本型 PDF 入库，默认最大 20 MiB。
- 默认按 800 字符切片并保留 100 字符重叠及真实 PDF 页码。
- 同一知识库内通过 SHA-256 拒绝重复文件。
- 图片扫描 PDF 会进入 `failed` 状态，后续可接入 OCR。
- DOCX、TXT、Markdown 和图片问答暂未开放。
- 智能问答区域目前是界面演示，尚未连接 RAG 或 LLM。

## 安全约束

- 环境文件、数据库凭据、上传内容和内部开发文档均不得提交。
- 删除接口只允许处理配置的上传根目录内的精确文件。
- 生产环境应使用最小权限数据库账号并独立管理密钥。
