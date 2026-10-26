# 双击启动与初始账号

## 第一次在 Windows 上部署

1. 安装并启动 Docker Desktop，下载或克隆本项目。
2. 在项目根目录双击 `start.cmd`，无需先打开 PowerShell 或安装 Python、Node.js。
3. 首次运行会自动创建缺少的 `.env`，下载并构建镜像。等待窗口显示 `Ready`，浏览器会自动打开 <http://localhost:4173>。
4. 全新空数据库使用以下超级管理员账号登录：

| 项目 | 本地初始值 |
|---|---|
| 用户名（登录页的学号） | `admin` |
| 密码 | `BookPath@123` |

登录后进入管理后台的用户管理，找到自己的账号，通过“重置密码”设置新密码。新密码为 8～16 位。不要在公开部署中继续使用本地默认密码。

首次部署没有学生、馆藏、推荐和学习路径数据。导入馆藏、生成标签和索引后才能体验完整推荐，步骤见[部署指南 2.7](./DEPLOYMENT.md#27-导入示例馆藏)。快捷启动不会自动导入业务或演示数据。

如果想在首次启动前自定账号，先复制 `.env.example` 为 `.env`，修改：

```dotenv
BOOTSTRAP_ADMIN_ENABLED=true
BOOTSTRAP_ADMIN_STUDENT_NO=admin
BOOTSTRAP_ADMIN_PASSWORD=你的8至16位密码
```

然后双击 `start.cmd`。用户名去除首尾空格后应为 1～64 个字符。自动初始化仅在用户表为空时执行；设置 `BOOTSTRAP_ADMIN_ENABLED=false` 可禁用它。

## 日常使用与更新

- 启动：双击根目录 `start.cmd`。
- 停止：双击根目录 `stop.cmd`，仅停止对应 Compose 栈，保留容器、账号、馆藏、索引和数据卷。
- 更新代码后：运行 `git pull`，再执行 `start.cmd -Rebuild`，让代码变更进入镜像。普通双击复用已有镜像；首次缺少镜像时 Compose 会自动构建。
- 首次下载或构建失败：根据窗口报错检查 Docker Desktop 和网络，再次双击重试；失败窗口会保留错误信息。

不需要浏览器自动打开，或需要指定部署方式时，可在终端执行：

```powershell
.\start.cmd -NoBrowser
.\start.cmd -Mode Local
.\start.cmd -Mode Home
.\stop.cmd -Mode Home
```

`Local` 使用 `docker-compose.yml`，页面端口为 `4173`；`Home` 使用 `docker-compose.home.yml`，页面端口为 `8180`。从其他工作目录调用也会定位到项目根目录。Linux/macOS 用户继续使用[部署指南](./DEPLOYMENT.md)中的 Docker Compose 命令。

## 已有部署如何兼容

默认 `Auto` 模式在发现 `.env.home` 时选择家庭栈，否则选择本地栈。两种配置同时存在时仍优先家庭栈；如需另一套，请显式传入 `-Mode`。两套栈拥有各自的账号和数据，不能将切换模式当作重置密码的方法。

启动器保留已有 `.env` / `.env.home`，复用原 Compose 项目名称和持久化卷。用户表只要已有任意账号，就跳过自动初始化：不添加默认超级管理员、不改密码、不改角色、不启用已停用账号。重启、重新构建、修改 `BOOTSTRAP_ADMIN_*` 均不会重置现有账号。原有脚本与定时任务仍可继续使用。

家庭部署首次运行 `start.cmd -Mode Home` 时，如果 `.env.home` 不存在，会自动生成数据库密码、JWT 密钥和随机的 16 位管理员初始密码。用户名为 `admin`，密码查看本机 `.env.home` 中的 `BOOTSTRAP_ADMIN_PASSWORD`；启动窗口不会显示密码。已有配置不会被重新生成。

快捷入口管理容器，不新增或修改 Tailscale Funnel 配置。需要启用公网或撤销已有公网入口时，继续使用原来的 `scripts/home/home-start.ps1` / `home-stop.ps1` 和网络脚本；见[家庭服务器部署](./DEPLOYMENT.md#7-家庭服务器生产部署)。

## 为什么提示账号已经存在

`seed-admin` 的 `already exists` 表示账号已存在，刚刚输入的密码**没有覆盖原密码**。自动初始化后再次运行它也会得到这个结果。请使用原密码登录；能登录的超级管理员可在用户管理中重置密码。

全新下载代码与全新数据库是两件事。同一台电脑上的旧 Docker 命名卷、已有 PostgreSQL 连接地址或恢复的备份，都可能包含旧账号；同一台电脑再次克隆项目也会复用同名 Compose 卷。快捷启动会保留这些数据。需要独立部署时，请使用独立数据库或独立 Docker 环境，并核对端口和卷，不能复制别人的 `.env`、数据库目录或备份。

当前版本使用 PostgreSQL；历史 `library_data.db` 不参与运行。仓库已停止跟踪该 SQLite 文件和 `backend.log`，本次修改保留当前工作目录中的文件。其他旧检出在拉取更新前，如需保留这些历史文件，可自行复制到被忽略的 `data/legacy/` 目录；Git 仍可能在更新时移除以前跟踪的副本。历史提交中的文件没有被改写。

日常启停不要删除数据卷。只有主动执行部署指南中的完全重置操作，才会清除账号和业务数据；这不属于快捷启动流程。
