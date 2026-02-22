<template>
  <div class="p-6 bg-gray-50 min-h-screen">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-800">⚖️ 智能文档比对 (Intelligent Comparison)</h1>
      <p class="text-gray-500 text-sm mt-1">选择 2-5 个文档，AI 将为您生成深度对比报告。</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
      
      <!-- Left: File Selection -->
      <div class="lg:col-span-1 bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col">
        <h3 class="text-lg font-semibold mb-4 text-gray-700 flex items-center justify-between">
            <span>📂 挑选文档</span>
            <span class="text-xs font-normal bg-blue-50 text-blue-600 px-2 py-1 rounded-full">已选 {{ selectedFiles.length }} 项</span>
        </h3>
        
        <div class="flex-1 overflow-hidden relative">
             <FileManager 
                ref="fileManager" 
                :is-selection-mode="true"
                :selected-files="selectedFiles"
                @update:selected-files="handleSelectionUpdate"
             />
        </div>

        <div class="mt-4 pt-4 border-t border-gray-100">
             <button 
                @click="startComparison"
                :disabled="isLoading || selectedFiles.length < 2 || selectedFiles.length > 5"
                class="w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                :class="canCompare ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md transform hover:-translate-y-0.5' : 'bg-gray-100 text-gray-400 cursor-not-allowed'"
             >
                <Loader2 v-if="isLoading" class="animate-spin" :size="20" />
                <Sparkles v-else :size="20" />
                <span>{{ isLoading ? '正在深度分析...' : '开始智能比对' }}</span>
             </button>
             <p v-if="selectedFiles.length === 1" class="text-xs text-center text-red-400 mt-2">请至少再选择一个文档</p>
        </div>
      </div>

      <!-- Right: Comparison Result -->
      <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-700">📊 对比报告</h3>
            <button v-if="resultMarkdown" @click="copyResult" class="text-sm text-gray-500 hover:text-indigo-600 flex items-center gap-1">
                <Copy :size="14" /> 复制结果
            </button>
        </div>

        <div v-if="!resultMarkdown && !isLoading" class="flex-1 flex flex-col items-center justify-center text-gray-300">
            <Scale :size="64" class="mb-4 opacity-20" />
            <p>请在左侧选择文件并开始比对</p>
        </div>

        <div v-else-if="isLoading" class="flex-1 flex flex-col items-center justify-center text-indigo-500">
             <div class="relative">
                 <div class="w-16 h-16 border-4 border-indigo-100 border-t-indigo-500 rounded-full animate-spin"></div>
                 <div class="absolute inset-0 flex items-center justify-center">
                     <Bot :size="24" class="animate-pulse" />
                 </div>
             </div>
             <p class="mt-4 text-sm font-medium animate-pulse">AI 正在阅读文档并提取关键维度...</p>
        </div>

        <div v-else class="flex-1 overflow-y-auto prose max-w-none pr-2 custom-scrollbar">
            <div v-html="renderedMarkdown"></div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import FileManager from '../components/FileManager.vue'
import axios from 'axios'
import MarkdownIt from 'markdown-it'
import { Sparkles, Loader2, Scale, Copy, Bot } from 'lucide-vue-next'

const fileManager = ref(null)
const selectedFiles = ref([])
const resultMarkdown = ref('')
const isLoading = ref(false)

const md = new MarkdownIt({ html: true, linkify: true, breaks: true })

const canCompare = computed(() => selectedFiles.value.length >= 2 && selectedFiles.value.length <= 5)
const renderedMarkdown = computed(() => resultMarkdown.value ? md.render(resultMarkdown.value) : '')

const handleSelectionUpdate = (newSelection) => {
    selectedFiles.value = newSelection
}

const startComparison = async () => {
    if (!canCompare.value) return
    
    isLoading.value = true
    resultMarkdown.value = ''
    
    try {
        const res = await axios.post('/api/comparison/compare', {
            file_ids: selectedFiles.value
        })
        resultMarkdown.value = res.data.markdown
    } catch (e) {
        console.error("Comparison failed", e)
        alert('比对分析失败: ' + (e.response?.data?.detail || e.message))
    } finally {
        isLoading.value = false
    }
}

const copyResult = () => {
    navigator.clipboard.writeText(resultMarkdown.value)
    alert('已复制到剪贴板')
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #f1f1f1;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

:deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 0.9em;
}
:deep(th), :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 8px 12px;
  text-align: left;
}
:deep(th) {
  background-color: #f8fafc;
  font-weight: 600;
  color: #334155;
}
:deep(td) {
  color: #475569;
}
</style>
