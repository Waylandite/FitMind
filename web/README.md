# FitMind Web

FitMind 的 React Web 客户端，负责真实账号登录、Session 对话、SSE 流式回复、Agent 状态展示、业务草稿确认、训练历史和周报趋势。

## 技术栈

- React 19 + Vite 8
- Tailwind CSS 4
- React Markdown + remark-gfm
- Recharts
- Vitest + ESLint

## 本地运行

```bash
npm install
npm run dev
```

默认访问 `http://127.0.0.1:5173`，通过 `/api/v1` 协议连接 FitMind Agent 服务。

## 质量检查

```bash
npm test
npm run lint
npm run build
```

鉴权状态统一由 `src/auth/AuthContext.jsx` 管理，普通请求统一经过 `src/lib/apiClient.js`；页面组件不要直接持久化 Access Token 或自行拼接用户 ID。
