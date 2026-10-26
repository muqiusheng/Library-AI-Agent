# 项目结构与目录职责

本次整理日期：2026-10-20。按后端、前端、测试、静态资源、脚本、文档和运行数据划分；应用模块与数据库迁移的导入路径保持现状。

## 代码与测试

| 路径 | 职责 |
|---|---|
| `app/main.py`、`app/cli.py` | FastAPI 应用与数据处理 CLI 入口 |
| `app/api/` | 依赖注入、HTTP 路由、认证和参数入口 |
| `app/core/` | 配置、安全、错误处理和限流 |
| `app/schemas/` | Pydantic 请求、响应和业务数据结构 |
| `app/services/` | 推荐、画像、会话、学习路径、预约和管理业务 |
| `app/repositories/` | 可复用的数据访问 |
| `app/db/models/`、`app/db/session.py` | ORM 模型与数据库会话 |
| `app/db/migrations/` | Alembic 迁移，根目录 `alembic.ini` 指向此处 |
| `app/integrations/` | 课程、馆藏、LLM、嵌入模型和向量库适配 |
| `app/pipelines/` | 馆藏清洗、导入、标签和索引管道 |
| `tests/` | 全部后端 Pytest；默认发现路径由 `pyproject.toml` 配置 |
| `frontend/src/pages/`、`frontend/src/components/` | 页面与可复用界面组件 |
| `frontend/src/api/`、`frontend/src/types/` | API 客户端与 TypeScript 契约 |
| `frontend/src/stores/`、`frontend/src/router/` | Pinia 状态与路由 |
| `frontend/src/utils/` | 前端工具及相邻的 Vitest 测试 |
| `frontend/mock/` | 前端模拟数据 |

开发入口使用 `uv run uvicorn app.main:app --reload`。根目录 `main.py` 继续提供兼容启动入口，Python 依赖、锁文件和工具配置保留在根目录，前端依赖及构建配置保留在 `frontend/`。

## 资料与运行数据

| 路径 | 内容与维护方式 |
|---|---|
| `resources/knowledge_base/` | 随仓库维护的馆藏 Excel、摘要、规则、问答和意图样本；详见[资源说明](../resources/README.md) |
| `docs/deployment/` | 环境配置、本地运行和家庭服务器部署 |
| `docs/development/` | 需求、实现、验证、发布与回滚流程 |
| `docs/policies/` | 隐私和试用边界 |
| `docs/references/project/` | 立项参考材料 |
| `docs/references/official/` | 官方比赛通知等原始资料 |
| `docs/references/extracted/` | 历史文档的文本提取，原内容保留 |
| `docs/competition/proposals/` | 参赛项目计划书，保留原文件名和版本 |
| `docs/competition/figures/` | 架构与推荐流程图的 HTML、PNG 和 PPTX |
| `data/` | 本机 Chroma、上传文件、备份、运维日志与发布记录；整体被 Git 忽略 |

容器运行数据仍使用 Compose 命名卷。历史 `library_data.db` 与 `backend.log` 已取消 Git 跟踪并加入忽略规则，本机文件保留，新部署不再分发这些运行数据；当前应用使用 PostgreSQL。其他旧检出拉取更新前如需保留历史副本，请先备份到 `data/legacy/`。旧 `chroma_db/` 与 `.proxy-repair-backup/` 属于本机维护遗留，不作为新文件的放置位置。现有数据库和持久化卷不迁移、不清空。新日志应放在 `data/` 下；`.venv/`、缓存、`frontend/node_modules/` 和 `frontend/dist/` 由各工具管理。

## 脚本与部署入口

- 根目录 `start.cmd` / `stop.cmd`：Windows 双击启停，由 `scripts/launcher.ps1` 实现，自动选择已有家庭配置或本地 Docker 栈，保留配置与数据；见[快捷启动](./deployment/QUICK_START.md)。
- `scripts/dev/`：本地启停、演示重置和质量验证。
- `scripts/home/`：生产启停、环境初始化、健康检查、备份恢复、发布检查和 Windows 定时任务管理。
- `scripts/network/`：Funnel 开启、关闭和状态检查。
- `scripts/home-start.ps1`、`scripts/home-health.ps1`、`scripts/home-backup.ps1`：旧定时任务的兼容入口，转发参数到 `scripts/home/`；后续维护实现只修改新位置。

脚本清单与命令见[脚本说明](../scripts/README.md)。`Dockerfile`、两个 Compose 文件和环境配置继续保留在根目录，前端镜像及 Nginx 配置仍在 `frontend/`。`docker compose up` 和现有持久化卷名保持不变。

## 旧路径对照

以下路径均相对仓库根目录：

| 原位置 | 新位置 |
|---|---|
| `app/tests/` | `tests/` |
| `docs/knowledge_base/` | `resources/knowledge_base/` |
| `DEPLOYMENT.md` | `docs/deployment/DEPLOYMENT.md` |
| `docs/ITERATION.md` | `docs/development/ITERATION.md` |
| `docs/PRIVACY.md` | `docs/policies/PRIVACY.md` |
| `参考文档/` | `docs/references/project/` |
| `参考文档（官方文档）/` | `docs/references/official/` |
| 根目录 `doc_dump_utf8.txt`、`full_ref_content.txt` | `docs/references/extracted/` 下的同名文件 |
| `参赛文档/` 中的 DOCX | `docs/competition/proposals/` |
| `参赛文档/` 中的 HTML、PNG、PPTX | `docs/competition/figures/` |
| `scripts/` 下的 `start.ps1`、`stop.ps1`、`verify.ps1`、`reset-demo.ps1` | `scripts/dev/` 下的同名文件 |
| `scripts/` 下的 `funnel-*.ps1` | `scripts/network/` 下的同名文件 |
| `scripts/` 下的其余运维脚本 | `scripts/home/` 下的同名文件；上述三个旧定时任务入口保留转发 |

## 后续维护规则

### VS Code 文件浏览器

项目级显示规则保存在 [`.vscode/settings.json`](../.vscode/settings.json) 的 `files.exclude` 中。默认隐藏依赖目录、Python 缓存、构建输出、运行数据、数据库文件、日志、依赖锁文件，以及 `.trae/` 和 `.proxy-repair-backup/` 等本机工具目录。源码、测试、文档、脚本和环境配置保持可见。

隐藏只影响 VS Code 文件浏览器，文件仍然保存在磁盘上，运行和 Git 跟踪规则不变。需要查看某项时，在该配置中删除对应规则或将值改为 `false`；锁文件仍需随依赖变更正常提交。

### 文件放置与目录变更

新增后端测试放在 `tests/`，前端工具测试继续邻近对应工具。新静态样本放在 `resources/`，上传文件和生成的数据放在 `data/`。项目指南放在 `docs/`，比赛交付物放在 `docs/competition/`，外部参考资料放在 `docs/references/`。

移动目录时检查 README、文档导航、相关指南、Pytest 配置、脚本根目录计算和定时任务入口。Ruff 检查需覆盖 `app tests`，避免测试移出应用目录后漏检。文档中的命令默认从仓库根目录执行。
