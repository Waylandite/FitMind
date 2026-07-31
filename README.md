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
  → ChatService（Session、上下文和 SSE 主编排）
  → IntentClassifier（关键词 + LLM 结构化分类）
  → Pending Draft Gate（挂起业务草稿优先）
  → IntentResolutionPolicy（置信度与候选冲突安全闸）
  → IntentClarification（必要时持久化澄清）
  → IntentRouter（唯一意图 → 领域服务）
  → 查询类直接响应 / 写入类草稿确认
  → MySQL 结构化落库与日志追踪
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
| 周报与趋势 | `weekly_trend_report` | 按自然周确定性计算训练、饮食和恢复指标，对比上周同期并生成简洁周报 |
| 今日训练推荐 | `today_workout_recommendation` | 并发查询最新长期计划和最近 7 天训练记录，LLM 结合恢复状态生成训练建议 |
| 训练日志查询与回顾 | `workout_history_query` | 按日期、部位和动作筛选真实训练记录，返回确定性统计与动作明细 |

### 对话与系统

| 功能 | 说明 |
|------|------|
| 普通 LLM 对话 | 带 session summary 上下文压缩的多轮对话 |
| 草稿确认机制 | 所有业务写入均经过 `提取 → 草稿 → 确认 → 持久化` 四段流程 |
| 多轮上下文感知 | pending workflow context 检测，自动识别确认/取消/修正意图 |
| 持久化意图澄清 | 低置信度、候选接近或多写入冲突时先展示候选；支持按钮、自由文本、取消、过期、两轮失败与刷新恢复 |
| Session 管理 | 新建、切换和恢复会话，最近对话窗口与历史摘要共同进入模型上下文 |
| Agent 执行可视化 | 前端实时展示工具调用过程（状态标签、工具名、参数、返回、耗时） |
| 意图识别日志 | 每次分类结果写入 `intent_recognition_logs`，支撑效果评估和 prompt 迭代 |
| Token 统计 | 单次 LLM 调用明细（`llm_call_logs`）+ 每轮对话聚合（`chat_turn_token_usage`），旁路异步写入 |
| SSE 流式响应 | Intent → Session → Agent State → Workflow → Delta → Done 六级事件序列 |

### Web 产品能力

| 功能 | 说明 |
|------|------|
| 登录与注册体验 | 深浅分区首页、登录/注册表单校验和默认测试账号入口 |
| 对话工作区 | 左右消息布局、Markdown 渲染、SSE 打字机输出、智能自动滚动和思考过程卡片 |
| 训练历史页 | 日期、部位和动作筛选，分页展示训练记录与确定性统计 |
| 周报趋势页 | 自然周切换、数据覆盖率、训练/饮食/恢复趋势与部位分布图 |
| 用户档案 | 编辑身高、体重、目标、训练水平、训练日、伤病和饮食背景 |
| 自定义记忆 | 维护训练偏好、关注主题、回答风格、饮食偏好和健康限制 |

---

## 当前边界

FitMind 已经具备完整的单用户开发链路，但距离生产环境仍有明确边界：

- 当前通过明文 `user_id` 标识用户，尚未接入 JWT、OAuth2、RBAC 和租户隔离
- 登录与注册目前是前端体验和接口占位，不是完整账号系统
- 营养 ReAct 已支持本地食物数据工具，外部权威营养数据库仍以 MCP 扩展点保留
- 用户自定义记忆已可编辑；Agent 派生记忆的自动提取、冲突合并和人工审阅仍待完善
- 当前主要面向桌面端，移动端布局、离线能力和消息推送尚未完成
- 健康建议用于训练与生活方式参考，不替代医疗诊断

---

## 技术方案

### 前端

- `React 19` + `Vite 8` + `Tailwind CSS 4` + `Recharts 3`
- SSE 流式消费 + 打字机渲染
- Agent 执行过程时间线可视化（`AgentThoughtProcess`）
- 草稿确认卡片交互（确认保存 / 取消保存 / 纠正错误）
- 意图澄清卡片交互（候选选择 / 自由补充 / 取消 / 刷新恢复）
- 独立训练历史页、周报趋势页、用户档案与自定义记忆面板

### 后端 Agent

- `Python 3.11+` + `FastAPI` + `Pydantic`
- 架构：`IntentClassifier → Pending Gate → ResolutionPolicy → IntentRouter → ServiceChain`
- 意图识别：关键词规则预判 + LLM 结构化分类，双模决策
- 安全决策：`IntentResolutionPolicy` + 持久化 `IntentClarificationService`
- 营养链路：LangGraph ReAct 循环 + MCP-ready 工具提供者
- 查询链路：`ThreadPoolExecutor` 并发查询数据库 + LLM 汇总生成
- `DeepSeekLLMClient`（OpenAI-compatible SDK）

