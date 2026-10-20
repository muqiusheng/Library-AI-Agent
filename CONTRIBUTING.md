# 代码拉取、推送与项目协作指南

适用仓库：`https://github.com/muqiusheng/Library-AI-Agent.git`。命令默认使用 Windows PowerShell，在仓库根目录执行；分支名、Issue 编号和文件路径示例应按任务替换。

准备开发下一项功能或发布新版本时，请按 [项目迭代实操指南](./docs/ITERATION.md) 执行。指南覆盖首次主线交接、需求验收、分层实现、数据库迁移、测试评审、版本发布、回滚和紧急修复。

## 1. 分支设计

采用 GitHub Flow：`main` 保存经过评审、验证的集成代码，每项任务使用短期分支，通过 Pull Request（PR）合入 `main`。暂不增加常驻 `develop`，避免同一套系统维护两条集成线；只有出现多个版本并行维护的实际需求时，再引入 `release/<major>.<minor>`。

```text
main ──●──────────────────────●──→
        └── feat/123-xxx ──●───┘
                    验证 + PR 评审
```

分支按“工作类型 + 工作内容”命名，不按工具或人员命名。统一使用小写英文、数字和连字符：`<type>/<issue-id>-<short-description>`；没有 Issue 时省略编号。

| 分支 | 用途 | 示例 |
|---|---|---|
| `main` | 集成主线；目标是保持可验证、可部署 | `main` |
| `feat/*` | 新功能 | `feat/123-reading-progress` |
| `fix/*` | 缺陷修复 | `fix/124-login-validation` |
| `refactor/*` | 不改变外部行为的结构调整 | `refactor/recommendation-service` |
| `docs/*` | 文档 | `docs/deployment-guide` |
| `test/*` | 测试与验证 | `test/profile-memory` |
| `chore/*` | 仓库、构建、依赖及工程维护 | `chore/repository-standardization` |
| `hotfix/*` | 已发布版本的紧急修复 | `hotfix/125-auth-expiry` |

每个分支只解决一个明确问题，尽量在数天内完成。环境差异使用配置管理，发布版本使用标签，不用 `main01`、`main02` 等名称表达版本。`hotfix` 通常从 `main` 创建；若线上版本落后于主线，应从对应发布标签创建，并安排修复回流主线。

## 2. 当前仓库的迁移状态

2026-10-20，本地当前分支由 `codex/github-public` 改为 `chore/repository-standardization`，定位为仓库规范化与既有系统交付的集成分支。改名只改变引用名称，不改变提交内容。

首次检查时，本地缓存的 `origin/HEAD` 指向 `origin/main`，当前分支比本地缓存的 `origin/main` 多 5 个提交。后续联网核实发现，远程实际默认分支为 `codex/github-public`，本地默认分支缓存已过时。

这条分支包含此前积累的系统实现及文档。首次向 `main` 提交 PR 时，要评审完整差异，不能将其视为只有本次协作文档的修改。完成首次集成后，新任务统一从更新后的 `main` 创建。集成前若必须依赖此分支开发，应在 PR 中注明依赖关系，并在首次集成后调整 PR 目标与差异。

本次已通过 GitHub 原生分支重命名接口将远程分支改为 `chore/repository-standardization`，提交仍为 `c4fe894151c0371612ac27cccacb6c91c35e1f7c`。旧远程名称已不存在，本地上游已更新为 `origin/chore/repository-standardization`，本地 `origin/HEAD` 也已刷新。远程默认分支随原生改名更新为新名称；`main` 尚未成为实际默认分支，需完成首次集成后再由维护者切换。

此次新增文档尚未提交，远程改名没有发布这些工作区修改。其他成员需按第 7 节更新本地分支和上游，并检查部署配置、脚本等旧名称引用。可用下面的命令核对实际状态：

```powershell
git branch --show-current
git branch -vv
git remote -v
git ls-remote --symref origin HEAD
git ls-remote --heads origin
```

## 3. 首次获取代码

准备 Git、Python 3.12+、uv，以及满足项目构建要求的 Node.js/npm。安装和运行细节见 [部署指南](./DEPLOYMENT.md)。

