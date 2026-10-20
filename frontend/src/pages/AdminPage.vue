<template>
  <main
    class="min-h-screen bg-[#f3f6fa] text-slate-700 lg:grid lg:grid-cols-[230px_minmax(0,1fr)]"
  >
    <aside
      class="bg-[#18243a] text-white lg:fixed lg:inset-y-0 lg:left-0 lg:w-[230px]"
    >
      <div class="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <span
          class="grid h-9 w-9 place-items-center rounded-lg bg-blue-500 font-bold"
          >B</span
        >
        <div>
          <p class="font-semibold">BookPath Admin</p>
          <p class="text-[10px] text-white/40">智慧图书管理平台</p>
        </div>
      </div>
      <nav class="flex gap-1 overflow-x-auto p-3 lg:block lg:space-y-1">
        <button
          v-for="item in navigation"
          v-show="item.id !== 'users' || auth.isSuperAdmin"
          :key="item.id"
          class="nav-item"
          :class="section === item.id && 'nav-active'"
          @click="selectSection(item.id)"
        >
          <span class="w-5 text-center">{{ item.icon }}</span
          ><span>{{ item.label }}</span>
        </button>
      </nav>
      <div
        class="hidden border-t border-white/10 px-5 py-4 text-xs text-white/35 lg:absolute lg:inset-x-0 lg:bottom-0 lg:block"
      >
        BookPath AI · P1 管理端
      </div>
    </aside>

    <section class="min-w-0 lg:col-start-2">
      <header
        class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-sm sm:px-6"
      >
        <div>
          <p class="text-xs text-slate-400">后台管理 / {{ currentLabel }}</p>
          <h1 class="mt-0.5 font-semibold text-slate-800">
            {{ currentLabel }}
          </h1>
        </div>
        <div class="flex items-center gap-3">
          <div class="hidden text-right sm:block">
            <p class="text-sm font-medium text-slate-700">
              {{ auth.user?.display_name || auth.user?.student_no }}
            </p>
            <p class="text-[10px] text-slate-400">
              {{ auth.isSuperAdmin ? "超级管理员" : "普通管理员" }}
            </p>
          </div>
          <span
            class="grid h-9 w-9 place-items-center rounded-full bg-blue-50 text-sm font-bold text-blue-600"
            >管</span
          ><button
            class="text-xs text-slate-500 hover:text-red-600"
            @click="signOut"
          >
            退出
          </button>
        </div>
      </header>

      <div class="p-4 sm:p-6">
        <section v-if="section === 'dashboard'" class="space-y-6">
          <div
            class="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white shadow-sm"
          >
            <p class="text-sm text-white/70">欢迎进入 BookPath 管理后台</p>
            <h2 class="mt-2 text-2xl font-semibold">
              馆藏数据与 AI 标签统一管理
            </h2>
            <p class="mt-2 text-sm text-white/65">
              新版本在清洗、标签和索引全部成功后才会发布，不影响当前线上馆藏。
            </p>
          </div>
          <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <article
              v-for="card in dashboardCards"
              :key="card.label"
              class="rounded-lg border border-slate-100 bg-white p-5 shadow-sm"
            >
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-400">{{ card.label }}</span
                ><span
                  class="grid h-9 w-9 place-items-center rounded-lg"
                  :class="card.color"
                  >{{ card.icon }}</span
                >
              </div>
              <p class="mt-4 text-3xl font-semibold text-slate-800">
                {{ card.value }}
              </p>
              <p class="mt-1 text-xs text-slate-400">{{ card.caption }}</p>
            </article>
          </div>
          <div class="grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
            <article
              class="rounded-lg border border-slate-100 bg-white shadow-sm"
            >
              <div
                class="border-b border-slate-100 px-5 py-4 font-medium text-slate-800"
              >
                最近导入批次
              </div>
              <div class="divide-y divide-slate-100">
                <div
                  v-for="item in imports.slice(0, 5)"
                  :key="item.id"
                  class="flex items-center justify-between gap-4 px-5 py-4"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium">
                      {{ item.file_name }}
                    </p>
                    <p class="mt-1 text-xs text-slate-400">
                      {{ item.stage }} · {{ formatDate(item.created_at) }}
                    </p>
                  </div>
                  <span class="status" :class="`status-${item.status}`">{{
                    statusText(item.status)
                  }}</span>
                </div>
                <p
                  v-if="!imports.length"
                  class="p-8 text-center text-sm text-slate-400"
                >
                  暂无导入记录
                </p>
              </div>
            </article>
            <article
              class="rounded-lg border border-slate-100 bg-white p-5 shadow-sm"
            >
              <div class="flex items-center justify-between">
                <h3 class="font-medium text-slate-800">快捷操作</h3>
                <span
                  class="status"
                  :class="
                    aiProvider?.configured
                      ? 'status-succeeded'
                      : 'status-failed'
                  "
                  >{{ aiProvider?.provider ?? "模型 API" }} ·
                  {{ aiProvider?.configured ? "可用" : "未配置" }}</span
                >
              </div>
              <div class="mt-4 grid gap-3">
                <button class="quick" @click="section = 'imports'">
                  上传新版馆藏 <span>→</span></button
                ><button class="quick" @click="selectSection('tags')">
                  审核 AI 标签 <span>→</span></button
                ><button class="quick" @click="selectSection('api')">
                  管理模型 API <span>→</span>
                </button>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="section === 'imports'" class="space-y-5">
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>上传新版馆藏</h2>
                <p>仅接受 XLSX；上传后在后台安全清洗并生成草稿版本。</p>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-3 p-5">
              <input
                ref="fileInput"
                accept=".xlsx"
                class="text-sm"
                type="file"
              /><button class="primary" :disabled="busy" @click="upload">
                {{ busy ? "处理中…" : "上传并校验" }}</button
              ><span v-if="message" class="text-sm text-emerald-600">{{
                message
              }}</span>
            </div>
          </article>
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>导入批次</h2>
                <p>自动每 3 秒刷新运行状态。</p>
              </div>
              <button class="link" @click="loadImports">刷新</button>
            </div>
            <div class="overflow-x-auto">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>文件名称</th>
                    <th>状态</th>
                    <th>处理阶段</th>
                    <th>进度</th>
                    <th>统计 / 错误</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in imports" :key="item.id">
                    <td class="font-medium text-slate-700">
                      {{ item.file_name }}
                    </td>
                    <td>
                      <span class="status" :class="`status-${item.status}`">{{
                        statusText(item.status)
                      }}</span>
                    </td>
                    <td>{{ item.stage }}</td>
                    <td class="w-40">
                      <div class="h-2 rounded bg-slate-100">
                        <div
                          class="h-2 rounded bg-blue-500"
                          :style="{ width: `${item.progress}%` }"
                        />
                      </div>
                      <span class="text-[10px] text-slate-400"
                        >{{ Math.round(item.progress) }}%</span
                      >
                    </td>
                    <td class="max-w-sm truncate text-xs text-slate-400">
                      {{ item.error_summary || statsText(item.statistics) }}
                    </td>
                    <td>
                      <button class="link mr-3" @click="showIssues(item.id)">
                        异常报告</button
                      ><button
                        v-if="
                          item.status === 'succeeded' &&
                          item.stage === 'ready_to_publish'
                        "
                        class="link text-emerald-600"
                        @click="publish(item.id)"
                      >
                        发布
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
          <article v-if="issues.length" class="panel">
            <div class="panel-title">
              <div>
                <h2>异常报告</h2>
                <p>展示前 100 条数据问题样例。</p>
              </div>
            </div>
            <div class="max-h-80 divide-y divide-slate-100 overflow-auto px-5">
              <p v-for="issue in issues" :key="issue.id" class="py-3 text-xs">
                第 {{ issue.row_no ?? "-" }} 行 ·
                <strong>{{ issue.field_name }}</strong> ·
                {{ issue.description }}
                <span class="text-slate-400">{{ issue.raw_value }}</span>
              </p>
            </div>
          </article>
        </section>

        <section v-else-if="section === 'tags'" class="space-y-5">
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>{{ aiProvider?.provider ?? "AI" }} 批量标签</h2>
                <p>
                  按书目内容缓存，不会按馆藏副本重复调用；模型近义枚举会自动标准化。
                </p>
              </div>
              <button class="primary" :disabled="busy" @click="generateTags">
                {{ tagGenerationRunning ? "正在生成…" : "生成 50 本待审标签" }}
              </button>
            </div>
            <div
              v-if="tagGenerationRunning"
              class="px-5 pb-4"
              aria-live="polite"
            >
              <div
                class="tag-progress-track"
                role="progressbar"
                aria-label="AI 标签生成进度"
                aria-valuetext="正在分批生成并保存标签"
              >
                <div class="tag-progress-indicator" />
              </div>
              <p class="mt-2 text-xs text-blue-600">
                正在调用模型并分批保存标签，请勿关闭此页面。
              </p>
            </div>
            <p
              v-if="message"
              class="px-5 pb-4 text-sm"
              :class="messageIsError ? 'text-red-600' : 'text-emerald-600'"
            >
              {{ message }}
            </p>
          </article>
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>待审核标签</h2>
                <p>共 {{ reviews.length }} 条，所有审核操作记录管理员身份。</p>
              </div>
              <div>
                <button
                  class="link mr-4 text-emerald-600"
                  @click="bulk('approved')"
                >
                  批量通过</button
                ><button class="link text-red-600" @click="bulk('rejected')">
                  批量拒绝
                </button>
              </div>
            </div>
            <div class="overflow-x-auto">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th><input type="checkbox" @change="toggleAll" /></th>
                    <th>图书</th>
                    <th>类型</th>
                    <th>标签值</th>
                    <th>置信度</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in reviews" :key="item.id">
                    <td>
                      <input
                        v-model="selected"
                        :value="item.id"
                        type="checkbox"
                      />
                    </td>
                    <td>
                      <p class="max-w-xs truncate font-medium text-slate-700">
                        {{ item.book_title }}
                      </p>
                      <p class="text-[10px] text-slate-400">
                        {{ item.model_name }}
                      </p>
                    </td>
                    <td>
                      <select v-model="item.tag_type" class="field">
                        <option value="topic">主题</option>
                        <option value="difficulty">难度</option>
                        <option value="learning_stage">阶段</option>
                        <option value="content_style">风格</option>
                      </select>
                    </td>
                    <td><input v-model="item.tag_value" class="field" /></td>
                    <td>{{ Math.round(item.confidence * 100) }}%</td>
                    <td>
                      <button class="link" @click="saveTag(item)">
                        保存修改
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p
                v-if="!reviews.length"
                class="p-10 text-center text-sm text-slate-400"
              >
                暂无待审核标签
              </p>
            </div>
          </article>
        </section>
        <section v-else-if="section === 'evaluations'" class="space-y-5">
          <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <article
              v-for="(value, key) in evaluationMetrics"
              :key="key"
              class="rounded-lg bg-white p-5 shadow-sm"
            >
              <p class="text-xs text-slate-400">{{ value.label }}</p>
              <p class="mt-3 text-3xl font-semibold text-slate-800">
                {{ value.score.toFixed(2) }}
              </p>
              <p class="mt-1 text-xs text-slate-400">满分 5 分</p>
            </article>
          </div>
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>人工推荐评测</h2>
                <p>
                  当前样本量
                  {{
                    evaluationSummary?.sample_size ?? 0
                  }}，小样本结果不宣称为普遍准确率。
                </p>
              </div>
            </div>
            <div class="grid gap-6 p-5 lg:grid-cols-2">
              <div>
                <h3 class="text-sm font-medium text-slate-700">满意度分布</h3>
                <div class="mt-4 space-y-3">
                  <div
                    v-for="score in 5"
                    :key="score"
                    class="grid grid-cols-[40px_1fr_40px] items-center gap-3 text-xs"
                  >
                    <span>{{ score }} 分</span>
                    <div class="h-2 rounded bg-slate-100">
                      <div
                        class="h-2 rounded bg-blue-500"
                        :style="{ width: distributionWidth(score) }"
                      />
                    </div>
                    <span>{{
                      evaluationSummary?.satisfaction_distribution[
                        String(score)
                      ] ?? 0
                    }}</span>
                  </div>
                </div>
              </div>
              <div>
                <h3 class="text-sm font-medium text-slate-700">画像场景样本</h3>
                <div class="mt-3 divide-y divide-slate-100">
                  <p
                    v-for="(
                      count, scenario
                    ) in evaluationSummary?.scenario_counts"
                    :key="scenario"
                    class="flex justify-between gap-3 py-2 text-xs"
                  >
                    <span>{{ scenario }}</span
                    ><strong>{{ count }}</strong>
                  </p>
                  <p
                    v-if="
                      !Object.keys(evaluationSummary?.scenario_counts ?? {})
                        .length
                    "
                    class="py-8 text-center text-xs text-slate-400"
                  >
                    暂无评测样本
                  </p>
                </div>
              </div>
            </div>
          </article>
        </section>
        <section v-else-if="section === 'users'" class="space-y-5">
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>注册邀请码</h2>
                <p>全站只使用一个固定邀请码；重新生成后，旧邀请码立即失效。</p>
              </div>
              <button class="primary" :disabled="busy" @click="generateInvite">
                {{ inviteStatus?.configured ? "重新生成" : "生成邀请码" }}
              </button>
            </div>
            <div class="p-5">
              <p class="text-sm text-slate-500">
                状态：
                <strong
                  :class="
                    inviteStatus?.configured
                      ? 'text-emerald-600'
                      : 'text-amber-600'
                  "
                >{{ inviteStatus?.configured ? "已启用" : "尚未生成" }}</strong>
              </p>
              <div
                v-if="generatedInviteCode"
                class="mt-4 rounded-md border border-blue-200 bg-blue-50 p-4"
              >
                <p class="text-xs text-blue-600">
                  邀请码只在本次生成后显示，请立即安全保存。
                </p>
                <div class="mt-2 flex flex-wrap items-center gap-3">
                  <code
                    class="rounded bg-white px-3 py-2 text-lg font-semibold tracking-widest text-slate-800"
                    >{{ generatedInviteCode }}</code
                  >
                  <button class="link" @click="copyInvite">复制邀请码</button>
                </div>
              </div>
            </div>
          </article>
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>新增普通管理员</h2>
                <p>
                  新建账号默认为普通管理员，可使用业务后台，但不能进入用户管理。
                </p>
              </div>
              <button
                class="primary"
                :disabled="busy"
                @click="createAdminAccount"
              >
                创建管理员
              </button>
            </div>
            <div class="grid gap-4 p-5 md:grid-cols-3">
              <label
                ><span class="setting-label">管理员账号</span
                ><input
                  v-model="adminForm.student_no"
                  class="setting-input"
                  placeholder="至少 4 位字母或数字" /></label
              ><label
                ><span class="setting-label">显示名称</span
                ><input
                  v-model="adminForm.display_name"
                  class="setting-input"
                  placeholder="例如：馆藏管理员" /></label
              ><label
                ><span class="setting-label">初始密码</span
                ><input
                  v-model="adminForm.password"
                  class="setting-input"
                  placeholder="8–16 位"
                  type="password"
              /></label>
            </div>
            <p
              v-if="message"
              class="px-5 pb-5 text-sm"
              :class="messageIsError ? 'text-red-600' : 'text-emerald-600'"
            >
              {{ message }}
            </p>
          </article>
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>用户管理</h2>
                <p>
                  共 {{ managedUsers.length }} 个账号；超级管理员账号受保护。
                </p>
              </div>
              <form class="flex gap-2" @submit.prevent="loadManagedUsers">
                <input
                  v-model="userQuery"
                  class="field"
                  placeholder="搜索账号或姓名"
                /><button class="link" type="submit">查询</button>
              </form>
            </div>
            <div class="overflow-x-auto">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>账号</th>
                    <th>姓名 / 专业</th>
                    <th>角色</th>
                    <th>状态</th>
                    <th>最后登录</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in managedUsers" :key="item.id">
                    <td>
                      <p class="font-medium text-slate-700">
                        {{ item.student_no }}
                      </p>
                      <p class="text-[10px] text-slate-400">
                        {{ formatDate(item.created_at) }}
                      </p>
                    </td>
                    <td>
                      {{ item.display_name || "—" }}
                      <p class="text-[10px] text-slate-400">
                        {{ item.major || "未填写画像" }}
                      </p>
                    </td>
                    <td>
                      <span
                        v-if="item.role === 'super_admin'"
                        class="status status-running"
                        >超级管理员</span
                      ><select
                        v-else
                        class="field"
                        :value="item.role"
                        @change="changeUserRole(item, $event)"
                      >
                        <option value="student">学生</option>
                        <option value="admin">普通管理员</option>
                      </select>
                    </td>
                    <td>
                      <span
                        class="status"
                        :class="
                          item.is_active ? 'status-succeeded' : 'status-failed'
                        "
                        >{{ item.is_active ? "启用" : "停用" }}</span
                      >
                    </td>
                    <td>
                      {{
                        item.last_login_at
                          ? formatDate(item.last_login_at)
                          : "从未登录"
                      }}
                    </td>
                    <td>
                      <button
                        v-if="item.role !== 'super_admin'"
                        class="link mr-3"
                        @click="toggleUser(item)"
                      >
                        {{ item.is_active ? "停用" : "启用" }}</button
                      ><button
                        class="link"
                        @click="startPasswordReset(item.id)"
                      >
                        重置密码
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p
                v-if="!managedUsers.length"
                class="p-10 text-center text-sm text-slate-400"
              >
                没有匹配用户
              </p>
            </div>
            <div
              v-if="resetUserId"
              class="flex flex-wrap items-end gap-3 border-t border-slate-100 p-5"
            >
              <label class="min-w-64"
                ><span class="setting-label">输入新密码</span
                ><input
                  v-model="resetPasswordValue"
                  class="setting-input"
                  placeholder="8–16 位"
                  type="password" /></label
              ><button class="primary" @click="confirmPasswordReset">
                确认重置</button
              ><button class="link" @click="resetUserId = null">取消</button>
            </div>
          </article>
        </section>
        <section v-else-if="section === 'api'" class="space-y-5">
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>模型 API 管理</h2>
                <p>
                  选择国内常用平台会自动填写兼容地址和推荐模型，也可使用自定义
                  OpenAI 兼容接口。
                </p>
              </div>
              <span
                class="status"
                :class="
                  aiProvider?.configured ? 'status-succeeded' : 'status-failed'
                "
                >{{ aiProvider?.configured ? "已配置" : "未配置" }}</span
              >
            </div>
            <div class="grid gap-5 p-5 lg:grid-cols-2">
              <label
                ><span class="setting-label">模型平台</span
                ><select
                  v-model="aiConfig.provider_id"
                  class="setting-input"
                  @change="applyProviderPreset"
                >
                  <option
                    v-for="item in providerPresets"
                    :key="item.id"
                    :value="item.id"
                  >
                    {{ item.name }}
                  </option></select
                ><small>{{ selectedProvider.help }}</small></label
              ><label
                ><span class="setting-label">API Key</span
                ><input
                  v-model="aiConfig.api_key"
                  autocomplete="new-password"
                  class="setting-input"
                  placeholder="已配置时留空表示不修改"
                  type="password"
                /><small>{{
                  aiProvider?.configured
                    ? "密钥已保存；输入新值可替换"
                    : "请粘贴平台控制台创建的 API Key"
                }}</small></label
              ><label
                ><span class="setting-label">API 地址</span
                ><input
                  v-model="aiConfig.base_url"
                  class="setting-input" /></label
              ><label
                ><span class="setting-label">对话模型</span
                ><input
                  v-model="aiConfig.chat_model"
                  class="setting-input" /></label
              ><label
                ><span class="setting-label">推理模型</span
                ><input
                  v-model="aiConfig.reasoning_model"
                  class="setting-input" /></label
              ><label v-if="aiConfig.provider_id === 'custom'"
                ><span class="setting-label">平台名称</span
                ><input
                  v-model="aiConfig.provider"
                  class="setting-input"
                  placeholder="自定义平台"
              /></label>
            </div>
            <div
              class="mx-5 mb-5 rounded-md border border-blue-100 bg-blue-50 p-4 text-xs leading-6 text-blue-700"
            >
              <strong>配置方法：</strong>进入所选平台的开放平台控制台创建 API
              Key → 粘贴到上方 → 核对 Base URL 和模型名称 → 保存。{{
                selectedProvider.note
              }}
            </div>
            <div
              class="flex items-center gap-3 border-t border-slate-100 px-5 py-4"
            >
              <button class="primary" :disabled="busy" @click="saveAIProvider">
                {{ busy ? "保存中…" : "保存并返回控制台" }}</button
              ><span
                v-if="message"
                class="text-sm"
                :class="messageIsError ? 'text-red-600' : 'text-emerald-600'"
                >{{ message }}</span
              >
            </div>
          </article>
        </section>
        <section v-else class="space-y-5">
          <article class="panel">
            <div class="panel-title">
              <div>
                <h2>业务参数配置</h2>
                <p>
                  调整推荐数量、标签任务和评分权重；模型 API
                  请在独立管理板块配置。
                </p>
              </div>
              <button class="primary" @click="saveSettings">保存配置</button>
            </div>
            <div class="grid gap-5 p-5 lg:grid-cols-3">
              <label
                ><span class="setting-label">每轮推荐数量</span
                ><input
                  v-model.number="settingValues.recommendation_top_k"
                  class="setting-input"
                  max="10"
                  min="1"
                  type="number"
                /><small>允许 1–10 本</small></label
              ><label
                ><span class="setting-label">AI 标签批量数</span
                ><input
                  v-model.number="settingValues.ai_tag_batch_size"
                  class="setting-input"
                  max="100"
                  min="1"
                  type="number"
                /><small>允许 1–100 本</small></label
              ><label
                ><span class="setting-label">模拟预约有效天数</span
                ><input
                  v-model.number="settingValues.reservation_expiry_days"
                  class="setting-input"
                  max="14"
                  min="1"
                  type="number"
                /><small>允许 1–14 天</small></label
              >
            </div>
            <div class="border-t border-slate-100 p-5">
              <h3 class="font-medium text-slate-800">推荐评分权重</h3>
              <p class="mt-1 text-xs text-slate-400">六项总和必须等于 1。</p>
              <div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <label v-for="(label, key) in weightLabels" :key="key"
                  ><span class="setting-label">{{ label }}</span
                  ><input
                    v-model.number="settingValues.recommendation_weights[key]"
                    class="setting-input"
                    max="1"
                    min="0"
                    step="0.05"
                    type="number"
                /></label>
              </div>
            </div>
            <p v-if="message" class="px-5 pb-5 text-sm text-emerald-600">
              {{ message }}
            </p>
          </article>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import {
  bulkReviewTags,
  generateAiTags,
  getAdminOverview,
  getAIProviderStatus,
  listImportIssues,
  listImports,
  listSystemSettings,
  listTagReviews,
  publishImport,
  updateAIProvider,
  updateSystemSettings,
  updateTagReview,
  uploadLibrary,
  type AdminOverviewData,
  type AIProviderStatusData,
  type ImportBatchData,
  type ImportIssueData,
  type TagReviewData,
} from "@/api/admin";
import {
  createManagedAdmin,
  generateRegistrationInvite,
  getRegistrationInviteStatus,
  listManagedUsers,
  resetManagedUserPassword,
  updateManagedUser,
  type ManagedUserData,
  type RegistrationInviteStatusData,
} from "@/api/adminUsers";
import { useAuthStore } from "@/stores/auth";
import {
  getEvaluationSummary,
  type EvaluationSummaryData,
} from "@/api/evaluations";
import { getApiErrorMessage } from "@/utils/apiError";

