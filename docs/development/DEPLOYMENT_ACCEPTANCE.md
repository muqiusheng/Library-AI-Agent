# 初始账号与快捷启动验收记录

日期：2026-10-26。

## 变更范围

- 后端仅在用户表为空时初始化超级管理员，本地默认 `admin` / `BookPath@123`。已有账号时跳过，保留原密码、角色、显示名与启用状态；环境变量不是密码重置开关。
- PostgreSQL 事务咨询锁串行化并发初始化，避免多个工作进程重复创建初始账号。
- 家庭配置生成器为新 `.env.home` 生成随机的 16 位管理员初始密码，保留已有配置。
- 新增根目录双击入口 `start.cmd` / `stop.cmd`，自动选择已有家庭配置或本地 Docker 栈，支持指定模式、重建和禁用浏览器；停止不删除数据卷。
- 修正原生开发脚本的后端端口为 `8001`，与 Vite 代理一致；修正本地 Docker 前端 API 地址为构建参数。
- 停止 Git 跟踪历史 SQLite 数据库和运行日志，保留本机文件，不迁移或重置当前 PostgreSQL 与命名卷。

使用步骤和兼容边界见[快捷启动说明](../deployment/QUICK_START.md)，完整配置见[部署指南](../deployment/DEPLOYMENT.md)。

## 已通过的检查

| 检查 | 结果 |
|---|---|
| 初始账号、已有部署兼容、配置与启动器回归 | 23 项通过 |
| 空用户表默认账号 | 可验证密码，角色为超级管理员 |
| 已有学生、管理员、超级管理员与停用账号 | 不新增默认账号，不修改密码、角色和状态 |
| 自定义初始账号、禁用自动创建与无效配置 | 通过 |
| 旧密码在后台修改后重启 | 新密码可登录，初始密码登录失败 |
| 独立 PostgreSQL 空库 Alembic 升级 | 通过 |
| PostgreSQL 四个并发初始化请求 | 仅一个请求创建账号 |
| 真实 API 初始登录、后台重置密码及应用生命周期重启 | 通过 |
| 本地与家庭 Compose 配置校验 | 通过 |
| PowerShell 语法、文档本地链接、Git 空白检查 | 通过 |
| 本次改动 Python 文件的 Ruff | 通过 |
| 前端 Vitest | 3 项通过 |
| 前端 TypeScript 检查及生产构建 | 通过 |

启动器测试在隔离目录中运行，模拟 Docker 命令和 HTTP 外部边界，覆盖含空格的目录、配置只创建一次、家庭配置优先、停止保留数据、随机密码不写入终端和 Compose 失败退出码。真实数据库验收使用随机端口的独立 PostgreSQL 容器与临时数据，结束后删除测试容器；未对现有家庭生产栈执行启停、迁移或账号重置。

## 忘记密码恢复脚本补充验收

新增 `reset-admin-password.cmd`、`scripts/reset-admin-password.ps1` 和 `scripts/reset_admin_password.py`。该入口使用已有镜像中的数据库与安全模块，无需重建镜像；直接在容器交互终端中隐藏输入并确认密码，不将密码写入命令参数、环境文件或终端输出。

- 密码恢复新增 15 项测试通过，连同原初始化与启动器回归共 38 项通过。
- 覆盖只修改指定超级管理员、其他账号不变、角色与停用状态保留、不创建账号、无效长度、确认不一致和不能隐藏输入时取消操作。
- 覆盖自动/显式部署选择、含空格的目录、保留已有配置、容器失败退出码，以及缺少配置时不自动创建或启动部署。
- 在独立 PostgreSQL 与已有后端镜像组成的临时部署中实际运行 PowerShell 恢复脚本，验证两次输入均不显示密码；重置后新密码认证通过、旧密码被拒绝，其他账号不变。测试容器与网络随后删除。
- 未重置现有家庭生产栈中的真实账号，也未重建或重启生产服务。本机 `.env.home` 中的初始密码保持原值，不作为重置后的登录密码。

复核恢复脚本：

```powershell
uv run pytest tests/test_admin_password_reset.py tests/test_password_reset_launcher.py -q
uv run ruff check scripts/reset_admin_password.py tests/test_admin_password_reset.py tests/test_password_reset_launcher.py
```

## 全量检查的现有限制

完整后端测试在新建并迁移的 PostgreSQL 上运行，结果为 53 项通过、11 项失败。其中 9 项依赖预置馆藏，2 项为现有测试接口不一致。验收未预置馆藏。馆藏、标签和推荐集成测试要求已发布馆藏数据，因此空库中的这些检查不能通过。另有两个现有测试与当前接口不一致：`test_general_chat.py` 调用 `is_library_request` 时缺少用户参数，`test_profile_memory.py` 同步调用了异步的 `extract_from_message`。

全仓 Ruff 仍报告 59 个现有问题，涉及本次未修改的接口、推荐服务等文件；本次改动涉及的 Python 文件检查通过。前端和本次回归通过不代表全仓检查全部通过。

复核本次回归：

```powershell
uv run pytest tests/test_admin_bootstrap.py tests/test_admin_seed.py tests/test_config.py tests/test_launcher.py -q
uv run ruff check app/core/config.py app/services/admin_seed.py app/main.py tests/test_admin_bootstrap.py tests/test_launcher.py
```

新机器完整部署与 Windows 真实浏览器自动打开尚需部署者在自己的 Docker Desktop 环境复核；本次没有重建或替换现有生产镜像。
