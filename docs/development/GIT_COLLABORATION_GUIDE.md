# 项目 Git 协作与分支操作指南

适用项目：Library-AI-Agent。分支状态核验日期：2026-10-29。命令默认在 Windows PowerShell 的项目根目录执行。

日常协作按这个顺序进行：保存当前工作，更新主线，为本次任务新建分支，修改并验证，提交到本机，推送到 GitHub，再通过 Pull Request（简称 PR，合并请求）进入 `main`。每项任务使用一个短期分支；代码和文档都遵循这个流程。

当前仓库：[Library-AI-Agent](https://github.com/deloisewampler8101987ted-ux/Library-AI-Agent)。已有协作规范见 [CONTRIBUTING.md](../../CONTRIBUTING.md)，开发与发布流程见 [迭代指南](./ITERATION.md)，运行方式见 [部署指南](../deployment/DEPLOYMENT.md)。

## 1 四个核心问题的直接答案

| 你想做什么 | 应该怎么做 |
|---|---|
| 别人更新了代码或文档，我怎么获取 | 先确认更新在哪个分支；切到对应本地分支，再执行 `git pull --ff-only`。只更新 `main`，拿不到尚未合入主线的其他分支改动。 |
| 我怎么进入某个分支 | 本地已有时使用 `git switch 分支名`；只有远程有时，先 fetch，再使用 `git switch --track origin/分支名`。 |
| 我要修改代码，是否先创建自己的分支 | 是。通常从更新后的 `main` 创建一个任务分支；同一项任务继续使用原分支，不必每天新建。 |
| 项目现在有哪些分支，分别做什么 | 远程目前有 `main`、`chore/repository-standardization`、`docs/collaboration-guide`，详细用途和合并状态见第 3 节。 |

## 2 先分清这些概念

| 名称 | 在本项目中的含义 |
|---|---|
| 工作区 | 你正在编辑的文件。未提交的修改尚未成为分支历史的一部分。 |
| 暂存区 | 本次准备提交的修改集合，通过 `git add` 选择。 |
| commit 提交 | 把暂存内容记录为本机的一次版本；不会自动上传。 |
| 分支 | 一条可以独立推进的提交线；切换时，Git 按目标分支更新受跟踪文件。 |
| `main` | 本地名为 main 的分支；创建后才会出现在 `git branch` 中。 |
| `origin` | 远程仓库的本地别名，使用 `git remote -v` 查看实际地址。 |
| `origin/main` | 本机记录的远程 main 状态，fetch 后更新；不是一个实时联网视图。 |
| 上游分支 | 本地分支默认拉取、推送所关联的远程分支。用 `git branch -vv` 查看。 |

`fetch` 获取远程提交和分支信息，通常不改动正在编辑的文件。`pull` 会先获取信息，再把指定远程分支整合进**当前分支**。`push` 上传本机提交；PR 则用于评审并合并分支。

**不要在自己的功能分支上执行 `git pull origin main` 来“切到主线”。** 它会把远程 main 整合进当前分支。切换分支应使用 `git switch`。这些行为可参考 [Git pull 官方说明](https://git-scm.com/docs/git-pull)。

## 3 项目当前有哪些分支

### 远程分支与用途

以下清单经过 `git fetch origin --prune` 和 `git ls-remote --symref origin HEAD 'refs/heads/*'` 核验，反映 2026-10-29 的状态；后续以重新查询的结果为准。

| 远程分支 | 当前用途与内容 | 相对 main 的状态 |
|---|---|---|
| `main` | 默认分支和集成主线，当前提交 `c15992e`。提交记录包含仓库规范化及协作文档的两次 PR 合并。新任务通常从这里开始。 | 比较基准 |
| `chore/repository-standardization` | 仓库规范化和早期交付集成分支，当前提交 `c4fe894`。其提交历史已经包含在 main 中。 | 独有 0 个提交；main 独有 4 个提交 |
| `docs/collaboration-guide` | 起初用于协作文档，后续还增加首次部署、快捷启停、管理员初始化及密码重置等代码，当前提交 `643c3f5`。 | 分支独有 4 个提交；main 独有 1 个提交 |

`docs/collaboration-guide` 的 4 个独有提交为 `bd246a7`、`8ba4601`、`08ade3c`、`643c3f5`。main 独有的 1 个提交是合并提交 `c15992e`。这些数字比较的是提交历史，不能直接理解成缺少几项功能。

**具体怎么选：** 开始一项常规新任务，选 `main`。需要查看尚未进入主线的快捷启停或密码重置实现，选 `docs/collaboration-guide`。需要基于这些实现继续开发，应先与相关负责人确定依赖和 PR 目标，并从该分支另建任务分支。`chore/repository-standardization` 可用于历史核对，通常不再作为新任务起点。

### 本机分支与远程分支的区别

本次核验时，本机有两个本地分支：

- `docs/collaboration-guide`：当前分支，跟踪 `origin/docs/collaboration-guide`。
- `codex/github-public`：跟踪 `origin/main`，当前提交也是 `c15992e`。这是本机保留的名称，远程已没有同名分支。

本机当时尚无名为 `main` 的本地分支。首次使用主线时，可在保存当前修改后执行 `git switch --track origin/main` 创建；其他成员若已有本地 main，则执行 `git switch main`。不需要为了创建 main 删除现有本地分支。

`origin/HEAD -> origin/main` 表示远程默认分支的本地记录，不应算作第四个业务分支。旧资料中的 `main01`、`main02`、`main03`、`codex/v2-scaffold` 不在本次远程清单中。

### 以后怎么自己查询

```powershell
git fetch origin --prune
git branch --show-current
git branch
git branch -r
git branch -avv
git ls-remote --symref origin HEAD
git ls-remote --heads origin
```

依次用于更新信息、查看当前分支、本地分支、远程跟踪分支、全部分支及其上游、远程实际默认分支、远程实际分支列表。新手判断分支用途时，应同时看提交记录和 PR，不能只看分支名称。

## 4 第一次获取项目

### 已经有项目文件夹

先确认当前目录确实是仓库，不要再在项目里面克隆一份：

```powershell
Set-Location 'C:\大学文件\项目\Library-AI-Agent'
git status
git remote -v
git branch -vv
```

路径按自己电脑的位置替换。若显示 `not a git repository`，说明目录不对，或拿到的是不带 Git 历史的压缩包；切到正确目录，或另选空位置重新 clone。

### 电脑上还没有项目

在准备存放项目的父目录执行：

```powershell
$owner = 'deloisewampler8101987ted-ux'
git clone "https://github.com/$owner/Library-AI-Agent.git"
Set-Location Library-AI-Agent
git status
```

克隆会进入远程默认分支，目前是 main。安装依赖和首次启动另按部署指南进行。

### 第一次提交前设置身份

```powershell
git config user.name '你的姓名或 GitHub 用户名'
git config user.email '你的 GitHub 已验证邮箱或隐私邮箱'
git config --get user.name
git config --get user.email
```

引号内的身份要换成自己的信息。这是提交署名，与 GitHub 登录认证是两件事；上述配置仅作用于当前仓库。

## 5 别人更新代码或文档后怎么拉取

### 更新已经合入 main

先执行 `git status`。有未提交修改时，先按第 9 节保存。工作区干净后执行：

```powershell
git fetch origin --prune
git switch main
git pull --ff-only origin main
git status -sb
```

如果本地没有 main，把其中的 `git switch main` 换成 `git switch --track origin/main`，其余命令相同。`Already up to date.` 表示当前分支无需再更新；`--ff-only` 在双方历史分叉时会停止，出现该情况见第 12 节。

### 更新还在某个任务分支

以本项目的 `docs/collaboration-guide` 为例，本地已经有这个分支时：

```powershell
git fetch origin --prune
git switch docs/collaboration-guide
git pull --ff-only origin docs/collaboration-guide
```

如果本地还没有，在 fetch 后改用：

```powershell
git switch --track origin/docs/collaboration-guide
```

这会创建同名本地分支并设置上游。以后在该分支上可直接执行 `git pull --ff-only`。获取尚未合并的任务分支，适合查看或参与指定任务；不等于这些内容已成为主线版本。

### 我在自己的分支上工作

如果别人更新的是你的同名远程分支，在自己的分支执行 `git pull --ff-only`。如果别人更新的是 main，而你希望把它带入当前任务，应按第 8 节合并 `origin/main`。

代码、Markdown、Word 等已提交文件都随所在分支同步。别人只在本机保存、还没有 commit 和 push 的修改，无法被你拉取。

## 6 怎么进入已有分支或创建新分支

### 切换到本地已有分支

```powershell
git status
git switch docs/collaboration-guide
git branch --show-current
```

切回上一个分支可用 `git switch -`。切换后，编辑器显示的是目标分支对应的文件版本；文件增减或内容变化属于正常现象。

### 第一次进入远程分支

```powershell
git fetch origin --prune
git switch --track origin/chore/repository-standardization
```

这个例子仅演示建立本地跟踪分支。该历史分支的内容已经进入 main，日常开发通常不用切过去。有关创建与跟踪的命令行为见 [Git switch 官方说明](https://git-scm.com/docs/git-switch)。

### 为自己的任务创建分支

通常从更新后的 main 创建：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feat/search-filter
git branch --show-current
```

本地没有 main 时，仍按第 5 节替换切换命令。新建分支以**执行命令时所在的提交**为起点；在旧任务分支上直接新建，可能把旧任务未合并的内容一起带入。

分支按任务命名，不需要每个人永久占用一个“个人分支”。团队现有命名约定如下；有 Issue 时可加入编号，如 `feat/123-search-filter`。

| 工作类型 | 示例 |
|---|---|
| 新增功能 | `feat/search-filter` |
| 修复问题 | `fix/login-message` |
| 修改文档 | `docs/git-guide` |
| 调整结构 | `refactor/recommendation-service` |
| 补充测试 | `test/admin-password-reset` |
| 依赖与工程维护 | `chore/update-dependencies` |
| 已发布版本紧急修复 | `hotfix/auth-expiry` |

## 7 修改后怎么提交和推送

以下用修改本文档为例，完整演示一项文档任务。前提是工作区干净，并已准备好本地 main。

```powershell
git switch main
git pull --ff-only origin main
git switch -c docs/git-guide
```

接着编辑 `docs/development/GIT_COLLABORATION_GUIDE.md`。完成后检查并提交：

```powershell
git status
git diff
git add docs/development/GIT_COLLABORATION_GUIDE.md
git diff --cached
git diff --cached --check
git commit -m 'docs: 完善 Git 协作与分支操作指南'
git push -u origin docs/git-guide
```

上面的文件路径和分支名是示例，实际操作时替换成你这次修改的文件和任务分支。如果文件是新建的，`git diff` 在暂存前不会展示其内容；暂存后用 `git diff --cached` 检查。

代码任务采用同一流程，另需运行相关检查。只暂存本次任务涉及的文件，先核对暂存内容，再 commit。不要把 `.env`、密码、API Key、数据库、日志或本地依赖目录加入提交；项目的 `.env.example` 等配置模板按需要正常维护。

第一次推送的 `-u` 用于设置上游。同一分支后续完成新的 commit 后通常执行 `git push` 即可。`nothing to commit` 表示当前没有待提交差异；如果自己明明改过文件，检查是否保存、是否在正确目录、是否被忽略。

推送成功后，去 GitHub 创建 PR。**push 只更新任务分支，不会自动把修改合进 main。**

## 8 开发过程中怎么同步 main

main 有新改动，而你还在自己的任务分支开发时，先保存未提交修改，再执行：

```powershell
git switch feat/search-filter
git fetch origin --prune
git merge origin/main
```

上面的 `feat/search-filter` 换成你实际的任务分支。合并成功后运行相关验证；如果该任务分支已发布，执行 `git push` 上传新的合并结果。这里不必先更新本地 main，因为 fetch 已更新了 `origin/main`。

如果多人协作同一个任务分支，先同步同名远程分支，再按需同步 main：

```powershell
git pull --ff-only
git fetch origin
git merge origin/main
```

若第一步提示分叉，先按第 12 节处理，完成后再继续。共享分支默认用 merge 保留已发布历史；新手不必为日常同步引入 rebase 或强制推送。

## 9 修改还没提交但需要切换分支

### 修改已经属于一个明确任务

在该任务分支检查后提交，再切换。未完成的内容可只保存在本机提交中，整理和验证后再决定何时推送。

### 只是临时中断

可使用 stash 临时收起修改：

```powershell
git status
git stash push -u -m 'wip: 切换任务前暂存'
git stash list
git status
```

确认工作区干净后切换。完成临时事项、回到原任务分支后，先查看列表，确认要恢复的是哪条记录，再执行：

```powershell
git stash list
git stash apply 'stash@{0}'
git status
git diff
```

检查内容恢复正确后，再删除对应临时记录：

```powershell
git stash drop 'stash@{0}'
```

示例假设要恢复的是列表最新一条；如果不是，应替换编号。PowerShell 中给 `stash@{0}` 加单引号。`-u` 包含未跟踪文件，但不包含被忽略的文件；stash 仅保存在本机。恢复发生冲突时，保留 stash，解决文件后按正常流程提交，不执行 `git merge --continue`。

未提交修改有时会随分支切换保留下来，也可能导致切换被拒绝。不要把“成功切换”当成修改已经被隔离或保存。

## 10 怎么提交 PR 并完成合并

1. 推送自己的任务分支，打开项目的 GitHub 页面，进入 Pull requests，再选择 New pull request。
2. 常规任务选择 `base: main`，`compare: 你的任务分支`。先检查差异里是否只有本次任务的内容。
3. 填写修改原因、改动内容、验证结果；涉及配置、数据库或部署时说明相应操作，界面变化附截图。
4. 请其他成员评审。按意见继续修改、commit、push，同一个 PR 会更新，无需重复创建。
5. 检查通过、讨论解决后，由维护者按团队约定合并。当前协作规范采用 Squash and merge。

如果任务依赖尚未合入 main 的另一分支，在 PR 中明确依赖，并与负责人确定目标分支。不要为了让差异看起来少就随意更改 base。

main 合并完成后，其他成员才能通过更新 main 获取这些改动。合并与部署是两个步骤；线上服务是否更新，还需按部署流程核实。完整协作模式可参考 [GitHub Flow 官方说明](https://docs.github.com/en/get-started/using-github/github-flow)。

## 11 出现合并冲突怎么处理

冲突表示 Git 无法自动决定同一处内容应采用哪个版本。合并冲突时，先找出文件：

```powershell
git status
git diff --name-only --diff-filter=U
```

文本文件可能出现以下标记：

```text
<<<<<<< HEAD
当前分支的内容
=======
正在合入的分支内容
>>>>>>> origin/main
```

结合业务意图编辑成最终内容，删除冲突标记。不要一律选择“全部保留当前”或“全部保留传入”。解决后执行相关验证，再按实际文件逐个暂存，最后完成合并：

```powershell
# 示例文件名，替换为实际解决的文件
git add app/core/config.py
git diff --cached
git merge --continue
```

合并完成、验证通过后再 push。若决定放弃本次尚未完成的 merge，执行 `git merge --abort`；这是 merge 冲突的取消方式，不适用于所有操作。

Word、Excel 等二进制文件的冲突通常无法像文本一样逐行合并。协商保留哪一版，再手工补齐另一版的有效修改。本指南优先维护 Markdown 源稿，再生成 Word 版，可以减少这种冲突。

## 12 常见报错怎么处理

### 推送出现 non fast forward 或拉取提示无法快进

以自己的 `feat/search-filter` 分支为例，先确认当前分支，再查看双方独有提交：

```powershell
git branch --show-current
git fetch origin
git log --oneline --left-right HEAD...origin/feat/search-filter
```

输出中 `<` 为本地独有提交，`>` 为远程独有提交。确认是在同步同一任务后，在自己的任务分支合并：

```powershell
git merge origin/feat/search-filter
```

处理冲突、验证后执行 `git push`。如果分叉的是本地 main，先把本地独有提交保存为一个新任务分支，并与维护者核对，不要直接强推或重置 main。

### 切换时报本地修改会被覆盖

先执行 `git status`，按第 9 节提交或 stash。未跟踪文件也可能挡住切换，需要先保存到 stash 或另行备份；不要直接删除不认识的文件。

### 找不到分支

先执行 `git fetch origin --prune` 和 `git branch -a`，核对拼写及大小写。如果只有 `origin/分支名`，使用 `git switch --track origin/分支名`；如果本地与远程都没有，确认对方是否已经推送，或分支是否已改名、删除。

### 当前分支没有上游

准备首次发布自己的任务分支时，执行 `git push -u origin feat/search-filter`，将名称换成当前分支。若远程分支早已存在，先 fetch 并核对历史，再用 `git branch --set-upstream-to=origin/feat/search-filter` 建立关联。

### GitHub 提示无权限或认证失败

先用 `git remote -v` 核对仓库地址，再确认登录账号有写权限。HTTPS 使用 Git Credential Manager、浏览器登录或 GitHub 支持的令牌认证，不使用账号密码。没有写权限时，申请协作权限，或使用 Fork 后向原仓库提交 PR；不要把令牌写进仓库 URL 或聊天记录。

### 旧电脑还指向以前的仓库

当前 origin 应对应本文开头的仓库地址。确认团队已使用这个新地址后，可更新本地设置：

```powershell
$owner = 'deloisewampler8101987ted-ux'
git remote set-url origin "https://github.com/$owner/Library-AI-Agent.git"
git remote -v
git fetch origin --prune
```

改变地址不会自动处理本地提交差异，仍需检查分支和上游。不要因为旧文档记录过迁移，就重复执行分支改名或删除命令。

## 13 提交错了或改错了怎么撤销

### 已经 add 但还没 commit

以下命令撤销示例文件的暂存，文件修改仍然保留：

```powershell
git restore --staged app/core/config.py
```

### 想丢弃某个文件尚未暂存的修改

先用 `git diff -- app/core/config.py` 查看差异；确认这些修改不再需要后，才执行：

```powershell
git restore -- app/core/config.py
```

这会丢弃该文件未暂存的修改，Git 通常无法找回从未提交的内容。示例路径按实际文件替换。

### 在 main 上改了文件但还没提交

可从当前状态创建任务分支，把未提交修改带过去，再按正常流程检查、提交：

```powershell
git switch -c fix/config-validation
git status
```

这是纠正“改错分支”的情况，与从更新后的 main 开始新任务不同。若已经提交到本地 main，先创建任务分支保留提交，再核对如何恢复 main；若已推送共享分支，与维护者通过 revert 和 PR 修正。

### 已经推送的提交需要撤销

通常用 `git revert` 生成一条反向提交，再走 PR，保留团队已共享的历史。先用 `git log --oneline -10` 找到目标提交。普通提交或 Squash 提交可按其提交号 revert；合并提交需要判断主父提交，先由维护者确认，不能把同一个命令套用到所有提交。

日常同步不使用 `git reset --hard`、`git clean -fd` 或 `git push --force` 来解决问题；这些命令可能丢失修改或覆盖其他成员的提交。

## 14 拉取之后运行项目还需要做什么

Git 只同步仓库文件，不自动安装依赖、迁移数据库或重启服务。根据实际差异处理：

- Python 依赖或 `uv.lock` 变化时，在已安装 uv 的开发环境执行 `uv sync --locked`。
- 前端依赖或 `package-lock.json` 变化时，进入 `frontend` 执行 `npm ci`。
- `.env.example` 或 `.env.home.example` 变化时，对照模板补充自己环境的配置；保留本机已有密钥。
- 数据库迁移、容器构建或启动方式变化时，按部署指南及 PR 说明升级。
- 已运行的进程或容器需要按实际运行方式重新加载、重启或重建，才能用到新代码。

拉取代码不会复制别人电脑的数据库、运行数据、依赖目录和被忽略的环境配置。切换分支也不会为每个分支创建独立数据库；测试不同版本前，尤其要核对迁移与数据兼容性。

### 提交前需要做哪些检查

纯文档任务检查文字、链接、路径、命令和排版，执行 `git diff --check`；暂存后可执行 `git diff --cached --check`。代码任务按影响范围运行相关验证，团队现有完整检查命令为：

```powershell
uv run --locked pytest tests -q
uv run --locked ruff check app tests
Push-Location frontend
npm run test
npm run build
Pop-Location
```

`npm run build` 包含 TypeScript 类型检查。某一步失败时先解决，再继续提交评审；PR 中填写实际运行过的检查和结果。

## 15 PR 合并后怎么收尾

保存当前工作并确认 PR 已合并后，更新本地主线：

```powershell
git switch main
git pull --ff-only origin main
git fetch origin --prune
git branch -d docs/git-guide
```

把末行换成已完成的任务分支。`-d` 在 Git 判断分支未完全合并时可能拒绝删除；Squash 合并产生新提交，也可能导致这种情况。此时先检查 PR 已合并、主线已包含对应内容、分支没有剩余工作，再决定是否用 `git branch -D` 强制删除本地分支。

远程分支可在 GitHub 的已合并 PR 页面删除。默认配置下，fetch 的 `--prune` 清理已经失效的远程跟踪引用，不会替你删除本地任务分支。详见 [Git fetch 官方说明](https://git-scm.com/docs/git-fetch)。

旧分支不必因为“看起来过时”就马上删除。维护者确认 PR、依赖和使用方后再清理。

## 16 进一步需要掌握的问题

### 多人能不能改同一个分支

可以，但各自建立任务分支更便于评审和追踪。确实要共享分支时，约定文件分工和协调人，提交前同步远程；不要在已共享分支上随意 rebase 或强推。

### 更新文档也必须创建分支吗

是。文档也需要验证命令、路径和事实。使用 `docs/具体任务`，通过 PR 合并。Word 等导出版与 Markdown 源稿同时更新时，先完成源稿，再生成导出版。

### 我怎么知道本地比远程多了还是少了提交

先 fetch，再看 `git status -sb` 和 `git branch -vv`。`ahead` 表示有尚未推送的本地提交，`behind` 表示远程有尚未整合的提交，两者同时出现表示历史分叉。这些提示基于已设置的上游，与分支名称是否相同无关。

### 已经提交但还没推送会不会丢

提交保存在本机 Git 仓库中，正常切换分支不会删除它。电脑或磁盘损坏仍可能导致丢失，需要协作或远程备份时及时 push；push 不要求 PR 必须立即合并。

### 为什么删除远程分支后本地还看得到

本地分支与远程分支分别存在。先 fetch 加 prune 更新远程跟踪记录，再核对本地分支是否还需保留。`git branch -vv` 中的 `gone` 表示上游已不在当前本地的远程跟踪记录中，本地提交仍在。

### 为什么不为每个版本建立 main01 或 main02

本项目采用 main 加短期任务分支。需要标记发布版本时使用 `v1.2.3` 等标签；仅在确有多版本并行维护需求时再引入 release 分支。分支名表示正在进行的工作，发布标签标识一个具体版本。

### 怎么查看别人具体改了什么

先 fetch，再查看目标分支提交记录。以当前部署相关分支为例：

```powershell
git log --oneline origin/main..origin/docs/collaboration-guide
git diff --stat origin/main...origin/docs/collaboration-guide
git diff origin/main...origin/docs/collaboration-guide -- scripts/launcher.ps1
```

第一条列出该分支独有提交，第二条概览自共同起点以来的改动，第三条查看指定文件。也可在 GitHub 的 PR 的 Files changed 中查看。两个点和三个点的含义依命令而异，不要把这些写法随意互换。

### 哪些操作需要团队协调

普通成员可以创建自己的任务分支、提交、推送并发起 PR。修改默认分支、重命名或删除共享分支、改动部署入口、数据库迁移及发布版本时，应按项目职责与维护者协调。main 的评审和合并遵循项目协作规范。

## 17 日常操作速查

### 开始一项新任务

工作区干净、本地已有 main 时执行：

```powershell
git fetch origin --prune
git switch main
git pull --ff-only origin main
git switch -c feat/search-filter
```

### 第二天继续同一项任务

工作区干净、任务分支已设置上游时执行：

```powershell
git switch feat/search-filter
git pull --ff-only
git fetch origin
git merge origin/main
```

然后继续修改，选择文件 add，检查暂存内容，commit，push。最后两条用于同步主线，按任务需要执行；出现冲突先处理，不要继续粘贴后续命令。

### 操作前的最小检查

```powershell
git status -sb
git branch -vv
git remote -v
```

确认自己位于正确仓库、正确分支，当前修改已妥善保存，上游指向预期目标，再继续拉取、合并或推送。