```powershell
git clone https://github.com/muqiusheng/Library-AI-Agent.git
Set-Location Library-AI-Agent
git remote -v
git branch -vv

# 身份仅设置在本仓库；替换为自己的姓名和 GitHub 已验证邮箱
git config user.name "Your Name"
git config user.email "your-verified-email@example.com"

uv sync --locked
Push-Location frontend
npm ci
Pop-Location

# 仅首次创建；已有 .env 时不要覆盖
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

克隆默认进入远程默认分支，不一定包含尚未合并的交付内容。首次集成前，如需协作当前交付分支，先确认同名远程分支已发布，再执行 `git switch --track origin/chore/repository-standardization`；本地已有同名分支时直接 `git switch chore/repository-standardization`。

推送需要仓库写权限。HTTPS 认证使用 Git Credential Manager、浏览器登录或 GitHub 支持的令牌方式，不使用账号密码，也不把令牌放入仓库 URL。无写权限的外部贡献者使用 Fork，并向原仓库提交 PR。

## 4. 日常开发：拉取 → 创建分支 → 提交 → 推送

开始前确认 `git status`；有未完成修改时先提交到所属任务分支，或临时使用 `git stash push -u -m "wip: before switching task"`，切回后用 `git stash pop` 恢复并检查冲突。stash 只保存在本机，不是远程备份。

```powershell
git status
git fetch --prune origin
git switch main
git pull --ff-only origin main
git switch -c feat/123-reading-progress
```

`fetch` 更新远程跟踪引用，不会自动合并工作代码；`pull --ff-only` 只接受快进，遇到分叉会停止，方便先检查原因。如果本地 `main` 分叉，先用 `git log --oneline --left-right main...origin/main` 检查，不要直接重置丢弃提交。

完成一个可理解的改动后，检查并选择性暂存：

```powershell
git diff
# 示例路径；按实际改动替换，不要直接提交所有运行时文件
git add app/services/recommendation.py
git diff --cached
git commit -m "feat(recommendation): support reading progress"

# 第一次推送设置上游，以后同一分支执行 git push 即可
git push -u origin feat/123-reading-progress
```

提交信息使用 `<type>(<scope>): <description>`，scope 可省略，描述可用中文。常用 type 与分支前缀一致，例如 `fix(auth): 修复登录校验`、`docs: 补充部署步骤`。一次提交表达一个逻辑变化。

`commit` 只保存到本机；`push` 才上传提交。推送分支不会自动合并到 `main`，还需要 PR。开始推送前用 `git branch -vv` 检查当前分支和上游，避免推到旧分支。

## 5. 同步他人改动与解决冲突

同一任务分支有多人协作时，指定协调人，默认使用 merge 同步，保留已发布提交：

```powershell
# 在自己的任务分支，先保证工作区干净
git pull --ff-only
# 如果提示分叉，先检查双方提交，再合并远程同名分支
git fetch origin
git merge origin/feat/123-reading-progress

# 同步主线新改动；仍在任务分支执行
git merge origin/main
git push
```

如果 pull 已成功且无需同步主线，可以直接继续开发；上面 merge 命令分别用于分叉处理和主线同步，按实际需要执行。推送出现 `non-fast-forward` 时，先 fetch、检查、merge，不用强推覆盖他人提交。

发生 merge 冲突时：

1. `git status` 找出冲突文件，与相关开发者确认业务行为。
2. 编辑冲突文件，删除 `<<<<<<<`、`=======`、`>>>>>>>` 标记，保留正确实现。
3. 执行相关测试，`git add <已解决的文件路径>`，再执行 `git merge --continue`。
4. 完成验证后 `git push`。如果决定取消本次合并，执行 `git merge --abort`。

未推送、仅自己使用的分支可以用 `git rebase origin/main` 整理历史；冲突后使用 `git rebase --continue` 或 `git rebase --abort`。已发布的共享分支不做 rebase，不对 `main` 或共享分支执行强推。

## 6. PR、验证与评审

在 GitHub 打开 PR，通常设置 `base: main`、`compare: 自己的任务分支`。提前发 Draft PR 便于协作；准备完成后再请求评审。仓库提供了 [PR 模板](./.github/pull_request_template.md)。

PR 应说明问题、实现后行为、影响范围、验证证据，以及新增环境变量、数据库迁移和回滚方式；界面变化附截图。关联 Issue 可使用 `Closes #123`。数据库迁移应审查 Alembic 脚本及已有数据兼容性，不能只验证空库启动。

