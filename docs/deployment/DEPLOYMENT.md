# 书途智启本地部署指南

本文面向第一次接触 Python、Vue 或 Docker 的用户，目标是让你在自己的电脑上完整启动书途智启。推荐优先使用“方式一：Docker Compose”，因为它不要求你单独安装 Python、Node.js 和 PostgreSQL。

Windows 用户可先阅读[双击启动与初始账号](./QUICK_START.md)：安装 Docker Desktop 后双击根目录 `start.cmd`，停止时双击 `stop.cmd`。已有家庭配置会自动复用，首次缺少配置时才生成。

目录职责与旧路径对照见 [项目结构说明](../STRUCTURE.md)，其他指南见 [文档导航](../README.md)。本文命令仍从仓库根目录执行。

## 1. 部署后会启动什么

Docker 本地栈包含三个服务：

| 服务 | 宿主机端口 | 用途 |
|---|---:|---|
| `frontend` | `4173` | Vue 前端页面 |
| `backend` | `8000` | FastAPI 后端与 API 文档 |
| `postgres` | `5432` | PostgreSQL 数据库 |

Chroma 以内嵌方式运行在后端中，数据保存在 Docker 命名卷 `chroma_data`；PostgreSQL 数据保存在 `postgres_data`。正常停止或重建容器不会删除这些数据。

## 2. 方式一：使用 Docker Compose（新手推荐）

### 2.1 安装必要软件

Windows 用户需要安装：