### 数据层

- `MySQL 8.0+` + `SQLAlchemy 2.0` + `Alembic`
- 20 张核心表：用户与档案、训练计划/记录/明细、饮食、身体状态、4 张草稿表、对话/意图日志、Session/摘要、两层记忆、意图澄清、LLM 调用日志和 Token 汇总
- 最新迁移：`20260731_000010_add_intent_clarifications`

详见 [docs/database-design.md](docs/database-design.md)

---

## 项目时间线

| 日期 | 提交 | 更新内容 |
|------|------|---------|
| 2026-07-31 | `0990ea6` | 新增持久化意图澄清、安全决策策略、前端澄清卡片和恢复协议 |
| 2026-07-30 | `44b8e7f` | 新增自然周周报、跨周确定性统计、趋势图与聊天 SSE 周报链路 |
| 2026-07-30 | `166468c` | 新增训练历史查询、动作部位映射、筛选 API 与独立历史页 |
| 2026-06-17 | `fd820c6` | 新增用户档案和自定义记忆编辑入口 |
| 2026-06-17 | `9a1b22c` | 新增当日训练推荐工作流与 Agent 状态可视化 |
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

### 下一阶段：生产安全与记忆闭环

- 接入 JWT/OAuth2 鉴权、密码哈希、登录态持久化与多用户数据隔离
- 将用户档案、自定义记忆和 Agent 派生记忆稳定注入对话与推荐上下文
- 实现记忆冲突检测、版本管理、人工确认和可追溯来源
- 增加意图识别评估集、Prompt 回归测试和低置信度运营指标

### 第二阶段：训练分析增强

- 标准化动作、重量、次数、距离和时长字段，计算训练容量与渐进超负荷趋势
- 增加多周、月度和自定义周期趋势，支持计划完成率与训练负荷分析
- 前端展示每轮、Session 和用户维度的 Token 与模型成本
- 将权威食物营养数据源封装为远程 MCP 服务，并完善工具降级策略

### 第三阶段：产品化

- 完整移动端适配、PWA、离线草稿和消息提醒
- 图片识别辅助饮食与器械训练记录
- 导入可穿戴设备和健康平台数据
- 支持自定义训练计划周期模板
- 完善审计、限流、监控、备份和隐私合规能力

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
cp .env.example .env
# 在 .env 中配置 FITMIND_DATABASE_URL 与 FITMIND_LLM_API_KEY
alembic upgrade head
uvicorn fitmind_agent.main:app --reload --port 8000
```

### 质量检查

```bash
cd agent
pytest -q
ruff check .

cd ../web
npm run lint
npm run build
```

当前主分支验证基线：后端 `75 passed`，Ruff、ESLint 和 Vite production build 均通过。

### 当前本地链路

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 流式对话：`POST /api/v1/chat/stream`
- 直连 LLM：`POST /api/v1/llm/chat`
- 训练历史：`GET /api/v1/workouts/history?user_id=1&start_date=2026-07-24&end_date=2026-07-30`
- 周报趋势：`GET /api/v1/analytics/weekly?user_id=1&anchor_date=2026-07-30`
- 用户档案：`GET/PUT /api/v1/profiles/{user_id}`
- 自定义记忆：`GET/POST/PATCH/DELETE /api/v1/memories/user-defined`
- 当前澄清：`GET /api/v1/memories/sessions/{session_id}/clarification?user_id=1`

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/agent-architecture.md](docs/agent-architecture.md) | Agent 架构设计，服务链编排、意图系统、执行链路 |
| [docs/intent-system.md](docs/intent-system.md) | 意图类型、路由模块和实现状态 |
| [docs/database-design.md](docs/database-design.md) | 面向健身数据的 20 张核心表与迁移设计 |
| [docs/memory-system-design.md](docs/memory-system-design.md) | 三层记忆体系与 Session 管理 |
| [docs/nutrition-react-design.md](docs/nutrition-react-design.md) | 饮食记录 ReAct / MCP 工具调用设计 |
| [docs/nutrition-tools-contract.md](docs/nutrition-tools-contract.md) | 饮食工具调用契约与数据格式 |
| [docs/token-usage-design.md](docs/token-usage-design.md) | LLM token 统计、调用明细与对话聚合设计 |
| [docs/project-overview.md](docs/project-overview.md) | 原始长版项目说明备份 |
| [docs/intent-routing-test-report.md](docs/intent-routing-test-report.md) | 意图识别联调测试报告 |
| [docs/workout-record-workflow-report.md](docs/workout-record-workflow-report.md) | 训练记录提取与确认流程报告 |
| [docs/weekly-trends-design.md](docs/weekly-trends-design.md) | 自然周对比、统计口径和趋势页接口设计 |

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
