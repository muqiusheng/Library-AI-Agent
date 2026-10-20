# 脚本分类与使用

命令默认从仓库根目录执行。分类后的脚本根据自身位置定位仓库根目录。

| 目录 | 脚本 | 用途 |
|---|---|---|
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

部署与数据操作细节见[部署指南](../docs/deployment/DEPLOYMENT.md)。本次目录整理未执行服务启停、任务注册、备份或恢复操作。
