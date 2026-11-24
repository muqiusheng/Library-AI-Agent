# Instabox 部署

部署日期：2026-11-24（北京时间）。

- 实例：`fck`（`m_agrazil7kddepuxpn3avhjqu6q`），4 vCPU / 8 GiB 内存。
- 网站：<https://8180-agrazil7kddepuxpn3avhjqu6q.instabox.tech>。
- 服务器项目目录：`/data/home/Library-AI-Agent`。
- 配置：`docker-compose.instabox.yml` 与 `.env.instabox`。
- 管理员学号：`admin`；迁移后沿用原电脑上该账号的当前密码。其他账号同样保留原密码。

`.env.instabox` 已被 Git 忽略，包含此部署独立生成的数据库密码、JWT 密钥和管理员密码，以及已有生产配置中的 DeepSeek 配置。请保留该文件，不要提交或公开。

## 暂停后恢复

在 Instabox 控制台恢复实例。容器使用 `restart: unless-stopped`，Docker 随系统启动。需要手动启动或恢复端口入口时，在这台实例的终端执行：

```sh
cd /data/home/Library-AI-Agent
sh scripts/instabox/start.sh
```

实例详情显示空闲 30 分钟自动暂停，部署时单次最长运行 2 小时（随使用增长，最高 8 小时）。网站受平台运行限制，不能作为全天在线服务。保留实例及其磁盘；删除实例会丢失该实例内的数据。

## 更新与检查

更新服务器上的源代码后执行：

```sh
cd /data/home/Library-AI-Agent
docker compose -f docker-compose.instabox.yml up -d --build --wait
docker compose -f docker-compose.instabox.yml ps
curl -fsS http://127.0.0.1:8180/health
```

前端使用相对路径 `/api/v1` 连接后端，由 Nginx 统一转发。仅网站入口绑定本机 `8180` 端口，并通过 Instabox 提供 HTTPS 地址；PostgreSQL 和后端没有对外发布端口。

## 数据与账号

已导入仓库中的 `可借_2021 至今_去重_已标注领域难度.xlsx`：6,621 条馆藏记录，聚合为 6,604 本图书；随后执行规则标签和全部图书的索引构建。

数据库保存在 `bookpath-instabox_postgres_data`；检索索引和上传文件在完整迁移后使用 `docker-compose.instabox.yml` 中 `volumes.chroma_data.name` 和 `volumes.uploads_data.name` 指定的数据卷。更新容器保留这些卷。不要执行 `docker compose down -v`。

2026-11-24 已将原电脑的家庭部署完整迁入此实例，包含账号、密码哈希、聊天、推荐、收藏、阅读路径、学习画像、系统设置、检索索引和上传文件。原电脑上的服务保留，并在快照完成后恢复运行。此后两边各自写入，不会自动同步。

现有账号使用原部署的当前密码；`.env.instabox` 中的 `BOOTSTRAP_ADMIN_PASSWORD` 仅用于空数据库初始化，不能代表迁移后的现有账号密码。已启用请求限流，关闭公开注册；管理员可登录后管理用户。详情见 [数据迁移记录](./INSTABOX_MIGRATION.md)。

## 部署验收

- 三个容器均为 healthy，数据库迁移处于 `a74d192f0b31 (head)`。
- 公网 HTTPS 登录页、前端静态资源和页面直接访问正常。
- 健康检查、管理员登录、当前用户、后台概览及 AI 配置接口均返回 HTTP 200。
- HTTPS 来源的跨域预检通过。
- 完整对话推荐返回 3 本真实在馆可借的 Python 机器学习图书，包含推荐理由和索书号，流式响应正常结束。验收会话随后删除。

## 平台说明

已于 2026-11-24 配置 Cloudflare Worker `bookpath-instabox-keepalive`，每 10 分钟访问本站 `/health`，尝试避免空闲暂停并唤醒已因空闲暂停的实例。任务运行在 Cloudflare，电脑关机后仍可执行。配置可能需要最多 15 分钟传播；实例达到免费运行时限后的强制暂停和冷却仍然有效，不能因此保证全天在线。部署与停用步骤见 [定时访问维护说明](../../ops/cloudflare-keepalive/README.md)。

- [SSH 连接](https://instabox.sh/docs/ssh)
- [HTTPS 端口发布](https://instabox.sh/docs/ports)
- 本次授权创建的 SSH 凭据名称为 `Codex deployment 2026-11-24`，有效期 24 小时。到期只影响后续 SSH 连接，不影响已部署的应用。