1. [Git](https://git-scm.com/downloads)
2. [Docker Desktop](https://www.docker.com/products/docker-desktop/)

安装 Docker Desktop 后请启动它，等待左下角或状态页显示 Docker Engine 正常运行。Windows 上通常需要启用 WSL 2；Docker Desktop 安装程序会提供引导。

macOS 或 Linux 用户同样需要 Git、Docker Engine 和 Docker Compose v2。后文的 `Copy-Item`、`Set-Location` 是 PowerShell 命令；在 Bash/Zsh 中分别使用 `cp`、`cd`。

打开 PowerShell，确认安装成功：

```powershell
git --version
docker --version
docker compose version
```

三个命令都应显示版本号。如果 `docker` 命令存在但提示无法连接 daemon，通常是 Docker Desktop 尚未启动完成。

### 2.2 下载项目

将下面的占位地址替换成仓库页面中绿色 **Code** 按钮提供的 HTTPS 地址：

```powershell
git clone <你的 GitHub 仓库地址>
Set-Location Library-AI-Agent
```

如果仓库目录名称不同，请将第二行改为实际目录名称。后续命令都必须在能看到 `docker-compose.yml` 的项目根目录执行。

### 2.3 创建本地配置

复制公开的配置模板：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS/Linux：

```bash
[ -f .env ] || cp .env.example .env
```

默认配置可以用于个人电脑上的本地开发。建议至少修改 `.env` 中的 `JWT_SECRET`，换成一个随机且不少于 32 个字符的值。例如可在 PowerShell 中生成：

```powershell
$bytes = New-Object byte[] 48
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

把输出复制到 `.env` 的 `JWT_SECRET=` 后面。不要把生成后的 `.env` 提交到 Git。

`DEEPSEEK_API_KEY` 可以暂时留空。系统仍能以降级模式完成基础检索推荐；AI 标签等明确依赖模型的功能会不可用或降级。

### 2.4 构建并启动系统

```powershell
docker compose up -d --build
```

第一次执行需要下载 PostgreSQL、Python、Node.js 等镜像并安装依赖，耗时取决于网络速度。命令结束后查看状态：

```powershell
docker compose ps
```

正常情况下，三个服务都应为 `Up` 或 `running`，PostgreSQL 会显示 `healthy`。后端容器启动时会自动执行：

```text
alembic upgrade head
```

因此新用户无需手工创建数据库表。随后应用仅在用户表为空时自动创建初始超级管理员；已有任意账号时跳过初始化。

### 2.5 验证服务

浏览器依次打开：

- 前端：<http://localhost:4173>
- 健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/docs>

也可在 PowerShell 中检查后端：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

如果页面打不开，先查看日志：

```powershell
docker compose logs --tail 100
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
```

### 2.6 初始超级管理员

全新本地空数据库首次启动后即可使用以下账号登录，无需手动执行创建命令：

| 项目 | 默认值 |
|---|---|
| 用户名（学号） | `admin` |
| 初始密码 | `BookPath@123` |

登录后进入管理后台的用户管理，找到自己的账号并重置密码。首次启动前可修改 `.env` 中的 `BOOTSTRAP_ADMIN_STUDENT_NO` 和 `BOOTSTRAP_ADMIN_PASSWORD` 自定账号，密码为 8～16 位；`BOOTSTRAP_ADMIN_ENABLED=false` 可禁用自动创建。修改这些变量不会重置已有账号。

**已有部署继续使用原账号与原密码。** 用户表存在任意账号时，自动初始化不创建账号、不覆盖密码、不改角色或账号状态。旧 Docker 卷、已有 PostgreSQL 和恢复的备份均会被保留；重新克隆代码不等于获得空数据库。

如首次启动前已禁用自动初始化，可以继续手动创建管理员：

```powershell
$env:BOOKPATH_ADMIN_PASSWORD = Read-Host "请输入管理员密码（至少8位）"
docker compose exec -e BOOKPATH_ADMIN_PASSWORD backend .venv/bin/python -m app.cli seed-admin --student-no admin --display-name "系统管理员"
Remove-Item Env:BOOKPATH_ADMIN_PASSWORD
```

`admin admin: created` 表示新账号创建成功，此时使用刚输入的密码。`already exists` 表示原账号已存在，**本次输入的密码未生效**，应使用原密码；该命令不用于重置密码。自动初始化已创建默认账号时，再次运行该命令也会提示已存在。手动命令保留原有兼容行为：同名普通管理员会升级为超级管理员，原密码仍保留；自动初始化不会进行这种升级。

> 容器内 Python 路径为 `.venv/bin/python`，即使宿主机是 Windows 也使用正斜杠。

### 2.7 导入示例馆藏

新数据库只有表结构，没有可推荐的图书。仓库提供了示例馆藏 Excel，先复制进后端容器：

```powershell
docker compose cp "resources/knowledge_base/books/ShiepbookInfo.xlsx" backend:/tmp/library.xlsx
```

然后依次执行导入、规则标签和向量索引构建：

```powershell
docker compose exec backend .venv/bin/python -m app.cli import-library /tmp/library.xlsx
docker compose exec backend .venv/bin/python -m app.cli tag-books
docker compose exec backend .venv/bin/python -m app.cli build-index
```

请等待每条命令结束后再执行下一条。数据量较大时，导入和索引构建可能需要数分钟，并占用较多内存。相同 Excel 重复导入时，系统会利用 SHA-256 做幂等保护。

完成后即可用普通学生账号体验完整推荐。你可以在页面注册，也可以创建两个演示学生：

```powershell
$env:BOOKPATH_DEMO_PASSWORD = Read-Host "请输入 8 至 16 位演示密码"
docker compose exec -e BOOKPATH_DEMO_PASSWORD backend .venv/bin/python -m app.cli seed-demo
Remove-Item Env:BOOKPATH_DEMO_PASSWORD
```

该命令会创建 `demo_java` 和 `demo_data`。如果账号已存在，则保留原账号数据。

### 2.8 配置 DeepSeek（可选）

编辑项目根目录的 `.env`：

```dotenv
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_CHAT_MODEL=deepseek-v4-flash
DEEPSEEK_REASONING_MODEL=deepseek-v4-pro
```

模型名称必须是你的 API 账户实际可用的模型。如果服务商调整了模型名称，请以服务商控制台为准。修改 `.env` 后重建后端容器使配置生效：

```powershell
docker compose up -d --build backend
```

不要把 API Key 写进 README、截图、Issue、提交记录或前端源码。Key 只能放在后端环境变量中。

### 2.9 日常启动、停止和更新

Windows 可双击根目录 `start.cmd` / `stop.cmd`；更新代码后执行 `start.cmd -Rebuild`。启动器复用原配置和卷，停止入口仅执行对应栈的 `docker compose stop`。两种配置同时存在时，默认优先家庭栈，需本地栈时使用 `start.cmd -Mode Local`。更多参数见[快捷启动说明](./QUICK_START.md)。

启动已有容器：

```powershell
docker compose up -d
```

停止并移除容器，但保留数据库和向量数据：

```powershell
docker compose down
```

查看实时日志，按 `Ctrl+C` 退出日志查看（不会停止容器）：

```powershell
docker compose logs -f
```

拉取新代码并重新构建：

```powershell
git pull
docker compose up -d --build
```

后端启动时会自动升级数据库结构。

### 2.10 完全重置本地数据

下面的命令会永久删除 Docker 本地栈的 PostgreSQL 与 Chroma 命名卷，所有账号、馆藏、推荐记录和索引都会丢失：

```powershell
docker compose down -v
```

仅在确认不需要现有数据时执行。再次 `docker compose up -d --build` 后会创建初始超级管理员（除非禁用了自动初始化），其余业务数据为空，需要重新导入馆藏。日常快捷启动不会执行此重置操作。

## 3. 方式二：原生开发环境

此方式适合准备修改代码的开发者。PostgreSQL 仍建议使用 Docker，只在宿主机运行 Python 后端和 Vite 前端。

### 3.1 环境要求

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20 或更高版本（推荐当前 LTS）
- npm（随 Node.js 安装）
- Docker Desktop（用于 PostgreSQL）或一个自行安装的 PostgreSQL 16

确认版本：

```powershell
python --version
uv --version
node --version
npm --version
docker compose version
```

### 3.2 安装后端与前端依赖

在项目根目录执行：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv sync
Set-Location frontend
npm ci
Set-Location ..
```

`uv sync` 会根据 `pyproject.toml` 和 `uv.lock` 创建 `.venv` 并安装锁定依赖；`npm ci` 会根据 `package-lock.json` 安装前端依赖。

### 3.3 只启动 PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps postgres
```

`.env.example` 的默认 `DATABASE_URL` 正好连接到本机 `localhost:5432` 的这个数据库。如果你的电脑已有 PostgreSQL 占用 `5432`，请停止冲突服务，或同时修改 Compose 端口映射和 `.env` 中的连接地址。

执行数据库迁移：

```powershell
uv run alembic upgrade head
```

### 3.4 启动后端

打开第一个 PowerShell 窗口，在项目根目录执行：

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

原生开发后端使用 `8001`，因为 `frontend/vite.config.js` 会把 `/api` 代理到 `http://127.0.0.1:8001`。健康检查地址是 <http://127.0.0.1:8001/health>，API 文档是 <http://127.0.0.1:8001/docs>。

### 3.5 启动前端

保持后端窗口运行，打开第二个 PowerShell 窗口：

```powershell
Set-Location <项目目录>\frontend
npm run dev
```

打开 <http://localhost:4173>。修改 Vue 或 TypeScript 文件后，Vite 会自动刷新；修改 Python 文件后，Uvicorn 的 `--reload` 会自动重启后端。

### 3.6 原生环境初始化账号与馆藏

原生后端同样在启动时自动检查用户表：空库创建 `.env` 中 `BOOTSTRAP_ADMIN_*` 指定的超级管理员，未配置时为 `admin` / `BookPath@123`；已有账号时保留原密码。修改密码使用管理后台的用户管理。若事先禁用自动初始化，可按 2.6 的手动方式创建，将命令前缀替换为 `uv run python -m app.cli seed-admin`。

在第三个 PowerShell 窗口、项目根目录执行以下馆藏命令。

导入仓库内示例馆藏：

```powershell
uv run python -m app.cli import-library "resources\knowledge_base\books\ShiepbookInfo.xlsx"
uv run python -m app.cli tag-books
uv run python -m app.cli build-index
```

创建演示账号：

```powershell
$env:BOOKPATH_DEMO_PASSWORD = Read-Host "请输入 8 至 16 位演示密码"
uv run python -m app.cli seed-demo
Remove-Item Env:BOOKPATH_DEMO_PASSWORD
```

### 3.7 停止原生开发环境

在后端和前端终端中分别按 `Ctrl+C`，然后停止 PostgreSQL：

```powershell
docker compose stop postgres
```

## 4. 配置项说明

### 4.1 应用与跨域

| 变量 | 开发默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | 可选 `development`、`test`、`production` |
| `APP_HOST` | `0.0.0.0` | 后端监听地址 |
| `APP_PORT` | `8000` | 应用端口配置；实际命令行端口可覆盖它 |
| `APP_FRONTEND_ORIGINS` | 本地前端地址数组 | 允许跨域访问 API 的明确来源，不能使用 `*` |

### 4.2 数据库与文件

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL 连接串 |
| `DATABASE_POOL_SIZE` | 常驻数据库连接池大小 |
| `DATABASE_MAX_OVERFLOW` | 连接池临时溢出上限 |
| `CHROMA_PERSIST_DIRECTORY` | Chroma 持久化目录 |
| `CHROMA_COLLECTION_PREFIX` | Chroma 集合名称前缀 |
| `EMBEDDING_MODEL` | 嵌入模型标识 |
| `IMPORT_UPLOAD_DIRECTORY` | 管理端上传文件的临时目录 |
| `IMPORT_MAX_BYTES` | 单个上传文件最大字节数，默认 64 MiB |

### 4.3 认证与注册

| 变量 | 说明 |
|---|---|
| `BOOTSTRAP_ADMIN_ENABLED` | 默认 `true`；仅在用户表为空时自动创建初始超级管理员 |
| `BOOTSTRAP_ADMIN_STUDENT_NO` | 默认 `admin`；初始用户名（学号），去除首尾空格后 1～64 字符 |
| `BOOTSTRAP_ADMIN_PASSWORD` | 本地默认 `BookPath@123`；8～16 位，生产生成器使用随机值；不重置已有密码 |
| `JWT_SECRET` | JWT 签名密钥；生产环境必须使用随机值 |
| `JWT_ALGORITHM` | 默认 `HS256` |
| `JWT_ACCESS_TOKEN_MINUTES` | Access Token 有效分钟数 |
| `REGISTRATION_ENABLED` | 是否开放注册 |
| `REGISTRATION_INVITE_CODE` | 注册邀请码；生产开放注册时建议设置 |
| `MAX_ACCOUNT_COUNT` | 系统最大账号数量 |

### 4.4 限流与模型

| 变量 | 说明 |
|---|---|
| `RATE_LIMIT_ENABLED` | 是否启用接口限流；生产环境必须为 `true` |
| `RATE_LIMIT_REGISTER_PER_MINUTE` | 每分钟注册请求限制 |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | 每分钟登录请求限制 |
| `RATE_LIMIT_AI_PER_MINUTE` | 每分钟 AI 请求限制 |
| `RATE_LIMIT_BATCH_TAG_PER_MINUTE` | 每分钟批量标签请求限制 |
| `LLM_PROVIDER` | 当前默认 `deepseek` |
| `DEEPSEEK_BASE_URL` | OpenAI 兼容 API 基础地址 |
| `DEEPSEEK_API_KEY` | 服务端 API Key，可留空进入降级模式 |
| `DEEPSEEK_CHAT_MODEL` | 对话模型名称 |
| `DEEPSEEK_REASONING_MODEL` | 推理模型名称 |

## 5. 验证安装与运行测试

### 5.1 Docker 运行状态

```powershell
docker compose ps
docker compose exec backend .venv/bin/alembic current
Invoke-RestMethod http://localhost:8000/health
```

### 5.2 完整开发检查

本次初始账号与快捷启动的独立回归不需要正在运行的数据库，可单独执行：

```powershell
uv run pytest tests/test_admin_bootstrap.py tests/test_admin_seed.py tests/test_config.py tests/test_launcher.py -q
```

`test_launcher.py` 在 Windows 上执行，在其他系统跳过。完整集成测试还需要可连接的 PostgreSQL、迁移后的表结构和已导入发布的馆藏；只迁移空库不足以通过馆藏相关测试。本次实际验收、已有旧测试接口问题及全仓静态检查限制见[部署变更验收记录](../development/DEPLOYMENT_ACCEPTANCE.md)。

已按原生开发方式安装依赖后，可在 Windows PowerShell 执行：

```powershell
.\scripts\dev\verify.ps1
```

也可以分别运行：

```powershell
uv run pytest tests -q
uv run ruff check app tests
Set-Location frontend
npm run test
npm run build
Set-Location ..
```

`npm run build` 内部会先执行 TypeScript 类型检查，再进行 Vite 生产构建。

## 6. 常见问题排查

### 6.1 `docker` 无法连接或一直启动失败

- 确认 Docker Desktop 已启动并完成初始化。
- Windows 用户确认 WSL 2 可用，重启 Docker Desktop 后再试。
- 执行 `docker info`；如果该命令失败，问题发生在 Docker 环境而不是本项目。

### 6.2 端口已被占用

常见报错包含 `port is already allocated` 或 `address already in use`。查看 Windows 端口占用：

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -In 4173,8000,8001,5432
```

停止占用端口的旧进程或旧容器：

```powershell
docker compose down
docker ps
```

如需改端口，请修改 `docker-compose.yml` 左侧的宿主端口，并同步修改前端 API 地址或 CORS 来源。例如将前端映射改为 `4174:5173` 后，应访问 `http://localhost:4174`，并将该来源加入 `APP_FRONTEND_ORIGINS`。

### 6.3 后端健康检查显示 `degraded`

通常表示 PostgreSQL 或 Chroma 不可用。依次检查：

```powershell
docker compose ps
docker compose logs --tail 100 postgres
docker compose logs --tail 100 backend
```

确认 `.env` 格式没有被破坏，并确认 Docker 有足够内存。项目完整导入与索引建议给 Docker Desktop 分配至少 4 GB 内存。

### 6.4 页面能打开，但注册或登录请求失败

- 查看浏览器开发者工具的 Network 面板和后端日志。
- Docker 模式确认 API 为 `http://localhost:8000/api/v1`。
- 原生模式确认 Uvicorn 运行在 `8001`，与 Vite 代理一致。
- 若修改过前端端口或域名，把新来源加入 `APP_FRONTEND_ORIGINS`。
- 生产模式下注册可能默认关闭，需要管理员配置注册开关与邀请码。

### 6.5 能登录，但没有推荐图书

空数据库不会自动包含馆藏。确认已经执行：

```powershell
docker compose exec backend .venv/bin/python -m app.cli import-library /tmp/library.xlsx
docker compose exec backend .venv/bin/python -m app.cli tag-books
docker compose exec backend .venv/bin/python -m app.cli build-index
```

若第一条提示文件不存在，请先重新执行 `docker compose cp`。导入命令默认发布数据版本；使用 `--draft` 导入的版本不会直接成为推荐数据源。

### 6.6 未配置 API Key

这不是启动失败。系统允许 `DEEPSEEK_API_KEY` 为空，并使用降级路径。需要 AI 批量标签或更完整的自然语言能力时再配置有效 Key，并重建后端。

### 6.7 修改 `.env` 后没有生效

容器环境变量在创建容器时读取。重新创建相关服务：

```powershell
docker compose up -d --force-recreate backend
```

如果前端 API 地址发生变化，因为它在前端构建时写入，还需要重新构建前端：

```powershell
docker compose up -d --build frontend
```

### 6.8 管理员提示 `already exists` 或初始密码无法登录

- `already exists` 表示密码没有被覆盖。使用原密码，或让已登录的超级管理员从用户管理重置密码。
- 初始凭据仅用于用户表为空的首次启动；用户表有任何账号时都会跳过。检查是否连接到已有 PostgreSQL、旧卷或恢复的备份。
- 家庭生产配置生成器使用随机密码，查看本机 `.env.home` 的 `BOOTSTRAP_ADMIN_PASSWORD`，不要使用本地默认密码。
- 不要为了登录而删除数据卷或覆盖 `.env`；`BOOTSTRAP_ADMIN_*` 不是密码重置开关。
- 双击启动发现 `.env.home` 会选择家庭栈。若实际要访问本地开发栈，显式使用 `start.cmd -Mode Local`。

如果已经忘记原超级管理员密码，先启动系统，再在 Windows 项目根目录执行：

```powershell
.\reset-admin-password.cmd
```

按提示隐藏输入并确认 8～16 位新密码，默认处理 `admin`；指定其他账号或部署栈可用 `.\reset-admin-password.cmd -Mode Home -StudentNo admin`。也可直接双击该文件。无需重建镜像，保留其他账号和业务数据，失败或取消时不会创建账号或重置环境。完整说明见[密码恢复步骤](./QUICK_START.md#忘记超级管理员密码)。

### 6.9 依赖下载慢或失败

- 确认浏览器可以访问 Docker Hub、GitHub 和包仓库。
- 重新执行相同构建命令，Docker 会复用已经完成的缓存层。
- 查看具体失败服务：`docker compose build backend` 或 `docker compose build frontend`。
- 网络受限环境需要根据所在网络配置 Docker 镜像加速或代理。

## 7. 家庭服务器生产部署

仓库提供 `docker-compose.home.yml`，使用 Nginx 同源转发前端与 `/api`，PostgreSQL 和 FastAPI 不映射到宿主机，只暴露 `127.0.0.1:8180`。它比开发 Compose 更接近长期运行环境。

### 7.1 生成生产配置

Windows PowerShell：

```powershell
.\scripts\home\init-home-env.ps1
```

脚本根据 `.env.home.example` 生成 `.env.home`，自动创建随机 PostgreSQL 密码、JWT 密钥和 16 位超级管理员初始密码。为了防止误覆盖，已有 `.env.home` 时脚本会停止。

检查 `.env.home`，按需要配置：

- `APP_FRONTEND_ORIGINS`：实际访问来源。
- `REGISTRATION_ENABLED` 与 `REGISTRATION_INVITE_CODE`：是否开放邀请注册。
- `MAX_ACCOUNT_COUNT`：账号数量上限。
- `DEEPSEEK_API_KEY` 与模型名称：可选模型服务。

全新空库的用户名为 `admin`，密码查看本机 `.env.home` 的 `BOOTSTRAP_ADMIN_PASSWORD`；已有账号仍使用原密码。旧 `.env.home` 无需补写这些新变量，已有数据会使初始化自动跳过。不要提交 `.env.home`。

### 7.2 启动家庭服务器栈

Windows 可执行 `start.cmd -Mode Home`，缺少 `.env.home` 时会自动生成；已有 `.env.home` 时直接双击 `start.cmd` 即可复用家庭栈。快捷入口不会修改 Funnel 配置；公网启停仍沿用 7.3 的原脚本。

通用 Docker 命令：

```powershell
docker compose -f docker-compose.home.yml up -d --build
docker compose -f docker-compose.home.yml ps
```

浏览器在服务器本机打开 <http://127.0.0.1:8180>。健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8180/health
```

项目还提供 `home-start.ps1`、`home-stop.ps1`、备份、恢复演练和发布检查脚本。这些脚本中的 Docker Desktop 与 Tailscale 路径带有原开发机器默认值，换电脑后应通过脚本参数传入真实路径，或直接使用上面的通用 `docker compose` 命令。

### 7.3 Windows 开机后的启动与关机前的关闭流程

BookPath 的自动启动定时任务不是运行项目的必要条件。未安装自动任务或已将任务删除时，每次 Windows 开机后手动运行启动脚本即可。项目支持“仅限本机访问”和“通过 Tailscale Funnel 开放公网”两种启动模式，不要同时启动另一套 `docker-compose.yml` 开发栈。

#### 启动前准备

1. 登录 Windows，确认网络连接正常。
2. 打开 VS Code，并在项目中打开 PowerShell 终端；也可以使用独立的普通 PowerShell，不需要管理员权限。
3. 进入项目根目录：

```powershell
Set-Location "D:\data\Java\lgh\vs code\Library-AI-Agent"
```

如果项目克隆在其他位置，请将路径替换为自己的项目根目录；判断标准是该目录中可以看到 `docker-compose.home.yml` 和 `scripts` 文件夹。

启动脚本会检查 Docker Engine。如果 Docker Desktop 尚未运行，脚本会尝试自动启动 Docker Desktop，并等待最多约 3 分钟。不要在看到第一次 Docker 连接失败时立刻重复运行脚本，应等待最终的成功或错误提示。

#### 模式一：仅限本机访问

只准备在当前电脑上使用时，添加 `-SkipFunnel`：

```powershell
.\scripts\home\home-start.ps1 -SkipFunnel
```

该命令会启动 PostgreSQL、FastAPI 后端和 Nginx 前端，但不会创建公网入口。成功时显示：

```text
BookPath is healthy at http://127.0.0.1:8180
```

浏览器访问：

```text
http://127.0.0.1:8180
```

执行健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8180/health
```

返回内容中的 `data.status` 应为 `ok`，数据库和向量库状态也应为 `ok`。

#### 模式二：通过 Tailscale Funnel 开放公网

公网模式要求电脑已经安装并登录 Tailscale，并且当前 Tailnet 已允许 Funnel。启动时不要添加 `-SkipFunnel`：

```powershell
.\scripts\home\home-start.ps1
```

脚本会先启动并检查本地服务，再把 `http://127.0.0.1:8180` 映射到 Tailscale 提供的 HTTPS 公网地址。查看公网状态和地址：

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" funnel status
```

公网地址通常采用以下格式：

```text
https://<设备名称>.<Tailnet 标识>.ts.net
```

本项目原部署机器当前的地址示例为：

```text
https://bookpath-home.tail949c1c.ts.net
```

换电脑、重新登录 Tailscale 或更换 Tailnet 后，域名可能变化，必须以 `tailscale funnel status` 的实际输出为准。建议关闭手机 Wi-Fi，使用手机流量访问公网地址，检查首页、登录和主要接口，确认服务确实可从外网访问。

> Funnel 地址可以被互联网访问。开启前应确认生产密钥已经生成、管理员使用强密码、注册受到邀请码或注册开关保护，并且没有公开不应暴露的数据。

#### 查看容器运行状态

本地和公网模式都可以执行：

```powershell
docker compose -f docker-compose.home.yml ps
```

正常情况下应看到以下三个服务处于运行或健康状态：

- `postgres`：PostgreSQL 数据库。
- `backend`：FastAPI 后端。
- `gateway`：Nginx 前端和 API 反向代理。

需要排查启动问题时查看日志：

```powershell
docker compose -f docker-compose.home.yml logs --tail 100
```

持续查看日志：

```powershell
docker compose -f docker-compose.home.yml logs -f
```

按 `Ctrl+C` 只会退出日志查看，不会关闭正在运行的项目。

#### 关闭公网并安全停止整个项目

无论使用本地模式还是公网模式，关机前都使用同一个关闭命令：

```powershell
Set-Location "D:\data\Java\lgh\vs code\Library-AI-Agent"
.\scripts\home\home-stop.ps1
```

如果 Funnel 已开启，脚本会先撤销公网配置；如果没有开启 Funnel，则直接跳过。随后脚本会关闭网关、后端和 PostgreSQL。成功时显示：

```text
BookPath containers stopped. Persistent volumes were preserved.
```

确认 Funnel 已撤销：

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" funnel status --json
```

没有公网配置时应返回：

```json
{}
```

确认项目容器已经关闭：

```powershell
docker compose -f docker-compose.home.yml ps
```

输出中不应再有运行中的项目服务。此时可以关闭 Docker Desktop，然后正常关闭 Windows。

`home-stop.ps1` 不会删除持久化数据，以下内容会在下次启动时恢复：

- PostgreSQL 中的账号、馆藏、推荐和其他业务数据。
- Chroma 向量索引。
- 管理端上传文件。
- Docker 命名卷中的其他持久化内容。

日常关闭时不要执行 `docker compose down -v`，因为 `-v` 会永久删除数据卷。虽然直接关闭电脑通常不会主动删除数据，但建议先执行 `home-stop.ps1`，让 PostgreSQL 和其他服务正常退出。

#### 日常命令速查

仅限本机启动：

```powershell
Set-Location "D:\data\Java\lgh\vs code\Library-AI-Agent"
.\scripts\home\home-start.ps1 -SkipFunnel
```

公网启动：

```powershell
Set-Location "D:\data\Java\lgh\vs code\Library-AI-Agent"
.\scripts\home\home-start.ps1
```

关闭公网并停止整个项目：

```powershell
Set-Location "D:\data\Java\lgh\vs code\Library-AI-Agent"
.\scripts\home\home-stop.ps1
```

两种模式的区别只有是否添加 `-SkipFunnel`：添加时仅允许本机通过 `127.0.0.1:8180` 访问；不添加时会额外建立 Tailscale HTTPS 公网入口。

### 7.4 生产安全检查

当 `APP_ENV=production` 时，后端会拒绝以下危险配置：

- 默认 `JWT_SECRET`。
- 默认或占位 PostgreSQL 密码。
- `RATE_LIMIT_ENABLED=false`。

对公网开放前还应完成：

1. 使用 HTTPS 反向代理，不直接暴露开发服务器。
2. 只开放必要端口，不对公网开放 PostgreSQL `5432`。
3. 限制管理员账号数量，使用强密码并妥善保存；全新生产部署使用生成的随机初始密码，首次登录后在用户管理重置密码。
4. 关闭自由注册，或启用足够长的注册邀请码。
5. 定期备份 PostgreSQL、Chroma 和上传目录，并实际执行恢复演练。
6. 配置日志轮转、磁盘空间和容器健康监控。
7. 确认馆藏数据、用户数据和第三方模型调用符合授权与隐私要求。
8. 在公开仓库添加合适的 `LICENSE`，并检查 Git 历史中从未提交过密钥。

## 8. GitHub 公开前检查清单

在推送为公开仓库前，建议逐项确认：

- [ ] `.env`、`.env.home` 和所有 API Key 未被 Git 跟踪。
- [ ] 没有提交真实学生姓名、学号、密码、Token、访问日志或数据库备份。
- [ ] 示例 Excel 和知识库数据具备公开与再分发权限；历史 SQLite 数据库和运行日志不再随新代码分发。
- [ ] `git log -p` 历史中没有曾经提交过的密钥；仅删除当前文件不能清除历史。
- [ ] 已添加符合项目意图的 `LICENSE`。
- [ ] README 中的仓库地址、作者、截图和联系方式已补充为最终信息。
- [ ] 执行 `.\scripts\dev\verify.ps1` 并通过全部测试与构建。
- [ ] 在一台没有本项目缓存的新电脑或虚拟机上按本文 Docker 步骤验证启动。

完成以上步骤后，新用户应能通过“双击启动（或手动复制配置并启动容器）→ 使用初始管理员登录并改密 → 导入馆藏 → 构建标签与索引”的顺序，在本地得到可用的完整系统。
