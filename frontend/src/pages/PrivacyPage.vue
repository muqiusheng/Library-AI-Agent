<template>
  <main class="min-h-screen bg-paper px-4 py-10 text-black/70 sm:px-8">
    <article class="mx-auto max-w-3xl rounded-3xl bg-white p-6 shadow-card sm:p-10">
      <RouterLink class="text-sm font-semibold text-navy hover:underline" to="/login">← 返回登录</RouterLink>
      <p class="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-amber">BookPath AI</p>
      <h1 class="mt-2 text-3xl font-semibold text-navy">隐私说明（V1 小范围试用）</h1>
      <p class="mt-2 text-sm text-black/40">更新日期：2026-07-26</p>

      <section v-for="section in sections" :key="section.title" class="mt-8">
        <h2 class="text-lg font-semibold text-navy">{{ section.title }}</h2>
        <p v-for="paragraph in section.paragraphs" :key="paragraph" class="mt-3 leading-7">{{ paragraph }}</p>
      </section>
    </article>
  </main>
</template>

<script setup lang="ts">
const sections = [
  { title: '适用范围', paragraphs: ['当前仅用于个人学习、课程、比赛或非商业小范围试用，不是学校正式信息系统。账号总数限制为 50。'] },
  { title: '保存的信息', paragraphs: ['系统可能保存测试学号或账号、昵称、年级、专业、学习基础、目标与兴趣、课程和已读图书、对话与推荐历史、反馈、模拟预约、通知及必要操作记录。', '测试期间请使用虚拟学号和昵称，不要输入身份证号、手机号、住址、支付信息、健康信息或其他无关敏感个人信息。'] },
  { title: '使用目的', paragraphs: ['信息仅用于登录、学习画像、馆藏推荐、学习路径、模拟预约、系统安全、故障排查和匿名效果评测，不用于广告、交易或向无关第三方出售。'] },
  { title: 'AI 服务', paragraphs: ['系统可能调用管理员配置的第三方大模型。请勿在对话中提交真实姓名、真实学号或不必要的完整个人资料。AI 输出可能存在错误，仅供学习和图书选择参考。'] },
  { title: '安全与备份', paragraphs: ['生产数据保存在家庭服务器中，并采用邀请码、密码哈希、角色权限、请求限流、HTTPS、日志轮转和定期备份。备份不包含明文密码、JWT Secret 或模型 API Key。'] },
  { title: '用户权利', paragraphs: ['试用用户可联系管理员申请查询、更正或删除自己的账号与相关数据，也可以停止使用服务。'] },
  { title: '可用性', paragraphs: ['家庭服务器断电、休眠、断网、系统更新或第三方服务异常时，网站可能暂时不可用。若项目转为正式或商业服务，将重新进行合规和安全评估。'] }
]
</script>
