# 书途智启（BookPath AI）

书途智启是一个面向高校学生的智能图书推荐与阅读学习路径系统。系统将学生的专业、课程、阅读目标、难度偏好和历史反馈与真实馆藏数据结合，通过多轮对话生成可解释的图书推荐，并把推荐结果进一步组织成可执行的分阶段学习路径。

本项目不是让大模型凭空“编书单”：候选图书、馆藏状态和馆藏位置来自数据库，向量检索与规则负责召回和约束，大模型主要用于理解需求、组织说明和辅助生成标签。未配置大模型 API Key 时，系统仍可使用确定性降级方案完成基础推荐。

> Windows 用户安装 Docker Desktop 后，双击根目录 `start.cmd` 即可启动并打开网页，双击 `stop.cmd` 停止。全新本地空库的超级管理员为 `admin` / `BookPath@123`，已有部署保留原账号密码。见[快捷启动与初始账号](./docs/deployment/QUICK_START.md)或[详细部署指南](./docs/deployment/DEPLOYMENT.md)。

## 核心能力

### 学生端

- 学号注册与登录：使用 Argon2 哈希保存密码、JWT 完成身份认证。
- 学生画像：记录专业、课程、阅读目标、基础水平、兴趣和偏好。
- 多轮对话推荐：可继续补充“从零开始”“只看在馆可借”“难度低一些”等条件。
- 真实馆藏推荐：推荐结果关联书目、副本、索书号、馆藏地和可借状态。
- 可解释匹配：展示课程匹配、兴趣匹配、难度匹配和综合匹配原因。
- 动态画像记忆：从对话与反馈中更新偏好，同时支持用户查看、编辑和删除。
- 阅读反馈：支持喜欢、不感兴趣、难度评价和已读状态，后续推荐会参考反馈。
- 学习路径：把推荐图书组织为分阶段阅读计划，支持进度和状态更新。
- 模拟预约与通知：演示预约、取消和站内通知闭环，并明确标注未对接真实学校系统。
- 匿名评测：从多个维度对推荐质量进行 1～5 分评价。

### 管理端

- 馆藏 Excel 上传、清洗、ISBN 校验、聚合和批量入库。
- 以文件 SHA-256 实现重复导入保护。
- 草稿数据版本、异常报告和审核后发布。
- 规则标签、AI 批量标签、人工编辑和批量审核追踪。
- 版本化 Chroma 向量索引构建。
- 用户、角色、账号状态和密码重置管理。
- 数据库业务指标、AI Provider 状态和白名单业务配置。
- 匿名评测汇总、五维均值、评分分布和典型场景统计。

## 典型使用流程

1. 管理员导入馆藏 Excel，生成标签并构建向量索引。
2. 学生注册账号并填写课程、基础水平和阅读目标。
3. 学生在工作台输入自然语言需求，例如“我想从零开始学习 Java，只推荐目前可借的书”。
4. 系统从已发布的真实馆藏中召回候选，应用画像、对话条件和历史反馈进行排序。
5. 系统以流式响应返回推荐说明、Top 5 推荐卡片和匹配度分项。
6. 学生继续细化要求，提交反馈，或将推荐结果生成分阶段学习路径。
7. 学生更新阅读进度，并可体验模拟预约、通知和匿名评测。

## 技术架构

| 层级 | 主要技术 | 作用 |
|---|---|---|
| Web 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Tailwind CSS | 注册登录、推荐工作台、画像、学习路径和管理后台 |
| HTTP API | FastAPI、Pydantic、Uvicorn | REST API、SSE 流式推荐、参数校验和统一错误响应 |
| 数据访问 | SQLAlchemy 2、Alembic、psycopg | 业务模型、事务、查询索引和数据库迁移 |
| 关系数据库 | PostgreSQL 16 | 用户、馆藏、推荐、路径、反馈、预约和管理数据 |
| 向量检索 | Chroma | 保存版本化书目向量并进行语义召回 |
| AI 接入 | OpenAI 兼容客户端、DeepSeek Provider | 需求理解、结构化输出和辅助标签生成 |
| 安全 | Argon2、JWT、RBAC、CORS、限流 | 密码保护、身份认证、管理员权限和接口防护 |
| 交付 | Docker、Docker Compose、Nginx | 本地一键启动与家庭服务器部署 |

