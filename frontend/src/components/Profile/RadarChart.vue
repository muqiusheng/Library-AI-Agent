<template>
  <div class="h-[300px] w-full">
    <v-chart class="h-full w-full" :option="option" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { ProfileMemoryData } from '@/types/profile'

use([CanvasRenderer, RadarChart, TooltipComponent])

const props = defineProps<{
  memories: ProfileMemoryData[]
}>()

const option = computed(() => {
  let foundation = 50
  let engineering = 30
  let theory = 40
  let breadth = 30
  let activity = Math.min(100, 30 + props.memories.length * 10)

  props.memories.forEach(m => {
    const valStr = JSON.stringify(m.value_json)
    if (m.category === 'foundation') foundation += 15
    if (m.category === 'interest') breadth += 15
    if (m.category === 'achievement') {
      if (valStr.includes('项目') || valStr.includes('实践')) engineering += 20
      if (valStr.includes('基础') || valStr.includes('原理') || valStr.includes('理论')) theory += 20
    }
  })

  return {
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator: [
        { name: '理论基础', max: 100 },
        { name: '工程实践', max: 100 },
        { name: '专业广度', max: 100 },
        { name: '进阶探索', max: 100 },
        { name: '学习活跃度', max: 100 }
      ],
      axisName: {
        color: '#14283d',
        fontSize: 12,
        fontWeight: 500
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(140, 155, 145, 0.05)', 'rgba(140, 155, 145, 0.1)']
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(20, 40, 61, 0.1)'
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(20, 40, 61, 0.1)'
        }
      }
    },
    series: [
      {
        name: '能力图谱',
        type: 'radar',
        data: [
          {
            value: [
              Math.min(100, foundation),
              Math.min(100, engineering),
              Math.min(100, breadth),
              Math.min(100, theory),
              Math.min(100, activity)
            ],
            name: '当前画像',
            itemStyle: {
              color: '#8c9b91'
            },
            areaStyle: {
              color: 'rgba(140, 155, 145, 0.4)'
            },
            lineStyle: {
              width: 2,
              color: '#8c9b91'
            }
          }
        ]
      }
    ]
  }
})
</script>
