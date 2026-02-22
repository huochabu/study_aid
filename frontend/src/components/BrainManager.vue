<script setup>
import { ref, watch, onMounted } from 'vue'
import { Trash2, AlertCircle, BookOpen, Clock } from 'lucide-vue-next'

const props = defineProps({
  fileId: {
    type: String,
    default: null
  }
})

const rules = ref([])
const loading = ref(false)
const error = ref(null)

const formatDate = (isoString) => {
  if (!isoString) return ''
  return new Date(isoString).toLocaleString()
}

const fetchRules = async () => {
    if (!props.fileId) {
        rules.value = []
        return
    }
    
    loading.value = true
    error.value = null
    try {
        const res = await fetch(`http://localhost:8000/api/rules?file_id=${props.fileId}`)
        if (!res.ok) throw new Error("Failed to fetch rules")
        const data = await res.json()
        rules.value = data.items
    } catch (e) {
        error.value = e.message
    } finally {
        loading.value = false
    }
}

const deleteRule = async (ruleId) => {
    if (!confirm("确定要删除这条记忆吗？删除后 AI 将不再遵守此条修正。")) return
    
    try {
        const res = await fetch(`http://localhost:8000/api/rules/${ruleId}`, {
            method: 'DELETE'
        })
        if (!res.ok) throw new Error("Failed to delete")
        // Remove from list
        rules.value = rules.value.filter(r => r.id !== ruleId)
    } catch (e) {
        alert("删除失败: " + e.message)
    }
}

// Expose refresh method
defineExpose({ refresh: fetchRules })

watch(() => props.fileId, fetchRules, { immediate: true })
</script>

<template>
  <div class="h-full flex flex-col bg-white">
    <!-- Empty State -->
    <div v-if="!fileId" class="flex-1 flex flex-col items-center justify-center text-zinc-400">
        <BookOpen :size="48" class="mb-2 opacity-20" />
        <span>请先上传或选择一个文档</span>
    </div>

    <div v-else-if="loading && rules.length === 0" class="flex-1 flex items-center justify-center text-zinc-400">
        <span>加载中...</span>
    </div>

    <div v-else-if="rules.length === 0" class="flex-1 flex flex-col items-center justify-center text-zinc-400 px-6 text-center">
        <BookOpen :size="48" class="mb-2 opacity-20" />
        <p>暂无修正记忆</p>
        <p class="text-xs mt-2 opacity-75">当您在该文档的问答中纠正 AI ("不对，应该是X") 时，新规则会出现在这里。</p>
    </div>

    <!-- Rule List -->
    <div v-else class="flex-1 overflow-y-auto p-4 space-y-3">
        <div v-for="rule in rules" :key="rule.id" 
             class="group relative bg-white border border-zinc-200 rounded-xl p-4 hover:shadow-md transition-shadow">
             
             <!-- Delete Button -->
             <button @click="deleteRule(rule.id)" 
                     class="absolute top-3 right-3 text-zinc-300 hover:text-red-500 transition-colors p-1">
                 <Trash2 :size="16" />
             </button>

             <div class="pr-8">
                 <div class="flex items-start gap-2 mb-2">
                     <span class="px-2 py-0.5 rounded textxs font-medium bg-zinc-100 text-zinc-600 shrink-0">
                         触发点
                     </span>
                     <p class="text-sm font-medium text-zinc-900 line-clamp-2">{{ rule.question }}</p>
                 </div>
                 
                 <div class="flex items-start gap-2">
                     <span class="px-2 py-0.5 rounded textxs font-medium bg-purple-50 text-purple-700 shrink-0">
                         记忆修正
                     </span>
                     <p class="text-sm text-zinc-600 whitespace-pre-wrap">{{ rule.correction }}</p>
                 </div>
             </div>

             <div class="mt-3 flex items-center gap-1 text-[10px] text-zinc-400">
                 <Clock :size="10" />
                 <span>{{ formatDate(rule.created_at) }}</span>
             </div>
        </div>
    </div>
  </div>
</template>
