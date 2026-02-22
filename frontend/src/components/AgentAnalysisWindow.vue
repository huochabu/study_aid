<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { X, Minimize2, Maximize2, Terminal, Bot, User, HardDrive, Cpu, FileText, AlertTriangle, CheckCircle } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
    html: true,
    linkify: true,
    breaks: true
})

const renderMarkdown = (text) => {
    return md.render(text || '')
}

const props = defineProps({
  logs: {
    type: Array, // [{ name: 'AgentName', content: '...', type: 'agent_log', timestamp: 0 }]
    default: () => []
  },
  status: {
    type: String,
    default: 'idle' // idle, analyzing, generating, completed, failed
  },
  progress: {
    type: Number,
    default: 0
  },
  isVisible: {
    type: Boolean,
    default: false
  },
  currentPhase: {
    type: String,
    default: '准备就绪'
  },
  thinkingAgent: {
    type: String,
    default: null
  },
  filename: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'minimize'])

const isMinimized = ref(false)
const scrollContainer = ref(null)

// Auto-scroll to bottom when logs change
watch(() => props.logs.length, () => {
    if (!isMinimized.value) {
        scrollToBottom()
    }
})

const scrollToBottom = () => {
    nextTick(() => {
        if (scrollContainer.value) {
            scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
        }
    })
}

// Watch thinking agent change to scroll
watch(() => props.thinkingAgent, (val) => {
    if (val && !isMinimized.value) {
        scrollToBottom()
    }
})

// [FIX] Watch status change to scroll (e.g. when completed)
watch(() => props.status, (val) => {
    if (val === 'completed' && !isMinimized.value) {
        scrollToBottom()
    }
})

// Map agent names to icons/colors
const getAgentIcon = (name) => {
    if (!name) return Bot
    if (name.includes('用户') || name.includes('User')) return User
    if (name.includes('日志')) return Terminal
    if (name.includes('配置')) return HardDrive
    if (name.includes('学术')) return FileText
    return Bot
}

const getAgentColor = (name) => {
    if (!name) return 'bg-zinc-100 text-zinc-600'
    if (name.includes('日志')) return 'bg-amber-100 text-amber-700'
    if (name.includes('配置')) return 'bg-cyan-100 text-cyan-700'
    if (name.includes('学术')) return 'bg-purple-100 text-purple-700'
    if (name.includes('解释')) return 'bg-emerald-100 text-emerald-700'
    return 'bg-blue-100 text-blue-700'
}

</script>

