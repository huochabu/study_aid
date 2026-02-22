<template>
  <div class="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden">
    <!-- Header with Decision Stamp -->
    <div class="relative p-6 border-b border-zinc-100 bg-zinc-50/50">
      <div class="flex justify-between items-start">
        <div>
          <h2 class="text-xl font-bold text-zinc-900 flex items-center gap-2">
            <span class="text-2xl">⚖️</span> 
            AI Peer Review Report
          </h2>
          <p class="text-zinc-500 text-sm mt-1">Simulated ICLR/CVPR Academic Review Process</p>
        </div>
        
        <!-- Decision Stamp -->
        <div 
          class="transform rotate-[-12deg] border-4 rounded-lg px-4 py-1 font-black text-xl uppercase tracking-widest opacity-80"
          :class="decisionClass"
        >
          {{ reviewData.decision }}
        </div>
      </div>

      <!-- Overall Score -->
      <div class="mt-4 flex items-baseline gap-2">
        <span class="text-4xl font-bold text-zinc-800">{{ reviewData.overall_score }}</span>
        <span class="text-zinc-400 text-sm">/ 10.0</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-0">
      <!-- Left: Radar Chart -->
      <div class="p-6 border-r border-zinc-100 bg-white flex items-center justify-center">
        <div ref="chartRef" class="w-full h-[300px]"></div>
      </div>

      <!-- Right: Summary & Lists -->
      <div class="p-6 bg-zinc-50/30">
        <div class="mb-6">
          <h3 class="font-semibold text-zinc-900 mb-2">Summary</h3>
          <p class="text-zinc-600 text-sm leading-relaxed">{{ reviewData.summary }}</p>
        </div>

        <div class="space-y-4">
          <div>
            <h4 class="text-xs font-bold text-green-700 uppercase tracking-wider mb-2 flex items-center gap-1">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
              Strengths
            </h4>
            <ul class="text-sm space-y-1">
              <li v-for="(item, i) in reviewData.strengths" :key="i" class="flex gap-2 text-zinc-700">
                <span class="text-green-500">•</span> {{ item }}
              </li>
            </ul>
          </div>
          
          <div>
            <h4 class="text-xs font-bold text-red-700 uppercase tracking-wider mb-2 flex items-center gap-1">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/></svg>
              Weaknesses
            </h4>
            <ul class="text-sm space-y-1">
              <li v-for="(item, i) in reviewData.weaknesses" :key="i" class="flex gap-2 text-zinc-700">
                <span class="text-red-500">•</span> {{ item }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Detailed Critique (Collapsible) -->
    <div class="p-4 border-t border-zinc-200 bg-zinc-50">
      <details class="group">
        <summary class="flex justify-between items-center font-medium cursor-pointer list-none text-zinc-600 hover:text-zinc-900 transition-colors">
          <span>View Detailed Critique</span>
          <span class="transition group-open:rotate-180">
            <svg fill="none" height="24" shape-rendering="geometricPrecision" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" viewBox="0 0 24 24" width="24"><path d="M6 9l6 6 6-6"></path></svg>
          </span>
        </summary>
        <div class="text-zinc-600 text-sm mt-4 prose max-w-none p-4 bg-white rounded border border-zinc-200" v-html="renderMarkdown(reviewData.detailed_critique)">
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt()
const renderMarkdown = (text) => {
  return md.render(text || '')
}

const props = defineProps({
  reviewData: {
    type: Object,
    required: true,
    default: () => ({
      scores: { novelty: 0, methodology: 0, rigor: 0, clarity: 0, impact: 0 },
      decision: 'Pending',
      overall_score: 0,
      summary: 'No review data available.',
      strengths: [],
      weaknesses: [],
      detailed_critique: ''
    })
  }
})

const chartRef = ref(null)
let chartInstance = null

const decisionClass = computed(() => {
  const d = (props.reviewData.decision || '').toLowerCase()
  if (d.includes('reject')) return 'border-red-600 text-red-600 bg-red-50'
  if (d.includes('accept')) return 'border-green-600 text-green-600 bg-green-50'
  return 'border-yellow-600 text-yellow-600 bg-yellow-50'
})

const initChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  
  if(chartInstance) {
      chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartRef.value)
  const scores = props.reviewData.scores || {}
  
  const option = {
    radar: {
      indicator: [
        { name: 'Novelty\n(创新性)', max: 10 },
        { name: 'Methodology\n(方法论)', max: 10 },
        { name: 'Rigor\n(严谨性)', max: 10 },
        { name: 'Clarity\n(清晰度)', max: 10 },
        { name: 'Impact\n(应用价值)', max: 10 }
      ],
      shape: 'circle',
      splitNumber: 5,
      axisName: {
        color: '#666',
        fontSize: 10
      },
      splitArea: {
        areaStyle: {
          color: ['#f8f9fa', '#f1f3f5', '#e9ecef', '#dee2e6'],
          shadowColor: 'rgba(0, 0, 0, 0.1)',
          shadowBlur: 10
        }
      }
    },
    series: [
      {
        name: 'Review Scores',
        type: 'radar',
        data: [
          {
            value: [
              scores.novelty || 0,
              scores.methodology || 0,
              scores.rigor || 0,
              scores.clarity || 0,
              scores.impact || 0
            ],
            name: 'Paper Score',
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: '#3b82f6' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(59, 130, 246, 0.5)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
              ])
            }
          }
        ]
      }
    ]
  }
  
  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})

watch(() => props.reviewData, () => {
  initChart()
}, { deep: true })

</script>
