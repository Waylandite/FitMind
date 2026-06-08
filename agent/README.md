# FitMind Agent

FitMind Agent 是当前项目的 Python 服务端，用于承接 Web 应用请求、编排 LangGraph 工作流，并把自然语言健身数据转成结构化结果。

## 当前目标

- 提供 Web 可调用的 HTTP API
- 承接登录后对话请求
- 预留 LangGraph 主图和子模块目录
- 预留后续数据库、schema、service 层扩展位

## 推荐目录

```text
agent/
  src/fitmind_agent/
    api/
    core/
    graphs/
    schemas/
    services/
  tests/
```

## 本地启动

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn fitmind_agent.main:app --reload --port 8000
```

## 默认接口

- `GET /healthz`
- `GET /api/v1/meta`
- `POST /api/v1/chat`

## 与 Web 的关系

Web 登录后进入对话页，对话请求后续会直接调用这个 Agent 服务。
