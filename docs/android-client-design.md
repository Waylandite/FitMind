# FitMind Android 原生客户端 V1

## 1. 目标与边界

Android V1 是 FitMind 的原生移动入口，优先保证核心对话闭环可用：真实账号、Session 管理、多轮 SSE 对话、Agent 状态、业务草稿确认和意图澄清。后端数据库仍是唯一事实来源，Room 仅负责离线只读缓存。

首版不复制 Web 的桌面玻璃拟态，而采用品牌化 Material 3。手机使用会话抽屉，宽屏设备自动切换为会话列表与聊天双栏。

## 2. 技术栈

- Kotlin、Jetpack Compose、Material 3
- Repository + ViewModel + 单向数据流
- Coroutines、Flow、Hilt
- Retrofit、OkHttp、Kotlin Serialization
- Room 2.8
- Material 3 Markdown Renderer
- JDK 17、Gradle 9.5、AGP 9.3
- `compileSdk/targetSdk 36`，`minSdk 26`

## 3. 工程结构

```text
android/app/src/main/java/com/fitmind/app/
  core/designsystem/  # 品牌主题、色板、形状和排版
  core/network/       # Retrofit、OkHttp、SSE、令牌刷新和加密 Cookie
  core/database/      # Room Session 与消息只读缓存
  core/di/            # Hilt 依赖装配
  core/model/         # UI 与领域模型
  data/               # Auth、Chat Repository
  feature/auth/       # 启动恢复、登录、注册
  feature/chat/       # Session、消息、思考轨迹、草稿与澄清
  ui/                 # 应用导航入口
```

## 4. 安全设计

- Access Token 只存在于 `AuthSessionStore` 的进程内存，不写磁盘和日志。
- 只持久化名为 `fitmind_refresh_token` 的 Refresh Cookie。
- Cookie 使用 Android Keystore 内 AES-256-GCM 密钥加密，SharedPreferences 只保存密文。
- `fitmind_auth.xml` 被 Cloud Backup 和设备迁移同时排除。
- 并发 `401` 通过 `RefreshCoordinator` 的 `Mutex` 合并为一次刷新，其余请求等待后重试。
- 刷新失败统一清理 Access Token、Cookie 和用户态。
- Debug 允许连接模拟器宿主机 `http://10.0.2.2:8000/api/v1/`；Release 禁止明文流量，发布前必须替换为真实 HTTPS 域名。

## 5. SSE 协议

`POST /api/v1/chat/stream` 使用共享认证 OkHttpClient。客户端解析以下事件：

| 事件 | Android 类型 | 用途 |
|------|--------------|------|
| `intent` | `IntentRecognized` | 展示当前识别意图 |
| `session` | `SessionConnected` | 绑定服务端 Session |
| `agent_state` | `AgentState` | 构建可折叠思考轨迹 |
| `workflow` | `Workflow` | 恢复或展示业务草稿 |
| `clarification` | `Clarification` | 展示意图候选卡片 |
| `delta` | `Delta` | 实时追加 Markdown 回复 |
| `done` | `Done` | 完成本轮消息 |
| `error` | `Error` | 安全结束并提示重试 |

未知事件会被忽略，不会导致整条流失败；协程取消会同步取消底层 OkHttp Call。

## 6. 会话恢复与离线规则

打开 Session 时并发请求：

1. `/memories/sessions/{session_id}/messages`
2. `/memories/sessions/{session_id}/clarification`
3. `/memories/sessions/{session_id}/pending-workflow`

消息与 Session 元数据写入 Room；Agent Trace、流式临时消息、草稿卡片和澄清卡片不长期缓存，而是联网时从后端恢复。离线状态允许浏览缓存，但禁用新建 Session、发送消息、确认草稿和处理澄清。

## 7. 交互规则

- 用户发送消息后自动恢复追踪最新内容。
- 用户手动上滑时停止自动滚动，并显示“回到最新”。
- 第一段 `delta` 到达前显示动态思考耗时。
- Agent 思考卡片位于对应助手消息上方，默认折叠。
- 草稿只提供确认、取消和纠错；纠错回填自然语言，不暴露 JSON。
- 意图澄清支持候选按钮、自由文本补充和取消，重启后可恢复。

## 8. 运行与验证

环境要求：JDK 17、Android SDK 36、Build Tools 36、Android Emulator。

```bash
cd android
./gradlew testDebugUnitTest
./gradlew lintDebug
./gradlew assembleDebug
./gradlew connectedDebugAndroidTest
```

模拟器联调前在仓库根目录启动 Agent 服务，Android Debug 包会访问宿主机的 `8000` 端口。

## 9. 后续阶段

- V1.1：训练历史、用户档案、自定义记忆和修改密码。
- V1.2：周报趋势、Vico 原生图表和完整平板交互。
- 后续：Health Connect、通知、图片记录、生物识别和可控离线发送。
