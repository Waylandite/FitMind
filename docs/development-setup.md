# 本地开发环境

使用 Python 3.12、Node 24。Windows 默认的 Python 应用商店入口不可用，默认 Node 18 也低于当前前端依赖要求；本机可使用 Codex 自带运行时，`scripts/dev.ps1` 自动选择其中的 Node。

后端虚拟环境位于 `agent/.venv`，前端依赖位于 `web/node_modules`。`agent/.env` 已从示例创建并生成独立随机鉴权密钥，文件不提交到 Git。数据库连接和模型 API Key 仍需填写；示例数据库密码不代表本机实际配置。

## 启动

在仓库根目录打开两个 PowerShell 窗口：

```powershell
./scripts/dev.ps1 agent
./scripts/dev.ps1 web
```

前端默认 `http://127.0.0.1:5173`，后端 `http://127.0.0.1:8000`。启动不代表数据库或模型已连通。

填写 `agent/.env` 后，在 `agent` 目录执行迁移：

```powershell
./.venv/Scripts/python.exe -m alembic upgrade head
```

仅对确认属于 FitMind 的数据库执行迁移。数据库需事先创建，账号需有相应权限。

## 检查

```powershell
./scripts/dev.ps1 check
```

脚本依次执行后端测试、Ruff、前端测试、ESLint 和生产构建，任一失败立即停止。当前后端测试主要使用隔离的 SQLite 和模型替身，不替代 MySQL 与真实模型验收。CI 配置位于 `.github/workflows/checks.yml`。

## 重新安装

标准 Python 与 Node 环境下：

```powershell
cd agent
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e '.[dev]'
cd ../web
npm ci
```

若虚拟环境没有 pip，可用已有可用 Python 的 pip 为目标环境安装：`python -m pip --python <虚拟环境Python路径> install -e '.[dev]'`。

Windows 完整后端依赖快照已保存在 `agent/requirements-dev-windows.lock.txt`，用于复现本机环境，不直接用于 Linux；其中 Windows 专属依赖需按平台处理。

本机复现安装可在 `agent` 目录运行：

```powershell
./.venv/Scripts/python.exe -m pip install -r requirements-dev-windows.lock.txt
./.venv/Scripts/python.exe -m pip install --no-deps -e '.[dev]'
```

## 当前开发范围

首项修复统一四类业务草稿的回复判定：明确确认才保存，含修正信息的礼貌问句进入重新提取，普通疑问保持草稿。事务与幂等仍需后续独立实现；本次语义修复不代表并发写入问题已解决。

## 2026-10-29 验证结果

- Python 3.12.14、Node 24.22.1，依赖安装完成。
- 后端105项测试通过（含新增23项草稿语义和保存流程测试）；Ruff、pip依赖一致性检查通过。
- 前端4项测试、ESLint和生产构建通过；Vitest升级到5.0.5，Vite锁定解析版本为8.3.5；安装补丁后npm审计为0项漏洞。
- 生产构建仍提示主包超过500KB，后续按页面和功能拆包。
- 本地测试默认使用假的模型密钥，并禁止构建真实模型客户端；不需要真实模型额度。
- 修正刷新令牌重放测试的Cookie设置：先清空Cookie容器再指定令牌，避免同名不同域Cookie导致测试重放了错误的令牌。
- Ruff显式保留原版本的E4/E7/E9/F检查范围，避免新版默认规则变化导致全仓库风格迁移。
- GitHub工作流已添加，尚未在远端触发；MySQL迁移、真实登录保存和模型联调仍待数据库及API Key配置。
