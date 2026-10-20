<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-semibold text-navy">基本信息</h1>
      <p class="mt-2 text-sm text-black/45">管理您的个人信息和头像。</p>
    </div>
    <div class="rounded-3xl bg-white p-5 shadow-card sm:p-7 max-w-2xl">
      <form @submit.prevent="save">
        <div class="flex items-center gap-6">
          <div class="relative group">
            <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" class="h-24 w-24 rounded-full object-cover border-4 border-paper" />
            <div v-else class="grid h-24 w-24 place-items-center rounded-full bg-paper text-3xl font-bold text-navy/20 border-4 border-white shadow-sm">
              {{ auth.user?.display_name?.[0]?.toUpperCase() || auth.user?.student_no?.[0]?.toUpperCase() }}
            </div>
            <label class="absolute inset-0 flex cursor-pointer items-center justify-center rounded-full bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
              <span class="text-xs font-medium text-white">修改头像</span>
              <input type="file" class="hidden" accept="image/*" @change="onAvatarChange" />
            </label>
          </div>
          <div>
            <h2 class="text-lg font-semibold text-navy">个人头像</h2>
            <p class="text-sm text-black/45 mt-1">支持 JPG、PNG 格式，图片大小不超过 5MB</p>
          </div>
        </div>

        <div class="mt-8 space-y-5">
          <label class="block">
            <span class="block text-sm font-medium text-navy">学号</span>
            <input type="text" class="mt-2 min-h-11 w-full rounded-xl border border-black/10 bg-black/5 px-3 text-sm text-black/50 outline-none cursor-not-allowed" :value="auth.user?.student_no" disabled />
            <p class="mt-2 text-xs text-black/40">学号为系统唯一标识，不可修改。</p>
          </label>
          
          <label class="block">
            <span class="block text-sm font-medium text-navy">姓名 (昵称)</span>
            <input v-model="displayName" type="text" class="mt-2 min-h-11 w-full rounded-xl border border-black/10 bg-white px-3 text-sm outline-none focus:border-navy focus:ring-4 focus:ring-navy/5 transition-all" placeholder="输入您的姓名或昵称" />
          </label>
        </div>

        <div class="mt-8 flex items-center gap-4">
          <button type="submit" class="min-h-11 rounded-xl bg-navy px-6 text-sm font-semibold text-white transition-transform active:scale-95 disabled:opacity-50 disabled:active:scale-100" :disabled="saving">
            {{ saving ? '保存中...' : '保存更改' }}
          </button>
          <p v-if="saved" class="text-sm text-sage transition-opacity duration-300">保存成功！</p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, uploadAvatar } from '@/api/auth'

const auth = useAuthStore()
const displayName = ref('')
const saving = ref(false)
const saved = ref(false)

onMounted(() => {
  displayName.value = auth.user?.display_name || ''
})

async function onAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return
  
  const file = input.files[0]
  
  // Compress image before upload
  const img = new Image()
  img.src = URL.createObjectURL(file)
  await new Promise((resolve) => { img.onload = resolve })
  
  const canvas = document.createElement('canvas')
  const maxSize = 500
  let width = img.width
  let height = img.height
  if (width > height && width > maxSize) {
    height *= maxSize / width
    width = maxSize
  } else if (height > maxSize) {
    width *= maxSize / height
    height = maxSize
  }
  
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx?.drawImage(img, 0, 0, width, height)
  
  canvas.toBlob(async (blob) => {
    if (!blob) return alert('图片处理失败')
    const compressedFile = new File([blob], file.name, { type: 'image/jpeg' })
    
    try {
      const data = await uploadAvatar(compressedFile)
      if (auth.user) {
        auth.user.avatar_url = data.avatar_url
      }
    } catch (err) {
      alert('头像上传失败')
    }
  }, 'image/jpeg', 0.8)
}

async function save() {
  if (saving.value) return
  saving.value = true
  saved.value = false
  
  try {
    const data = await updateProfile({ display_name: displayName.value })
    if (auth.user) {
      auth.user.display_name = data.display_name
    }
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (err) {
    alert('保存失败')
  } finally {
    saving.value = false
  }
}
</script>
