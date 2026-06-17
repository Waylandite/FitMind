<div align="center">

# FitMind

### 用自然语言记录训练、饮食与身体状态，让健身数据真正沉淀下来

[![Python](https://img.shields.io/badge/Python-3.11+-2F6690?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-0E7C66?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-ReAct_Loop-1F3A5F?style=for-the-badge)](https://www.langchain.com/langgraph)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-AA2B1D?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migration-5B4B8A?style=for-the-badge)](https://alembic.sqlalchemy.org/)
[![MySQL](https://img.shields.io/badge/MySQL-Storage-005C84?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-LLM-1E3A8A?style=for-the-badge)](https://api.deepseek.com/)
[![React](https://img.shields.io/badge/React-Frontend-1C3144?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-Build-6C63FF?style=for-the-badge&logo=vite&logoColor=white)](https://vite.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-UI-0B7285?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

<p>
  <img src="https://skillicons.dev/icons?i=python,fastapi,mysql,react,vite,tailwind,git" alt="FitMind 技术栈图标" />
</p>

</div>

---

## 项目背景

大多数健身记录产品依赖表单输入，但真实场景里，用户更习惯直接说：

- 今天练胸，卧推 60kg 5x5
- 原计划跑 8 公里，最后只跑了 5 公里
- 昨晚没睡好，今天状态一般
- 晚饭吃了鸡胸、米饭和蛋白粉

FitMind 想解决的不是"陪聊"，而是：

- 听懂这些自然语言表达
- 拆成训练计划、训练结果、身体状态、饮食记录
- 转成结构化事实
- 最终为数据库、分析和复盘提供稳定输入

一句话概括：

> FitMind 是一个面向健身场景的对话式数据入口，而不是普通聊天机器人。

---

## 项目定位

FitMind 当前由两部分组成：

- `web` — 提供登录体验、对话页和用户交互入口
- `agent` — 提供 Python API、意图识别、服务链编排和领域数据处理能力

架构采用 **顺序服务链** 模式（详见 [agent-architecture.md](docs/agent-architecture.md)）：

```text
自然语言输入
  → Web 对话界面
  → ChatService（主编排器、session 管理）
  → IntentClassifier（关键词 + LLM 双模意图分类）
  → IntentRouter（意图 → 模块路由）
  → ServiceChain（健康总结 → 训练推荐 → 饮食 → 身体状态 → 训练记录 → 计划更新）
  → 草稿确认 → 结构化落库
```

---

## 已实现功能

### 记录类（写入 + 草稿确认）

| 功能 | 意图 | 说明 |
|------|------|------|
| 当日训练记录 | `today_workout_record` | 提取训练动作、组数、重量，草稿确认后写入 `user_workout_records` + `user_workout_record_items` |
| 当日饮食记录 | `today_nutrition_record` | LangGraph ReAct 循环驱动工具调用（食物查询、份量估算、营养计算、累计汇总），草稿确认后写入 `user_nutrition_records` |
| 当日身体状态 | `today_body_status_record` | 提取睡眠、疲劳、压力、酸痛、体重、情绪，草稿确认后写入 `user_body_status_records` |
| 训练计划更新 | `user_workout_plan_update` | 提取长期训练计划标题、日期、内容，草稿确认后写入 `user_workout_plans` |

### 查询类（流式 + 直接返回）

| 功能 | 意图 | 说明 |
|------|------|------|
| 最近健康总结 | `recent_health_summary` | 并发查询最近 7 天训练、饮食、身体状态和长期计划，LLM 汇总生成结构化总结 |
| 今日训练推荐 | `today_workout_recommendation` | 并发查询最新长期计划和最近 7 天训练记录，LLM 结合恢复状态生成训练建议 |

### 对话与系统

| 功能 | 说明 |
|------|------|
| 普通 LLM 对话 | 带 session summary 上下文压缩的多轮对话 |
| 草稿确认机制 | 所有业务写入均经过 `提取 → 草稿 → 确认 → 持久化` 四段流程 |
| 多轮上下文感知 | pending workflow context 检测，自动识别确认/取消/修正意图 |
| Agent 执行可视化 | 前端实时展示工具调用过程（状态标签、工具名、参数、返回、耗时） |
| 意图识别日志 | 每次分类结果写入 `intent_recognition_logs`，支撑效果评估和 prompt 迭代 |
| Token 统计 | 单次 LLM 调用明细（`llm_call_logs`）+ 每轮对话聚合（`chat_turn_token_usage`），旁路异步写入 |
| SSE 流式响应 | Intent → Session → Agent State → Workflow → Delta → Done 六级事件序列 |

---

## 未实现功能

| 功能 | 说明 |
|------|------|
| 澄清追问 | `unknown` 意图已预留路由，当置信度不足时的主动追问逻辑待实现 |
| 训练日志查询回顾 | 按日期/部位/动作查询历史训练记录 |
| 周报与趋势分析 | 基于结构化数据的健身趋势可视化和复盘 |
| 记忆冲突处理 | Agent 提取的长期记忆与用户显式记忆冲突时的协调机制 |
| 移动端适配 | 当前以桌面端为主 |

---

## 技术方案

### 前端

- `React 19` + `Vite 8` + `Tailwind CSS 4`
- SSE 流式消费 + 打字机渲染
- Agent 执行过程时间线可视化（`AgentThoughtProcess`）
- 草稿确认卡片交互（确认保存 / 取消保存 / 纠正错误）

### 后端 Agent

- `Python 3.11+` + `FastAPI` + `Pydantic`
- 架构：`IntentClassifier → IntentRouter → ServiceChain`
- 意图识别：关键词规则预判 + LLM 结构化分类，双模决策
- 营养链路：LangGraph ReAct 循环 + MCP-ready 工具提供者
- 查询链路：`ThreadPoolExecutor` 并发查询数据库 + LLM 汇总生成
- `DeepSeekLLMClient`（OpenAI-compatible SDK）

### 数据层

- `MySQL 8.0+` + `SQLAlchemy 2.0` + `Alembic`
- 19 张核心表：用户、档案、训练计划/记录/明细、饮食、身体状态、4 张草稿表、对话日志、意图日志、Session/摘要、两层记忆、LLM 调用日志、Token 汇总

详见 [docs/database-design.md](docs/database-design.md)

---

## 项目时间线

| 日期 | 提交 | 更新内容 |
|------|------|---------|
| 2026-06-16 | `49d2e47` | 新增最近健康总结，并发查询训练/饮食/身体状态/计划 |
| 2026-06-16 | `c3f2b91` | 前端 Agent 执行过程可视化，完善训练记录展示 |
| 2026-06-15 | `9422e5e` | 新增 LLM token 使用统计（调用明细 + 对话聚合） |
| 2026-06-14 | `53f91da` | 饮食记录接入 LangGraph ReAct 循环，身体状态独立草稿流程 |
| 2026-06-13 | `fae775a` | 新增意图识别 + 路由系统，训练记录草稿确认流程 |
| 2026-06-11 | `54ad105` | 流式 SSE 对话、Session 管理、上下文压缩 |
| 2026-06-09 | `a3508c3` | README 重构，项目定位和核心能力说明 |
| 2026-06-09 | `79e9b85` | 项目初始化，前端原型 + Agent API 骨架 |

---

## 开发路线

### 近期

- 当前轮：完善今日训练推荐，更新文档一致性
- 澄清追问模块（`unknown` 意图路由已预留）
- 前端展示每轮对话 token 消耗和 session 累计消耗

### 中期

- 训练日志查询与回顾界面
- 构建可解释的健身记忆系统
- 记忆冲突处理与人工确认

### 后续

- 周报、复盘和趋势分析
- 移动端适配
- 支持自定义训练计划周期模板

---

## 当前仓库结构

```text
FitMind/
  agent/       # Python Agent 服务，API 与领域服务链
  web/         # React Web 应用，登录页与对话页
  docs/        # 项目设计文档
  dataset/     # 测试用例与评估数据
  README.md
```

---

## 快速开始

### 启动前端

```bash
cd web
npm install
npm run dev
```

### 启动 Agent 服务

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn fitmind_agent.main:app --reload --port 8000
```

### 当前本地链路

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 流式对话：`POST /api/v1/chat/stream`
- 直连 LLM：`POST /api/v1/llm/chat`

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/agent-architecture.md](docs/agent-architecture.md) | Agent 架构设计，服务链编排、意图系统、执行链路 |
| [docs/intent-system.md](docs/intent-system.md) | 意图类型、路由模块和实现状态 |
| [docs/database-design.md](docs/database-design.md) | 面向健身数据的 19 张核心表设计 |
| [docs/memory-system-design.md](docs/memory-system-design.md) | 三层记忆体系与 Session 管理 |
| [docs/nutrition-react-design.md](docs/nutrition-react-design.md) | 饮食记录 ReAct / MCP 工具调用设计 |
| [docs/nutrition-tools-contract.md](docs/nutrition-tools-contract.md) | 饮食工具调用契约与数据格式 |
| [docs/token-usage-design.md](docs/token-usage-design.md) | LLM token 统计、调用明细与对话聚合设计 |
| [docs/project-overview.md](docs/project-overview.md) | 原始长版项目说明备份 |
| [docs/intent-routing-test-report.md](docs/intent-routing-test-report.md) | 意图识别联调测试报告 |
| [docs/workout-record-workflow-report.md](docs/workout-record-workflow-report.md) | 训练记录提取与确认流程报告 |

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Waylandite/FitMind&type=Date)](https://star-history.com/#Waylandite/FitMind&Date)

---

## 愿景

FitMind 的目标不是把自己做成一个"会聊天的健身助手"，而是做成一个真正能沉淀健身数据的自然语言系统：

- 让用户更轻松地记录
- 让训练数据更清晰地积累
- 让后续分析、复盘和建议建立在真实数据之上

如果你也对"AI + 健身记录 + 结构化数据"这个方向感兴趣，欢迎一起完善 FitMind。