<template>
  <div 
    v-if="isVisible"
    class="fixed top-20 right-6 w-[500px] bg-white rounded-xl shadow-2xl border border-zinc-200 z-50 flex flex-col overflow-hidden transition-all duration-300"
    :class="{ 'h-14': isMinimized, 'h-[600px]': !isMinimized }"
  >
    <!-- Header -->
    <div 
        class="h-14 bg-gradient-to-r from-zinc-900 to-zinc-800 text-white flex items-center justify-between px-4 shrink-0 cursor-pointer"
        @click="isMinimized = !isMinimized"
    >
        <div class="flex items-center gap-2">
            <div class="relative">
                  <div v-if="status === 'analyzing' || status === 'generating'" class="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-pulse border border-zinc-900"></div>
                  <div v-if="status === 'completed'" class="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full border border-zinc-900"></div>
                  <div v-if="status === 'failed'" class="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border border-zinc-900"></div>
                  <Cpu :size="18" />
            </div>
            
            <div class="flex flex-col">
                <span class="text-sm font-medium truncate max-w-[200px]" :title="filename ? `多智能体分析中台 - ${filename}` : '多智能体分析中台'">
                    多智能体分析中台 <span v-if="filename" class="opacity-80 font-normal">- {{ filename }}</span>
                </span>
                <span v-if="!isMinimized" class="text-[10px] text-zinc-400">{{ currentPhase }} ({{ progress }}%)</span>
            </div>
        </div>
        
        <div class="flex items-center gap-2" @click.stop>
             <button @click="isMinimized = !isMinimized" class="p-1 hover:bg-white/10 rounded">
                <Minimize2 v-if="!isMinimized" :size="14" />
                <Maximize2 v-else :size="14" />
             </button>
             <button @click="$emit('close')" class="p-1 hover:bg-red-500/80 rounded">
                <X :size="14" />
             </button>
        </div>
    </div>

    <!-- Progress Bar (Visible even when minimized if needed, but here only expanded) -->
    <div v-if="!isMinimized" class="h-1 bg-zinc-100 w-full shrink-0">
        <div 
            class="h-full transition-all duration-500" 
            :class="status === 'failed' ? 'bg-red-500' : 'bg-blue-600'"
            :style="{ width: progress + '%' }"
        ></div>
    </div>

    <!-- Content -->
    <div v-if="!isMinimized" class="flex-1 bg-zinc-50/50 p-4 overflow-y-auto space-y-4 font-mono text-sm" ref="scrollContainer">
        
        <div v-if="logs.length === 0 && !thinkingAgent" class="text-center text-zinc-400 py-10">
            <div v-if="status === 'failed'" class="flex flex-col items-center text-red-500/80">
                 <AlertTriangle :size="32" class="mb-2" />
                 <p class="font-medium">分析启动失败</p>
                 <p class="text-xs mt-1 text-zinc-500">请查看上方的错误提示信息</p>
            </div>
            <div v-else>
                <div class="animate-spin mb-2 inline-block">
                    <Cpu :size="24" />
                </div>
                <p>等待智能体接入...</p>
            </div>
        </div>

        <div v-for="(log, idx) in logs" :key="idx" class="animate-fade-in-up">
            <!-- System/Status Messages -->
            <div v-if="log.type === 'status_update'" class="flex justify-center my-2">
                <span class="text-xs bg-zinc-200/80 text-zinc-600 px-2 py-0.5 rounded-full">{{ log.message }}</span>
            </div>
            
            <!-- Agent Messages -->
            <div v-else class="flex gap-3">
                <div 
                    class="w-8 h-8 rounded-lg shrink-0 grid place-items-center text-xs font-bold"
                    :class="getAgentColor(log.name)"
                >
                    <component :is="getAgentIcon(log.name)" :size="16" />
                </div>
                
                <div class="space-y-1 max-w-[88%] min-w-0">
                    <div class="flex items-baseline gap-2">
                        <span class="text-xs font-bold text-zinc-700">{{ log.name }}</span>
                        <span class="text-[10px] text-zinc-400">{{ new Date(log.timestamp).toLocaleTimeString() }}</span>
                    </div>
                    <!-- [FIX] Added break-words, break-all, reduced max-width constraints -->
                    <div class="chat-bubble bg-white border border-zinc-200 p-3 rounded-2xl rounded-tl-sm shadow-sm text-zinc-600 text-xs leading-relaxed prose prose-sm max-w-none prose-zinc break-words break-all" v-html="renderMarkdown(log.content)"></div>
                </div>
            </div>
        </div>

        <!-- Success Message -->
        <div v-if="status === 'completed'" class="animate-fade-in-up flex flex-col items-center py-6 text-emerald-600 bg-emerald-50/50 rounded-lg border border-emerald-100 my-4">
             <div class="w-10 h-10 bg-emerald-100 rounded-full grid place-items-center mb-2">
                 <CheckCircle :size="20" />
             </div>
             <p class="font-medium">全流程分析已完成</p>
             <p class="text-xs text-emerald-600/70 mt-1 mb-3">思维导图与知识图谱已生成</p>
             <button 
                @click="$emit('close')"
                class="px-4 py-1.5 bg-white border border-emerald-200 shadow-sm rounded text-xs font-medium text-emerald-700 hover:bg-emerald-50 transition-colors"
             >
                关闭窗口查看结果
             </button>
        </div>

        <!-- Typing Indicator -->
        <div v-if="thinkingAgent" class="animate-fade-in-up flex gap-3">
             <div 
                class="w-8 h-8 rounded-lg shrink-0 grid place-items-center text-xs font-bold"
                :class="getAgentColor(thinkingAgent)"
            >
                <component :is="getAgentIcon(thinkingAgent)" :size="16" />
            </div>
            <div class="space-y-1">
                 <div class="flex items-baseline gap-2">
                    <span class="text-xs font-bold text-zinc-700">{{ thinkingAgent }}</span>
                    <span class="text-[10px] text-zinc-400">Thinking...</span>
                </div>
                <div class="bg-white border border-zinc-200 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm">
                    <div class="flex gap-1">
                        <span class="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span class="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span class="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce"></span>
                    </div>
                </div>
            </div>
        </div>

    </div>
  </div>
</template>

<style scoped>
/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

/* Force wrapping for all content inside chat bubbles, especially code blocks */
.chat-bubble :deep(pre),
.chat-bubble :deep(code) {
    white-space: pre-wrap !important;
    word-break: break-all !important;
    overflow-wrap: break-word !important;
}

.chat-bubble :deep(p),
.chat-bubble :deep(li) {
    word-break: break-all !important;
    overflow-wrap: break-word !important;
}
</style>
