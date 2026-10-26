# 脚本分类与使用

命令默认从仓库根目录执行。分类后的脚本根据自身位置定位仓库根目录。

| 目录 | 脚本 | 用途 |
|---|---|---|
| 仓库根目录 | `start.cmd`、`stop.cmd` | Windows 双击启停，默认自动识别家庭或本地 Docker 栈 |
| 仓库根目录 | `reset-admin-password.cmd` | 双击或终端重置指定超级管理员密码，保留其他数据 |
| `scripts/` | `reset-admin-password.ps1`、`reset_admin_password.py` | 识别部署栈，在现有容器中隐藏输入并重置密码，无需重建镜像 |
| `scripts/` | `launcher.ps1` | 检查 Docker、补齐缺少的配置、等待服务就绪并打开浏览器 |
| `dev/` | `start.ps1`、`stop.ps1` | 本地开发进程启停 |
| `dev/` | `verify.ps1` | 后端 Pytest、Ruff，以及前端测试、类型检查和构建 |
| `dev/` | `reset-demo.ps1` | 重置演示活动数据 |
| `home/` | `init-home-env.ps1` | 从模板初始化生产环境变量 |
| `home/` | `home-start.ps1`、`home-stop.ps1` | 家庭服务器启停 |
| `home/` | `home-health.ps1`、`home-smoke-test.ps1` | 健康与基础接口检查 |
| `home/` | `home-backup.ps1` | 数据库和上传文件备份 |
| `home/` | `home-restore.ps1`、`home-restore-drill.ps1` | 生产恢复与恢复演练 |
| `home/` | `home-seed-admin.ps1` | 初始化管理员 |
| `home/` | `home-release-check.ps1` | 现有家庭栈发布检查 |
| `home/` | `install-home-tasks.ps1`、`uninstall-home-tasks.ps1` | 注册和移除 Windows 运维定时任务 |
| `network/` | `funnel-start.ps1`、`funnel-stop.ps1`、`funnel-check.ps1` | Tailscale Funnel 入口管理 |

常用命令：

```powershell
.\scripts\dev\verify.ps1
.\scripts\home\home-start.ps1 -SkipFunnel
.\scripts\network\funnel-check.ps1
```

`verify.ps1` 原有的退出码检查尚不完整，需核对各项结果；不能只凭末尾的成功提示判断全部通过。也可按[协作指南](../CONTRIBUTING.md)逐条运行验证命令。发布检查中的固定馆藏数量和版本标识等限制见[迭代指南](../docs/development/ITERATION.md)。

为兼容已安装的 Windows 定时任务，`scripts/` 根目录保留 `home-start.ps1`、`home-health.ps1`、`home-backup.ps1` 三个转发入口，参数与退出码传递给 `home/` 下的实现。新安装任务直接引用 `home/` 中的脚本，无需为本次整理重新注册已有任务。

双击入口的参数、初始账号和已有部署兼容规则见[快捷启动说明](../docs/deployment/QUICK_START.md)。`start.cmd -Rebuild` 用于更新镜像，`-Mode Local` / `-Mode Home` 指定部署栈，`-NoBrowser` 禁用自动打开网页。`stop.cmd` 只停止容器并保留持久化数据，不修改已有 Funnel 配置。原生开发仍使用 `dev/start.ps1`（后端 `8001`，与 Vite 代理一致）与 `dev/stop.ps1`。

`home/init-home-env.ps1` 在新生成的 `.env.home` 中写入随机管理员初始密码；已有配置不会被覆盖。部署与数据操作细节见[部署指南](../docs/deployment/DEPLOYMENT.md)。

忘记密码时先启动系统，再运行 `.\reset-admin-password.cmd`；默认账号为 `admin`，支持 `-Mode Home` / `-Mode Local` 和 `-StudentNo 用户名`。密码输入两次且不会显示，详细提示及兼容规则见[密码恢复步骤](../docs/deployment/QUICK_START.md#忘记超级管理员密码)。
