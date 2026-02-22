<script setup>
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  // 引入图标
  import { 
    LayoutDashboard, 
    FileText, 
    Video, 
    FileStack, 
    Sparkles,
    Search,
    Plus,
    Network, // [NEW]
    BookOpen // [NEW]
  } from 'lucide-vue-next'

  import SelectionTranslator from '@/components/SelectionTranslator.vue'
  const route = useRoute()
  
  // 定义导航
  const navLinks = [
    { path: '/', name: 'intro', label: '首页', icon: LayoutDashboard },
    { path: '/document-analysis', name: 'document-analysis', label: '智能文档分析', icon: FileText },
    { path: '/video-analysis', name: 'video-analysis', label: '智能视频分析', icon: Video },
    { path: '/pdf-helper', name: 'pdf-helper', label: 'PDF 助手', icon: FileStack },
    { path: '/bilingual-reader', name: 'bilingual-reader', label: '双语对照阅读', icon: FileText },
    { path: '/learning', name: 'learning', label: '学习系统', icon: LayoutDashboard },
    { path: '/dashboard', name: 'dashboard', label: '数据驾驶舱', icon: LayoutDashboard },
    { path: '/comparison', name: 'comparison', label: '智能比对', icon: Sparkles },
    { path: '/encyclopedia', name: 'encyclopedia', label: '知识智库', icon: BookOpen }, // [NEW]
    { path: '/brain', name: 'brain', label: '全局知识大脑', icon: Network }, // [NEW]
  ]
  
  const currentLabel = computed(() => {
    const hit = navLinks.find(x => x.path === route.path)
    return hit ? hit.label : 'Study Aid'
  })
  </script>
  
  <template>
    <div class="min-h-screen bg-[#FAFAFA] text-zinc-900 selection:bg-black selection:text-white">
      <SelectionTranslator />
      <div class="flex min-h-screen">
        
        <aside class="w-56 shrink-0 border-r border-zinc-200/60 bg-white/50 backdrop-blur-xl flex flex-col sticky top-0 h-screen z-30">
          <div class="h-16 px-6 flex items-center gap-3">
            <div class="h-8 w-8 rounded-lg bg-gradient-to-br from-zinc-800 to-black text-white grid place-items-center shadow-lg shadow-zinc-200">
              <Sparkles :size="16" />
            </div>
            <div class="leading-none">
              <div class="font-bold text-base tracking-tight">StudyAid</div>
              <div class="text-[10px] uppercase tracking-wider text-zinc-400 font-medium mt-1">AI Workspace</div>
            </div>
          </div>
  
          <nav class="px-4 py-6 space-y-1 flex-1">
            <div class="text-[11px] font-bold text-zinc-400 uppercase tracking-widest px-3 mb-3">Menu</div>
  
            <router-link
              v-for="link in navLinks"
              :key="link.path"
              :to="link.path"
              class="group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-300 ease-out"
              :class="route.path === link.path 
                ? 'bg-zinc-100/80 text-zinc-900 font-medium' 
                : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900'"
            >
              <div v-if="route.path === link.path" class="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-zinc-900" />
              
              <component :is="link.icon" :size="18" :class="route.path === link.path ? 'text-zinc-900' : 'text-zinc-400 group-hover:text-zinc-600'" />
              <span>{{ link.label }}</span>
            </router-link>
          </nav>

        </aside>
  
        <div class="flex-1 flex flex-col min-w-0">
          <header class="sticky top-0 z-20 border-b border-zinc-200/60 bg-white/80 backdrop-blur-md h-16 px-8 flex items-center justify-between">
            <div class="flex items-center gap-2 text-sm text-zinc-500">
              <span class="opacity-50">App</span>
              <span class="opacity-30">/</span>
              <span class="text-zinc-800 font-medium">{{ currentLabel }}</span>
            </div>
            <!-- Search and New Project removed -->
          </header>
  
          <main class="flex-1 p-8">
            <div class="mx-auto max-w-6xl animate-fade-in-up">
              <router-view />
            </div>
          </main>
        </div>
      </div>
    </div>
  </template>
  
  <style>
  /* 淡入上浮动画 */
  .animate-fade-in-up {
    animation: fadeInUp 0.5s ease-out;
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  </style>