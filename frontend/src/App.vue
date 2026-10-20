<template>
    <router-view />
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
useThemeStore()
</script>