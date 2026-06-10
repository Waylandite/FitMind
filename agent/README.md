# FitMind Agent

FitMind Agent 是当前项目的 Python 服务端，用于承接 Web 应用请求、编排 LangGraph 工作流，并把自然语言健身数据转成结构化结果。

## 当前目标

- 提供 Web 可调用的 HTTP API
- 承接登录后对话请求
- 维护多轮 Session 上下文
- 提供 SSE 流式对话输出
- 提供 SQLAlchemy + Alembic + MySQL 数据层基础设施
- 提供 Session Summary 水位线压缩能力

## 推荐目录

```text
agent/
  alembic/
  src/fitmind_agent/
    api/
    core/
    db/
    graphs/
    schemas/
    services/
  tests/
```

## 当前技术栈

- `FastAPI`
- `Pydantic`
- `LangChain / LangGraph`
- `SQLAlchemy 2.0`
- `Alembic`
- `PyMySQL`
- `OpenAI Compatible SDK`
- `DeepSeek Official API`

## 本地启动

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn fitmind_agent.main:app --reload --port 8000
```

## 数据库迁移

```bash
cd agent
alembic upgrade head
```

## 数据库配置位置

当前数据库连接主要看两个地方：

1. 本地运行时配置：
   `agent/.env`
2. 默认示例配置：
   `agent/.env.example`

当前默认示例已经切到 MySQL：

```env
FITMIND_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/fitmind?charset=utf8mb4
```

如果你本地用户名、密码或数据库名不同，直接改 `agent/.env` 即可。

## 默认接口

- `GET /healthz`
- `GET /api/v1/meta`
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`
- `POST /api/v1/llm/chat`
- `POST /api/v1/memories/*`

## LLM 配置

当前项目已经内置了一个基于 `OpenAI` 兼容协议的 DeepSeek 官方 LLM 工具类，默认读取：

- `FITMIND_LLM_API_KEY`
- `FITMIND_LLM_BASE_URL`
- `FITMIND_LLM_MODEL`
- `FITMIND_LLM_TEMPERATURE`

核心位置：

- `fitmind_agent.core.llm.DeepSeekLLMClient`
- `fitmind_agent.services.llm_service.LLMService`

测试接口示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ],
    "model": "deepseek-v4-flash",
    "temperature": 0.7
  }'
```

## 与 Web 的关系

Web 登录后进入对话页，对话请求会直接调用这个 Agent 服务。

当前已经打通：

- 前端输入消息
- 后端 SSE 流式返回
- 对话日志写入 `conversation_logs`
- 当前 session 最近 `N` 轮上下文读取
- 超过窗口的历史消息压缩进 `running_summary`