系统使用统一的 `/api/v1` API 前缀；FastAPI 自动接口文档位于 `/docs`。前端开发服务器通过代理访问后端，Docker 开发栈则使用构建时配置的 API 地址。

## 推荐链路如何工作

推荐请求会依次综合以下信息：

1. 基础画像：专业、课程、学习阶段、兴趣和初始目标。
2. 当前对话：用户本轮问题及多轮会话中保留的条件。
3. 动态记忆：用户确认或系统从历史交互中提取的长期偏好。
4. 历史反馈：喜欢、不感兴趣、已读和难度评价。
5. 馆藏约束：已发布数据版本、真实书目和副本可借状态。
6. 检索排序：规则过滤、向量召回与匹配度计算。
7. 结果生成：只引用候选书目的事实，输出解释、推荐卡片和后续建议。

这种设计将“自然语言表达能力”与“馆藏事实来源”分离，降低大模型产生不存在书目、错误馆藏位置或错误借阅状态的风险。

## 数据与降级策略

- 仓库内提供示例馆藏文件：`resources/knowledge_base/books/ShiepbookInfo.xlsx`。
- 导入后需要依次执行规则标签和向量索引构建，才具备完整的馆藏推荐能力。
- 默认嵌入模型接口为 `BAAI/bge-small-zh-v1.5`；模型不可用时，程序会使用确定性的字符哈希向量降级。
- `DEEPSEEK_API_KEY` 为可选配置。未配置时，基础推荐仍可工作，但依赖大模型的能力会降级或给出明确提示。
- Chroma 和 PostgreSQL 数据均持久化保存；Docker 容器重建不会自动删除命名卷。

## 项目结构

```text
Library-AI-Agent/
├─ app/                    # 后端接口、业务、数据访问、模型适配与管道
├─ frontend/               # Vue 前端：页面、组件、API、状态和类型
├─ tests/                  # 后端自动化测试，与 app/ 分离
├─ resources/
│  └─ knowledge_base/      # 示例馆藏、规则和知识库样本
├─ scripts/
│  ├─ dev/                 # 本地启停、质量验证、演示重置
│  ├─ home/                # 家庭部署、备份恢复和定时任务管理
│  └─ network/             # Tailscale Funnel 网络入口
├─ docs/
│  ├─ README.md            # 文档导航
│  ├─ STRUCTURE.md         # 目录职责、迁移对照和维护规则
│  ├─ deployment/          # 环境与部署指南
│  ├─ development/         # 开发迭代指南
│  ├─ policies/            # 隐私与试用边界
│  ├─ references/          # 立项参考、官方资料和历史文本提取
│  └─ competition/         # 参赛计划书与展示图
├─ data/                   # 本机运行数据与备份，Git 忽略
├─ Dockerfile              # 后端镜像构建入口
├─ docker-compose.yml      # 本地 Docker 开发栈
├─ docker-compose.home.yml # 家庭服务器生产栈
├─ start.cmd / stop.cmd    # Windows 双击启停入口
├─ reset-admin-password.cmd # 忘记超级管理员密码时的恢复入口
├─ CONTRIBUTING.md         # 协作与 Git 工作流
└─ README.md               # 项目介绍与快速开始
```

完整说明见 [目录职责与迁移对照](./docs/STRUCTURE.md)，其他资料见 [文档导航](./docs/README.md)。后端入口仍为 `app.main:app`，命令默认从仓库根目录执行。

## 快速开始

Windows 用户下载项目后，双击根目录 `start.cmd` 即可。启动器会检查 Docker、仅在缺少配置时创建配置，并在服务就绪后自动打开浏览器。已有 `.env.home` 时自动复用家庭栈，否则使用本地栈。更新代码后执行 `start.cmd -Rebuild`。

也可手动运行 Docker Compose：

```powershell
git clone <你的 GitHub 仓库地址>
Set-Location Library-AI-Agent
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build
```

