<script setup>
  import { ref, nextTick } from 'vue'
  import { RouterLink } from 'vue-router'
  import { 
    ArrowRight, 
    BrainCircuit, 
    FileSearch, 
    MonitorPlay, 
    Sparkles,
    Command,
    Share2
  } from 'lucide-vue-next'

  // 演示视频功能
  const showDemo = ref(false)
  const videoRef = ref(null)

  const openDemo = async () => {
    showDemo.value = true
    await nextTick()
    // 尝试播放视频，如果失败则忽略错误
    if (videoRef.value) {
      try {
        await videoRef.value.play()
      } catch (error) {
        console.log('演示视频播放失败:', error)
      }
    }
  }

  const closeDemo = () => {
    showDemo.value = false
    if (videoRef.value) {
      videoRef.value.pause()
      videoRef.value.currentTime = 0
    }
  }
  </script>
  
  <template>
    <div class="space-y-12 pb-10">
      
      <section class="text-center space-y-6 pt-10">
        <div class="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-600 shadow-sm transition hover:border-zinc-300 cursor-default">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          New Model v2.0 Available
        </div>
  
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight text-zinc-900">
          Turn information into <br/>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-zinc-900 via-zinc-600 to-zinc-900">executable knowledge.</span>
        </h1>
        
        <p class="mx-auto max-w-2xl text-lg text-zinc-500 leading-relaxed">
          StudyAid 是你的全能 AI 阅读助手。上传文档或视频，即可自动提取摘要、构建知识图谱，并进行深度问答。
        </p>
  
        <div class="flex items-center justify-center gap-4 pt-2">
          <RouterLink to="/document-analysis" class="group relative inline-flex h-10 items-center justify-center overflow-hidden rounded-lg bg-zinc-900 px-6 font-medium text-white transition duration-300 hover:bg-zinc-800 hover:shadow-xl hover:shadow-zinc-200 active:scale-95">
            <span class="mr-2">开始分析</span>
            <ArrowRight :size="16" class="transition-transform group-hover:translate-x-1" />
          </RouterLink>
          <button 
          @click="openDemo"
          class="rounded-lg px-6 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition">
            查看演示
          </button>
        </div>
      </section>
  
      <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <RouterLink to="/document-analysis" class="tech-card group md:col-span-2 relative overflow-hidden rounded-2xl bg-white p-8 border border-zinc-200/60 shadow-sm transition-all duration-300 hover:shadow-xl hover:-translate-y-1 hover:border-zinc-300/80">
          <div class="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <FileSearch :size="120" />
          </div>
          <div class="relative z-10">
            <div class="h-12 w-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <FileSearch :size="24" />
            </div>
            <h3 class="text-xl font-semibold text-zinc-900">智能文档分析</h3>
            <p class="mt-2 text-zinc-500 max-w-md">
              支持 PDF、Word 等多格式。深度解析文档结构，生成摘要、关键问题与证据引用，一键生成思维导图。
            </p>
          </div>
        </RouterLink>
  
        <RouterLink to="/video-analysis" class="tech-card group relative overflow-hidden rounded-2xl bg-white p-8 border border-zinc-200/60 shadow-sm transition-all duration-300 hover:shadow-xl hover:-translate-y-1 hover:border-zinc-300/80">
          <div class="absolute -bottom-4 -right-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <MonitorPlay :size="100" />
          </div>
          <div class="relative z-10">
            <div class="h-12 w-12 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
              <MonitorPlay :size="24" />
            </div>
            <h3 class="text-lg font-semibold text-zinc-900">视频内容提取</h3>
            <p class="mt-2 text-sm text-zinc-500">
              将长视频转化为结构化笔记。自动识别时间轴与重点段落。
            </p>
          </div>
        </RouterLink>
  
        <RouterLink
          to="/pdf-helper"
          class="tech-card group rounded-2xl bg-white p-6 border border-zinc-200/60 shadow-sm transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
        >
          <div class="flex items-center gap-4">
            <div class="h-10 w-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <BrainCircuit :size="20" />
            </div>
            <div>
              <div class="font-medium text-zinc-900">PDF 助手</div>
              <div class="text-xs text-zinc-500 mt-0.5">PDF 处理工具箱</div>
            </div>
          </div>
        </RouterLink>

  
        <RouterLink to="/qa" class="tech-card group rounded-2xl bg-white p-6 border border-zinc-200/60 shadow-sm transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
          <div class="flex items-center gap-4">
            <div class="h-10 w-10 rounded-lg bg-zinc-100 text-zinc-700 flex items-center justify-center">
              <Command :size="20" />
            </div>
            <div>
              <div class="font-medium text-zinc-900">快捷指令库</div>
              <div class="text-xs text-zinc-500 mt-0.5">QA 问答与工具集</div>
            </div>
          </div>
        </RouterLink>
  
        <div class="tech-card group rounded-2xl bg-gradient-to-br from-zinc-50 to-white p-6 border border-zinc-200/60 border-dashed shadow-sm">
          <div class="flex items-center gap-4 opacity-60">
            <div class="h-10 w-10 rounded-lg bg-zinc-100 text-zinc-400 flex items-center justify-center">
              <Share2 :size="20" />
            </div>
            <div>
              <div class="font-medium text-zinc-900">分享协作</div>
              <div class="text-xs text-zinc-400 mt-0.5">Coming soon</div>
            </div>
          </div>
        </div>
  
      </section>
  
      <section class="border-t border-zinc-200 pt-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-lg font-bold text-zinc-900">最近更新</h2>
          <a href="#" class="text-xs font-medium text-zinc-500 hover:text-zinc-900">View Changelog -></a>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="i in 2" :key="i" class="flex gap-4 p-4 rounded-xl hover:bg-white hover:shadow-md border border-transparent hover:border-zinc-100 transition-all cursor-pointer">
            <div class="mt-1 h-2 w-2 rounded-full bg-emerald-500 shrink-0"></div>
            <div>
              <h4 class="text-sm font-medium text-zinc-900">Study Aid {{ i === 1 ? 'v2.1' : 'v2.0' }}</h4>
              <!-- <p class="mt-1 text-xs text-zinc-500 leading-relaxed">
                提升 PDF 解析速度，新增对扫描件 OCR 的支持，并优化思维导图的节点生成逻辑。
              </p> -->
              <div class="mt-2 flex gap-2">
                <span class="inline-flex items-center rounded-md bg-zinc-100 px-2 py-1 text-[10px] font-medium text-zinc-600">AI Engine</span>
                <span class="inline-flex items-center rounded-md bg-zinc-100 px-2 py-1 text-[10px] font-medium text-zinc-600">Performance</span>
              </div>
            </div>
          </div>
        </div>
      </section>
  
      <footer class="text-center text-xs text-zinc-400 py-6">
        © 2025 StudyAid Inc. All rights reserved.
      </footer>

      <!-- Demo Video Modal -->
      <Teleport to="body">
        <div
          v-if="showDemo"
          class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
          @click.self="closeDemo"
        >
          <div class="w-full max-w-4xl rounded-2xl bg-white overflow-hidden shadow-2xl">
            <div class="flex items-center justify-between px-4 py-3 border-b border-zinc-100">
              <div class="text-sm font-medium text-zinc-900">演示视频</div>
              <button class="text-sm text-zinc-500 hover:text-zinc-900" @click="closeDemo">关闭</button>
            </div>

            <video
              ref="videoRef"
              class="w-full h-auto bg-black"
              :src="'/demo_video.mp4'"
              controls
              muted
              playsinline
              @error="(e) => console.log('视频加载失败:', e)"
            >
              您的浏览器不支持视频播放
            </video>
          </div>
        </div>
      </Teleport>

    </div>
  </template>
  
  <style scoped>
  
  </style>

