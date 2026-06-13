<div align="center">

# FitMind

### 用自然语言记录训练、饮食与身体状态，让健身数据真正沉淀下来

[![Python](https://img.shields.io/badge/Python-3.11+-2F6690?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-0E7C66?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Workflow-1F3A5F?style=for-the-badge)](https://www.langchain.com/langgraph)
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

FitMind 想解决的不是“陪聊”，而是：

- 听懂这些自然语言表达
- 拆成训练计划、训练结果、身体状态、饮食记录
- 转成结构化事实
- 最终为数据库、分析和复盘提供稳定输入

一句话概括：

> FitMind 是一个面向健身场景的对话式数据入口，而不是普通聊天机器人。

---

## 项目定位

FitMind 当前由两部分组成：

- `web`
  提供登录体验、对话页和用户交互入口
- `agent`
  提供 Python API、LangGraph 工作流骨架和后续数据处理能力

核心目标是构建一条完整链路：

```text
自然语言输入
  -> Web 对话界面
  -> Python Agent API
  -> 意图识别与 Agent 工作流
  -> 健身结构化事实
  -> 数据库存储与后续分析
```

---

## 核心能力

### 1. 训练计划记录

- 识别训练部位、动作、组数、次数、重量
- 支持日计划、周计划和自然语言补充

### 2. 训练结果记录

- 记录实际完成情况
- 支持计划与实际偏差对比
- 支持动作、组次、重量、时长等结构化提取

### 3. 身体状态记录

- 独立识别 `today_body_status_record`
- 记录睡眠、疲劳、酸痛、体重、压力、心情和恢复状态
- 支持同日多次记录，`raw_text` 按时间刻度追加
- 结构化字段保留最新非空快照
- 为训练解释和后续建议提供上下文

### 4. 饮食与补剂记录

- 独立识别 `today_nutrition_record`
- 记录餐次、食物、份量、补剂和营养估算
- 读取当天已有饮食记录作为上下文
- 饮食字段表示“今天截至目前”的累计估算值
- 已预留 ReAct / MCP 工具接入，用于后续更准确计算热量、蛋白、碳水和脂肪

### 5. 修改与补录

- 支持用户通过自然语言纠正历史记录
- 支持补充漏记的数据

---

## 技术方案

### 前端

- `React`
- `Vite`
- `Tailwind CSS`

负责：

- 登录页与产品首页
- 对话工作台
- 后续训练记录与日志查看界面

### 后端 Agent

- `Python 3.11+`
- `FastAPI`
- `Pydantic`
- `LangChain / LangGraph`
- `OpenAI Compatible SDK`
- `DeepSeek Official API`

负责：

- 提供 Web 调用的 API
- 承接用户对话消息
- 路由训练、状态、饮食等意图
- 输出结构化结果
- 维护多轮对话上下文
- 提供 SSE 流式返回
- 记录意图识别结果，方便追踪和调试
- 为饮食记录预留 ReAct 工具调用链路

### 数据层

当前仓库已经完成新的数据库与迁移基础设施，重点围绕：

- `MySQL`
- `SQLAlchemy 2.0`
- `Alembic`
- 普通用户表
- 健身档案
- 训练计划
- 训练执行
- 身体状态
- 饮食记录
- 对话日志
- 意图识别日志
- Session 短期记忆
- 水位线 Summary 压缩

详见：

- [docs/database-design.md](docs/database-design.md)

---

## 当前仓库结构

```text
FitMind/
  agent/    # Python Agent 服务，API 与 LangGraph 骨架
  web/      # React Web 应用，登录页与对话页
  docs/     # 项目设计文档与备份说明
  README.md
```

---

## 已完成内容

- 登录页与对话页前端原型
- Web 对话页接入后端流式 SSE Chat
- Python Agent API、DeepSeek 官方模型接入
- MySQL + SQLAlchemy + Alembic 数据层落地
- 健身数据导向的核心表与记忆表设计
- Session 级多轮上下文窗口
- 基于水位线的历史 Summary 压缩机制
- 对话日志持久化与本地联调验证
- 意图识别结果落库到 `intent_recognition_logs`
- 当日训练记录：结构化提取、用户确认、动作明细落库
- 当日饮食记录：独立意图、今日上下文填充、ReAct 工具接入预留、饮食表落库
- 当日身体状态记录：独立意图、今日上下文填充、身体状态表落库
- 饮食和身体状态表已移除 `remark`，统一使用 `raw_text` 保存原始流水

---

## 开发路线

### 近期

- 接入饮食 ReAct 工具链：食物识别、份量估算、营养查询和汇总
- Session Summary 与长期记忆联动
- 完善用户计划更新、最近训练总结和今日训练推荐模块

### 中期

- 支持纠错与补录流程
- 支持训练日志查询与回顾
- 构建可解释的健身记忆系统

### 后续

- 引入更完整的 LangGraph 工作流
- 增强结构化追问和工具调用
- 支持周报、复盘和趋势分析

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

- [docs/project-overview.md](docs/project-overview.md)  
  原始长版项目说明备份

- [docs/agent-architecture.md](docs/agent-architecture.md)  
  Agent 与子 Agent 架构说明

- [docs/database-design.md](docs/database-design.md)  
  面向健身计划与训练数据的数据库设计

- [docs/intent-system.md](docs/intent-system.md)  
  当前支持的意图类型、路由模块和实现状态

- [docs/nutrition-react-design.md](docs/nutrition-react-design.md)  
  饮食记录 ReAct / MCP 工具调用设计

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Waylandite/FitMind&type=Date)](https://star-history.com/#Waylandite/FitMind&Date)

---

## 愿景

FitMind 的目标不是把自己做成一个“会聊天的健身助手”，而是做成一个真正能沉淀健身数据的自然语言系统：

- 让用户更轻松地记录
- 让训练数据更清晰地积累
- 让后续分析、复盘和建议建立在真实数据之上

如果你也对“AI + 健身记录 + 结构化数据”这个方向感兴趣，欢迎一起完善 FitMind。