打开 <http://localhost:4173>。首次启动会迁移数据库，并且仅在用户表为空时创建超级管理员：用户名（学号）`admin`，初始密码 `BookPath@123`。登录后请在用户管理中重置密码。家庭生产配置生成器使用随机初始密码，查看 `.env.home` 的 `BOOTSTRAP_ADMIN_PASSWORD`。已有任何账号时跳过初始化，不覆盖原账号、密码、角色和业务数据。

忘记超级管理员密码时，先启动系统，再双击根目录 `reset-admin-password.cmd`，或在终端运行 `.\reset-admin-password.cmd`，按提示隐藏输入两次新密码即可；无需原密码或重建镜像，保留其他账号和业务数据。详见[密码恢复步骤](./docs/deployment/QUICK_START.md#忘记超级管理员密码)。

要看到真实推荐结果，还需导入馆藏、生成标签和索引。初始账号定制、旧部署兼容和双击启停见[快捷启动说明](./docs/deployment/QUICK_START.md)；完整命令、故障排查、原生开发和生产部署见[部署指南](./docs/deployment/DEPLOYMENT.md)。

## 常用地址

| 地址 | 说明 |
|---|---|
| <http://localhost:4173> | Docker 本地栈前端 |
| <http://localhost:8000/health> | 后端健康检查 |
| <http://localhost:8000/docs> | Swagger API 文档 |
| <http://localhost:8000/redoc> | ReDoc API 文档 |

## 测试与质量检查

Windows PowerShell 可执行项目自带的完整验证脚本：

```powershell
.\scripts\dev\verify.ps1
```

脚本会运行后端 Pytest、Ruff、前端 Vitest、TypeScript 类型检查和生产构建。各命令也可单独运行，详见部署指南中的“验证安装与运行测试”。

## 安全与隐私

- 不要提交 `.env`、`.env.home`、API Key、数据库密码或真实用户数据。
- 公开部署前必须替换默认 `JWT_SECRET` 和 PostgreSQL 密码，并启用接口限流。
- 生产配置会拒绝默认 JWT 密钥、默认数据库密码和未启用限流的组合。
- 项目中的预约是演示功能，不代表已连接学校图书馆系统。
- 管理员导入真实数据前，应确认数据授权范围并移除不应公开的个人信息。
- 更完整的边界说明见 [隐私说明](./docs/policies/PRIVACY.md)。

## 当前边界

- 课程目录当前由本地 Provider 提供，已预留学校教学系统的适配入口。
- 预约与通知为系统内部模拟闭环，未连接真实图书馆借阅接口。
- DeepSeek 是当前实现的外部模型 Provider；如需其他模型，可在集成层增加 OpenAI 兼容适配。
- 示例数据仅用于开发和演示，实际部署者需要自行确认数据来源、版权和使用权限。

## 参与开发

分支命名、代码拉取与推送、冲突处理、PR 评审和发布约定见 [项目协作指南](./CONTRIBUTING.md)。项目采用 `main` + 短期任务分支的 GitHub Flow，通过 PR 集成改动。

后续新增功能、修复缺陷和发布版本，请阅读 [项目迭代实操指南](./docs/development/ITERATION.md)，按需求验收、任务分支、实现验证、PR 合并、版本发布及回滚的流程推进。首次迭代前需先完成交付分支到 `main` 的集成与默认分支切换。

欢迎通过 Issue 报告缺陷或提出功能建议。提交代码前请：

1. 从新分支进行修改。
2. 不提交密钥、运行时数据和个人信息。
3. 为新增后端逻辑补充 Pytest，为前端工具逻辑补充 Vitest。
4. 执行 `.\scripts\dev\verify.ps1` 并确保检查通过。
5. 在 Pull Request 中说明功能影响、验证方式和必要的配置变化。

## License

当前仓库尚未包含开源许可证。正式公开前，请仓库所有者根据希望允许的使用、修改和再分发范围选择并添加 `LICENSE`（例如 MIT、Apache-2.0 或其他适合的许可证）。在许可证添加前，默认版权规则仍然适用。