代码变更在依赖已安装的环境中执行以下检查；任一步失败都应先修复，再继续提交评审：

```powershell
uv run --locked pytest app/tests -q
uv run --locked ruff check app
Push-Location frontend
npm run test
npm run build
Pop-Location
```

`npm run build` 已包含 TypeScript 类型检查。也可运行项目现有的 `.\scripts\verify.ps1`，但该脚本目前没有逐步检查原生命令退出码，不能只凭末尾的成功提示判断全部通过，应核对每项结果。纯文档变更检查链接、路径、命令和 `git diff --check` 即可。

至少由另一位成员检查业务逻辑、权限与数据边界、兼容性、验证结果。新增行为应有相应测试；修复缺陷时优先增加能复现问题的测试。确认讨论已解决后，由维护者执行 Squash and merge，合并提交标题遵循提交规范。合并代表代码集成，生产部署另按部署指南执行。

合并后更新本地：

```powershell
git switch main
git pull --ff-only origin main
git fetch --prune origin

# 普通 merge 后且提交已合入，可安全删除本地任务分支
git branch -d feat/123-reading-progress
```

Squash 合并生成新提交，`git branch -d` 可能拒绝删除旧分支。这时先确认 GitHub PR 已合并、代码已包含在主线，且没有遗留提交；确认后才手动用 `git branch -D <任务分支>` 删除。远程任务分支可在 PR 合并页面删除。

## 7. 分支改名与旧成员迁移

本次本地和远程均已改名，上游关联已更新，不需要再次推送来完成改名。将来仅在本地改名、尚未发布同名远程分支时，可在当前分支执行：

```powershell
git push -u origin chore/repository-standardization
git branch -vv
```

其他成员保留自己的本地提交，并更新名称和上游：

```powershell
git status
git fetch origin
# 本地仍使用旧名称、且新名称未被占用时执行
git switch codex/github-public
git branch -m chore/repository-standardization
git branch --set-upstream-to=origin/chore/repository-standardization
git status -sb
git log --oneline --left-right HEAD...origin/chore/repository-standardization
```

若双方有不同提交，先合并并验证，不要重置覆盖。旧远程分支删除前，维护者需要确认新分支存在、旧分支没有遗漏提交，检查以旧分支为源或目标的 PR、部署配置及其他引用，并通知协作者迁移。创建新分支再删除旧分支不会自动迁移这些关联。

本次使用 GitHub 原生改名，旧远程分支已不存在，无需再次删除。将来采用“新建分支再删除旧分支”的迁移方式时，只有旧分支仍存在且完成上述检查后，才由维护者执行：

```powershell
git push origin --delete codex/github-public
git fetch --prune origin
```

`codex/v2-scaffold`、`main01`、`main02`、`main03` 等其他历史分支暂不批量改名或删除，需逐条确认未合并工作和使用方。此次保留原默认分支身份并随改名更新其名称，没有合并或覆盖 `main`。

## 8. 维护者的仓库设置与发布

以下是待维护者在 GitHub 核对并配置的规则，不代表本次已启用：

- 保护 `main`，通过 PR 合并，要求至少一位其他成员批准并解决评审讨论。
- 禁止对 `main` 强推和删除，按团队需要限制绕过保护的权限。
- 仓库当前未提供 GitHub Actions 工作流。先通过 PR 建立并验证 CI，再将真实检查名称设为必需检查；此前在 PR 附本地验证结果。
- 团队使用 Squash merge；需要发布时，在经过验证的主线提交创建 `v<major>.<minor>.<patch>` 标签，并记录发布说明、配置变化及数据库迁移。
- 线上缺陷修复后回流主线。回滚代码优先使用 `git revert <提交>` 后提交 PR；Squash PR 对应一个合并提交。数据库和数据变更需独立评估回滚，不能假设代码回退就能恢复数据。

不要提交 `.env`、API Key、密码、真实用户数据、数据库、日志或本地运行缓存。提交前检查 `git diff --cached`；`.gitignore` 不会移除已被 Git 跟踪的敏感文件。如密钥曾被推送，应立即撤销或轮换，并由维护者评估历史清理。

流程依据：[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)、[受保护分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)。项目运行与部署参考 [DEPLOYMENT.md](./DEPLOYMENT.md)。