type Section =
  | "dashboard"
  | "imports"
  | "tags"
  | "evaluations"
  | "users"
  | "api"
  | "settings";
const auth = useAuthStore();
const router = useRouter();
const section = ref<Section>("dashboard");
const overview = ref<AdminOverviewData | null>(null);
const aiProvider = ref<AIProviderStatusData | null>(null);
const evaluationSummary = ref<EvaluationSummaryData | null>(null);
const imports = ref<ImportBatchData[]>([]);
const issues = ref<ImportIssueData[]>([]);
const reviews = ref<TagReviewData[]>([]);
const managedUsers = ref<ManagedUserData[]>([]);
const inviteStatus = ref<RegistrationInviteStatusData | null>(null);
const generatedInviteCode = ref("");
const selected = ref<string[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const busy = ref(false);
const tagGenerationRunning = ref(false);
const message = ref("");
const messageIsError = ref(false);
const userQuery = ref("");
const resetUserId = ref<string | null>(null);
const resetPasswordValue = ref("");
let timer: number | undefined;
const navigation: { id: Section; label: string; icon: string }[] = [
  { id: "dashboard", label: "控制台", icon: "▦" },
  { id: "imports", label: "馆藏数据管理", icon: "⇧" },
  { id: "tags", label: "AI 标签审核", icon: "✓" },
  { id: "evaluations", label: "推荐评测", icon: "评" },
  { id: "users", label: "用户管理", icon: "人" },
  { id: "api", label: "模型 API 管理", icon: "模" },
  { id: "settings", label: "系统参数", icon: "⚙" },
];
const adminForm = reactive({ student_no: "", display_name: "", password: "" });
const settingValues = reactive({
  recommendation_top_k: 5,
  ai_tag_batch_size: 50,
  reservation_expiry_days: 3,
  recommendation_weights: {
    goal: 0.3,
    difficulty: 0.2,
    major: 0.15,
    interest: 0.1,
    semantic: 0.15,
    availability: 0.1,
  },
});
const providerPresets = [
  {
    id: "deepseek",
    name: "DeepSeek",
    base_url: "https://api.deepseek.com",
    chat_model: "deepseek-v4-flash",
    reasoning_model: "deepseek-v4-pro",
    help: "DeepSeek 开放平台",
    note: "V4 模型使用 deepseek-v4-flash / deepseek-v4-pro。",
  },
  {
    id: "ollama",
    name: "Ollama 本地模型",
    base_url: "http://host.docker.internal:11434/v1",
    chat_model: "qwen3:4b-instruct",
    reasoning_model: "qwen3:4b-instruct",
    help: "Ollama OpenAI 兼容接口",
    note: "本机推荐 qwen3:4b-instruct；API Key 使用占位值 ollama。",
  },
  {
    id: "qwen",
    name: "阿里云百炼（通义千问）",
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    chat_model: "qwen-plus",
    reasoning_model: "qwen-plus",
    help: "阿里云百炼控制台",
    note: "使用百炼 API Key；模型可按已开通权限修改。",
  },
  {
    id: "zhipu",
    name: "智谱开放平台（GLM）",
    base_url: "https://open.bigmodel.cn/api/paas/v4",
    chat_model: "glm-5.2",
    reasoning_model: "glm-5.2",
    help: "智谱 BigModel 开放平台",
    note: "使用通用开放平台 Key，不要填写 Coding 套餐专用地址。",
  },
  {
    id: "moonshot",
    name: "Moonshot（月之暗面 Kimi）",
    base_url: "https://api.moonshot.cn/v1",
    chat_model: "moonshot-v1-8k",
    reasoning_model: "moonshot-v1-8k",
    help: "Moonshot 开放平台",
    note: "模型名称可按 Moonshot 控制台当前可用列表修改。",
  },
  {
    id: "custom",
    name: "自定义 OpenAI 兼容平台",
    base_url: "",
    chat_model: "",
    reasoning_model: "",
    help: "任何兼容 Chat Completions 的服务",
    note: "请自行填写平台名称、Base URL 与模型名称。",
  },
];
const aiConfig = reactive({
  provider_id: "deepseek",
  provider: "DeepSeek",
  api_key: "",
  base_url: "https://api.deepseek.com",
  chat_model: "deepseek-v4-flash",
  reasoning_model: "deepseek-v4-pro",
});
const weightLabels = {
  goal: "学习目标",
  difficulty: "难度匹配",
  major: "专业匹配",
  interest: "兴趣偏好",
  semantic: "语义相关",
  availability: "馆藏可用",
};
const currentLabel = computed(
  () => navigation.find((item) => item.id === section.value)?.label ?? "控制台",
);
const selectedProvider = computed(
  () =>
    providerPresets.find((item) => item.id === aiConfig.provider_id) ??
    providerPresets[providerPresets.length - 1],
);
const dashboardCards = computed(() => [
  {
    label: "发布书目",
    value: overview.value?.published_books ?? 0,
    caption: `${overview.value?.published_holdings ?? 0} 个馆藏副本`,
    icon: "书",
    color: "bg-blue-50 text-blue-600",
  },
  {
    label: "注册用户",
    value: overview.value?.users ?? 0,
    caption: `${overview.value?.conversations ?? 0} 个学习会话`,
    icon: "人",
    color: "bg-amber-50 text-amber-600",
  },
  {
    label: "推荐结果",
    value: overview.value?.recommendation_sets ?? 0,
    caption: `${overview.value?.active_reservations ?? 0} 个模拟预约`,
    icon: "荐",
    color: "bg-indigo-50 text-indigo-600",
  },
  {
    label: "待审标签",
    value: overview.value?.pending_tags ?? 0,
    caption: `${overview.value?.evaluation_samples ?? 0} 份人工评测`,
    icon: "签",
    color: "bg-emerald-50 text-emerald-600",
  },
]);
const evaluationMetrics = computed(() => {
  const value = evaluationSummary.value?.averages;
  return {
    relevance: { label: "目标相关性", score: value?.relevance ?? 0 },
    difficulty: { label: "难度匹配", score: value?.difficulty ?? 0 },
    reason: { label: "理由可信度", score: value?.reason ?? 0 },
    holding: { label: "馆藏实用性", score: value?.holding ?? 0 },
    satisfaction: { label: "整体满意度", score: value?.satisfaction ?? 0 },
  };
});
onMounted(async () => {
  await Promise.all([
    loadOverview(),
    loadAIProvider(),
    loadImports(),
    loadTags(),
    loadSettings(),
    loadEvaluations(),
  ]);
  timer = window.setInterval(() => {
    loadImports();
    loadOverview();
  }, 3000);
});
onBeforeUnmount(() => window.clearInterval(timer));
function selectSection(value: Section) {
  section.value = value;
  message.value = "";
  messageIsError.value = false;
  if (value === "tags") loadTags();
  if (value === "evaluations") loadEvaluations();
  if (value === "users" && auth.isSuperAdmin) {
    loadManagedUsers();
    loadInviteStatus();
  }
}
async function loadImports() {
  imports.value = await listImports();
}
async function loadOverview() {
  overview.value = await getAdminOverview();
}
async function loadAIProvider() {
  aiProvider.value = await getAIProviderStatus();
  aiConfig.provider_id = aiProvider.value.provider_id;
  aiConfig.provider = aiProvider.value.provider;
  aiConfig.base_url = aiProvider.value.base_url;
  aiConfig.chat_model = aiProvider.value.chat_model;
  aiConfig.reasoning_model = aiProvider.value.reasoning_model;
}
function applyProviderPreset() {
  const preset = selectedProvider.value;
  if (preset.id === "custom") {
    aiConfig.provider = "自定义平台";
    return;
  }
  aiConfig.provider = preset.name;
  aiConfig.base_url = preset.base_url;
  aiConfig.chat_model = preset.chat_model;
  aiConfig.reasoning_model = preset.reasoning_model;
  aiConfig.api_key = preset.id === "ollama" ? "ollama" : "";
}
async function saveAIProvider() {
  busy.value = true;
  message.value = "";
  messageIsError.value = false;
  try {
    aiProvider.value = await updateAIProvider({
      ...aiConfig,
      api_key: aiConfig.api_key || undefined,
    });
    aiConfig.api_key = "";
    message.value = "AI API 配置已保存并立即生效。";
    section.value = "dashboard";
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "AI API 配置保存失败");
  } finally {
    busy.value = false;
  }
}
async function loadManagedUsers() {
  managedUsers.value = await listManagedUsers(userQuery.value);
}
async function loadInviteStatus() {
  inviteStatus.value = await getRegistrationInviteStatus();
}
async function generateInvite() {
  busy.value = true;
  generatedInviteCode.value = "";
  message.value = "";
  try {
    const result = await generateRegistrationInvite();
    inviteStatus.value = result;
    generatedInviteCode.value = result.code;
    messageIsError.value = false;
    message.value = "新邀请码已生成，旧邀请码已失效。";
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "邀请码生成失败");
  } finally {
    busy.value = false;
  }
}
async function copyInvite() {
  if (!generatedInviteCode.value) return;
  await navigator.clipboard.writeText(generatedInviteCode.value);
  messageIsError.value = false;
  message.value = "邀请码已复制。";
}
async function createAdminAccount() {
  message.value = "";
  messageIsError.value = false;
  if (
    !adminForm.student_no ||
    adminForm.password.length < 8 ||
    adminForm.password.length > 16
  ) {
    messageIsError.value = true;
    message.value = "请填写管理员账号和 8–16 位的初始密码。";
    return;
  }
  busy.value = true;
  try {
    await createManagedAdmin({
      ...adminForm,
      display_name: adminForm.display_name || undefined,
    });
    adminForm.student_no = "";
    adminForm.display_name = "";
    adminForm.password = "";
    message.value = "普通管理员创建成功。";
    await Promise.all([loadManagedUsers(), loadOverview()]);
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "管理员创建失败");
  } finally {
    busy.value = false;
  }
}
async function changeUserRole(item: ManagedUserData, event: Event) {
  const role = (event.target as HTMLSelectElement).value as "student" | "admin";
  try {
    await updateManagedUser(item.id, { role });
    await loadManagedUsers();
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "角色修改失败");
    await loadManagedUsers();
  }
}
async function toggleUser(item: ManagedUserData) {
  try {
    await updateManagedUser(item.id, { is_active: !item.is_active });
    await loadManagedUsers();
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "账号状态修改失败");
  }
}
function startPasswordReset(id: string) {
  resetUserId.value = id;
  resetPasswordValue.value = "";
  message.value = "";
}
async function confirmPasswordReset() {
  if (
    !resetUserId.value ||
    resetPasswordValue.value.length < 8 ||
    resetPasswordValue.value.length > 16
  ) {
    messageIsError.value = true;
    message.value = "新密码需要 8–16 位。";
    return;
  }
  try {
    await resetManagedUserPassword(resetUserId.value, resetPasswordValue.value);
    resetUserId.value = null;
    resetPasswordValue.value = "";
    messageIsError.value = false;
    message.value = "密码已重置。";
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "密码重置失败");
  }
}
async function loadEvaluations() {
  evaluationSummary.value = await getEvaluationSummary();
}
async function loadSettings() {
  const values = await listSystemSettings();
  for (const item of values) {
    if (
      item.key === "recommendation_weights" &&
      typeof item.value === "object" &&
      item.value
    )
      Object.assign(settingValues.recommendation_weights, item.value);
    else if (item.key in settingValues && typeof item.value === "number")
      (settingValues as unknown as Record<string, number>)[item.key] =
        item.value;
  }
}
async function saveSettings() {
  await updateSystemSettings({
    ...settingValues,
    recommendation_weights: { ...settingValues.recommendation_weights },
  });
  message.value = "系统参数已保存并立即生效。";
  await loadOverview();
}
async function upload() {
  const file = fileInput.value?.files?.[0];
  if (!file) {
    message.value = "请先选择 XLSX 文件。";
    return;
  }
  busy.value = true;
  try {
    const result = await uploadLibrary(file);
    message.value = result.duplicate_file
      ? "该文件已存在，已定位到原批次。"
      : "上传成功，后台正在清洗。";
    await loadImports();
  } catch (error) {
    message.value = getApiErrorMessage(error, "上传失败");
  } finally {
    busy.value = false;
  }
}
async function showIssues(id: string) {
  issues.value = await listImportIssues(id);
}
async function publish(id: string) {
  await publishImport(id);
  message.value = "正在生成标签和索引，成功后自动发布。";
  await loadImports();
}
async function loadTags() {
  reviews.value = await listTagReviews();
}
async function generateTags() {
  busy.value = true;
  tagGenerationRunning.value = true;
  message.value = "";
  messageIsError.value = false;
  try {
    const result = await generateAiTags();
    message.value = `生成 ${result.created_tags} 条标签，缓存命中 ${result.cached_books} 本。`;
    await loadTags();
  } catch (error) {
    messageIsError.value = true;
    message.value = getApiErrorMessage(error, "标签生成失败");
  } finally {
    tagGenerationRunning.value = false;
    busy.value = false;
  }
}
async function saveTag(item: TagReviewData) {
  await updateTagReview(item.id, item.tag_type, item.tag_value, "pending");
  message.value = "标签修改已保存。";
}
async function bulk(status: "approved" | "rejected") {
  if (!selected.value.length) return;
  await bulkReviewTags(selected.value, status);
  selected.value = [];
  await loadTags();
}
function toggleAll(event: Event) {
  selected.value = (event.target as HTMLInputElement).checked
    ? reviews.value.map((item) => item.id)
    : [];
}
async function signOut() {
  await auth.logout();
  await router.replace("/login");
}
function statusText(value: string) {
  return (
    (
      {
        pending: "等待",
        running: "处理中",
        succeeded: "成功",
        failed: "失败",
      } as Record<string, string>
    )[value] ?? value
  );
}
function statsText(value: Record<string, unknown>) {
  return Object.keys(value).length
    ? `书目 ${value.books ?? "-"} · 副本 ${value.holdings ?? "-"} · 异常 ${value.issues ?? "-"}`
    : "-";
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}
function distributionWidth(score: number) {
  const total = evaluationSummary.value?.sample_size || 1;
  const count =
    evaluationSummary.value?.satisfaction_distribution[String(score)] || 0;
  return `${(count * 100) / total}%`;
}
</script>

