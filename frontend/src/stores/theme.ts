import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'classic' | 'mist' | 'sand' | 'dusk'

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref<Theme>((localStorage.getItem('bookpath_theme') as Theme) || 'classic')

  function applyTheme(theme: Theme) {
    document.documentElement.classList.remove('theme-classic', 'theme-mist', 'theme-sand', 'theme-dusk')
    if (theme !== 'classic') {
      document.documentElement.classList.add(`theme-${theme}`)
    }
  }

  watch(currentTheme, (newTheme) => {
    localStorage.setItem('bookpath_theme', newTheme)
    applyTheme(newTheme)
  }, { immediate: true })

  function setTheme(theme: Theme) {
    currentTheme.value = theme
  }

  return { currentTheme, setTheme }
})
