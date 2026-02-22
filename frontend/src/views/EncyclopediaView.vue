<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { Search, Filter, BookOpen, Database, Layers, Tag } from 'lucide-vue-next'
import EntityDrawer from '@/components/encyclopedia/EntityDrawer.vue'

// Data
const allNodes = ref([])
const allEdges = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const selectedCategory = ref('All')

// Drawer State
const showDrawer = ref(false)
const selectedEntity = ref(null)

// Derived Data
const categories = computed(() => {
  const cats = new Set(allNodes.value.map(n => n.category || '通用'))
  return ['All', ...Array.from(cats).sort()]
})

const filteredNodes = computed(() => {
  return allNodes.value.filter(node => {
    // 1. Text Search
    if (searchQuery.value) {
       const q = searchQuery.value.toLowerCase()
       if (!node.name.toLowerCase().includes(q)) return false
    }
    // 2. Category Filter
    if (selectedCategory.value !== 'All') {
       if ((node.category || '通用') !== selectedCategory.value) return false
    }
    return true
  })
})

// Enhance nodes with connection count
const enrichedNodes = computed(() => {
  return filteredNodes.value.map(node => {
     const degree = allEdges.value.filter(e => e.source === node.id || e.target === node.id).length
     // Find top connections
     const topEdges = allEdges.value.filter(e => e.source === node.id || e.target === node.id).slice(0, 3)
     const connections = topEdges.map(e => {
         const otherId = e.source === node.id ? e.target : e.source
         const otherNode = allNodes.value.find(n => n.id === otherId)
         return otherNode ? otherNode.name : otherId
     })
     
     return {
       ...node,
       degree,
       previewConnections: connections
     }
  })
})

// Fetch Data
const fetchData = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/graph/data')
    // Expected format: { nodes: [{id, name, category, ...}], edges: [{source, target, relation...}] }
    if (res.data) {
        allNodes.value = res.data.nodes || []
        allEdges.value = res.data.links || []
    }
  } catch (e) {
    console.error("Failed to fetch encyclopedia data", e)
  } finally {
    isLoading.value = false
  }
}

const openEntity = (node) => {
  selectedEntity.value = node
  showDrawer.value = true
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Header Section (Search Engine Style) -->
    <div class="bg-white border-b border-zinc-200 py-8 px-8 mb-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 p-10 opacity-5 pointer-events-none">
            <BookOpen :size="300" />
        </div>
        
        <div class="max-w-4xl mx-auto relative z-10">
            <h1 class="text-3xl font-bold text-zinc-900 mb-2 flex items-center gap-3">
                <Database :size="32" class="text-blue-600" />
                知识智库 (Entity Encyclopedia)
            </h1>
            <p class="text-zinc-500 mb-8">全量检索系统提取的所有知识实体，支持微观溯源分析。</p>
            
            <!-- Search Bar -->
            <div class="relative shadow-xl shadow-blue-500/5 rounded-2xl">
                <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Search :size="20" class="text-zinc-400" />
                </div>
                <input 
                    v-model="searchQuery" 
                    type="text" 
                    class="block w-full pl-12 pr-4 py-4 rounded-2xl border-0 ring-1 ring-zinc-200 focus:ring-2 focus:ring-blue-500 text-lg placeholder:text-zinc-300 transition-shadow bg-white"
                    placeholder="输入关键词检索 (例如: 'Transformer', '损失函数')..."
                />
            </div>
        </div>
    </div>

    <!-- Filter Bar -->
    <div class="px-8 mb-6 max-w-7xl mx-auto w-full">
        <div class="flex items-center gap-4 overflow-x-auto py-2 scrollbar-hide">
            <div class="flex items-center gap-2 text-sm font-medium text-zinc-400 mr-2 shrink-0">
                <Filter :size="16" />
                分类索引:
            </div>
            <button 
                v-for="cat in categories" 
                :key="cat"
                @click="selectedCategory = cat"
                class="px-4 py-1.5 rounded-full text-sm font-medium transition-all whitespace-nowrap border shrink-0"
                :class="selectedCategory === cat 
                    ? 'bg-zinc-900 text-white border-zinc-900 shadow-md' 
                    : 'bg-white text-zinc-500 border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'"
            >
                {{ cat }}
            </button>
        </div>
    </div>

    <!-- Content Grid -->
    <div class="flex-1 px-8 pb-10 overflow-y-auto min-h-0">
        <div class="max-w-7xl mx-auto">
            
            <div v-if="isLoading" class="flex justify-center py-20">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>

            <div v-else-if="enrichedNodes.length === 0" class="text-center py-20 text-zinc-400">
                <p class="text-lg">未找到相关词条</p>
                <p class="text-sm mt-2">请尝试调整搜索词或分类</p>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 animate-fade-in-up">
                <div 
                    v-for="node in enrichedNodes" 
                    :key="node.id"
                    @click="openEntity(node)"
                    class="group bg-white border border-zinc-200 rounded-xl overflow-hidden hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer flex flex-col min-h-[180px] h-auto"
                >
                    <!-- Card Header Stripe -->
                    <div class="h-1.5 w-full bg-gradient-to-r from-blue-500 to-indigo-500 group-hover:from-blue-400 group-hover:to-cyan-400 transition-all"></div>
                    
                    <div class="p-5 flex-1 flex flex-col">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-xs font-bold px-2 py-0.5 rounded bg-zinc-100 text-zinc-500 uppercase tracking-wide group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                                {{ node.category || 'Concept' }}
                            </span>
                            <span class="text-xs font-mono text-zinc-300">#{{ node.degree }}</span>
                        </div>
                        
                        <h3 class="text-lg font-bold text-zinc-900 mb-2 group-hover:text-blue-700 transition-colors">
                            {{ node.name }}
                        </h3>
                        
                        <div class="text-xs text-zinc-500 mt-auto">
                            <div class="mb-1 flex items-center gap-1 opacity-70">
                                <Layers :size="12" />
                                <span>关联:</span>
                            </div>
                            <div class="leading-relaxed opacity-80 break-words">
                                {{ node.previewConnections.join(', ') || '暂无直接关联' }}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Card Footer -->
                    <div class="bg-zinc-50 px-4 py-2 border-t border-zinc-100 flex justify-between items-center text-[10px] text-zinc-400 group-hover:bg-blue-50/30 transition-colors">
                        <span class="flex items-center gap-1">
                           <Tag :size="10" /> ID: {{ node.id.substring(0,6) }}
                        </span>
                        <span class="font-medium group-hover:text-blue-600">View Dossier →</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Details Drawer -->
    <EntityDrawer 
        :is-visible="showDrawer" 
        :entity="selectedEntity" 
        :all-nodes="allNodes"
        :all-edges="allEdges"
        @close="showDrawer = false" 
    />

  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