<style scoped>
.nav-item {
  @apply flex min-w-max items-center gap-3 rounded-md px-4 py-3 text-left text-sm text-white/60 transition hover:bg-white/5 hover:text-white lg:w-full;
}
.nav-active {
  @apply bg-blue-600 text-white hover:bg-blue-600;
}
.panel {
  @apply overflow-hidden rounded-lg border border-slate-100 bg-white shadow-sm;
}
.panel-title {
  @apply flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4;
}
.panel-title h2 {
  @apply font-medium text-slate-800;
}
.panel-title p {
  @apply mt-1 text-xs text-slate-400;
}
.primary {
  @apply rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50;
}
.link {
  @apply text-xs font-medium text-blue-600 hover:underline;
}
.quick {
  @apply flex items-center justify-between rounded-md border border-slate-200 px-4 py-3 text-left text-sm hover:border-blue-300 hover:text-blue-600;
}
.admin-table {
  @apply w-full min-w-[850px] text-left text-sm;
}
.admin-table th {
  @apply bg-slate-50 px-4 py-3 text-xs font-medium text-slate-400;
}
.admin-table td {
  @apply border-t border-slate-100 px-4 py-3;
}
.status {
  @apply inline-flex rounded-full px-2.5 py-1 text-[11px];
}
.status-pending {
  @apply bg-slate-100 text-slate-500;
}
.status-running {
  @apply bg-blue-50 text-blue-600;
}
.status-succeeded {
  @apply bg-emerald-50 text-emerald-600;
}
.status-failed {
  @apply bg-red-50 text-red-600;
}
.field {
  @apply min-h-9 rounded-md border border-slate-200 bg-white px-2 text-sm outline-none focus:border-blue-500;
}
.setting-label {
  @apply block text-sm font-medium text-slate-700;
}
.setting-input {
  @apply mt-2 min-h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-blue-500;
}
.setting-input + small {
  @apply mt-1 block text-xs text-slate-400;
}
.tag-progress-track {
  @apply relative h-2 overflow-hidden rounded-full bg-blue-100;
}
.tag-progress-indicator {
  @apply absolute inset-y-0 w-1/3 rounded-full bg-blue-600;
  animation: tag-progress 1.2s ease-in-out infinite;
}
@keyframes tag-progress {
  0% {
    left: -34%;
  }
  100% {
    left: 100%;
  }
}
.api-config {
  @apply rounded-md border border-slate-100 bg-slate-50 p-4;
}
.api-config span {
  @apply block text-xs text-slate-400;
}
.api-config strong {
  @apply mt-2 block text-sm font-medium text-slate-700;
}
</style>
