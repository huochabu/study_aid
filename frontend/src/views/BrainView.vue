<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext' // [NEW] For permanent labels
import axios from 'axios'
import MarkdownIt from 'markdown-it'
import { Search, Info, Share2, Sparkles, X, ArrowLeft } from 'lucide-vue-next'
import BrainManager from '@/components/BrainManager.vue'

const md = new MarkdownIt({
  html: false, // Enable HTML tags in source
  breaks: true, // Convert '\n' in paragraphs to <br>
  linkify: true // Autoconvert URL-like text to links
})

const renderMarkdown = (text) => {
    if (!text) return ''
    return md.render(text)
}

// Routing Logic
const route = useRoute()
const router = useRouter()
const fileId = computed(() => route.query.file_id || '')

// ==========================================
// MODE 1: Brain Manager (File Specific)
// ==========================================
const goBack = () => {
  router.back()
}

// ==========================================
// MODE 2: Global Graph (3D)
// ==========================================
const graphRef = ref(null)
const graphInstance = ref(null)
const nodes = ref([])
const links = ref([])
const loading = ref(true)
const searchQuery = ref('')
const selectedNode = ref(null)
const showSidebar = ref(false)
const showChat = ref(false)
const chatInput = ref('')
const chatHistory = ref([])
const chatLoading = ref(false)

// Color palette for categories
const colorMap = {
  Concept: '#6366f1', // Indigo
  Person: '#ec4899', // Pink
  Algorithm: '#10b981', // Emerald
  Technology: '#3b82f6', // Blue
  Document: '#f59e0b', // Amber
  Other: '#8b5cf6' // Violet
}

// Auto-generate colors for clusters
const getClusterColor = (clusterId) => {
    if (clusterId === undefined) return colorMap.Other
    const hue = (clusterId * 137.508) % 360 // Golden angle approximation for distinct colors
    return `hsl(${hue}, 65%, 60%)`
}

const getNodeColor = (node) => {
  // Strategy: If node has a specific cluster, use it. 
  // But maybe user wants Categories? 
  // Let's mix: Use cluster color for distinct structures.
  if (node.cluster !== undefined) {
      return getClusterColor(node.cluster)
  }
  return colorMap[node.group] || colorMap.Other
}

// Compute Connected Components
const computeClusters = (nodes, links) => {
    const adj = new Map()
    const nodeMap = new Map()
    
    nodes.forEach(n => {
        adj.set(n.id, [])
        nodeMap.set(n.id, n)
        n.cluster = undefined // Reset
    })
    
    links.forEach(l => {
        // Handle both string IDs and object references (ForceGraph parses them)
        const s = typeof l.source === 'object' ? l.source.id : l.source
        const t = typeof l.target === 'object' ? l.target.id : l.target
        
        if (adj.has(s)) adj.get(s).push(t)
        if (adj.has(t)) adj.get(t).push(s)
    })
    
    const visited = new Set()
    let clusterId = 0
    
    nodes.forEach(node => {
        if (!visited.has(node.id)) {
            // New component
            const stack = [node.id]
            visited.add(node.id)
            
            while (stack.length) {
                const currId = stack.pop()
                const currNode = nodeMap.get(currId)
                if (currNode) currNode.cluster = clusterId
                
                const neighbors = adj.get(currId) || []
                neighbors.forEach(nextId => {
                    if (!visited.has(nextId)) {
                        visited.add(nextId)
                        stack.push(nextId)
                    }
                })
            }
            clusterId++
        }
    })
    console.log(`Discovered ${clusterId} clusters/components in graph.`)
}

const initGraph = () => {
  if (!graphRef.value) return 
  
  const width = graphRef.value.clientWidth
  const height = graphRef.value.clientHeight

    graphInstance.value = ForceGraph3D()(graphRef.value)
    .width(width)
    .height(height)
    .graphData({ nodes: nodes.value, links: links.value })
    .nodeLabel('name') // Tooltip still useful
    .nodeColor(getNodeColor)
    .nodeVal(node => Math.sqrt(node.val) * 2) 
    .nodeResolution(16)
    .linkWidth(link => link.weight || 0.5)
    .linkOpacity(0.3)
    .backgroundColor('#00000000') 
    .nodeThreeObject(node => {
        // [NEW] Permanent Label
        const sprite = new SpriteText(node.name)
        sprite.color = '#ffffff'
        sprite.textHeight = 2 + (node.val * 0.2) // Scale text with node importance
        sprite.position.y = 8 // Offset label above node
        return sprite
    })
    .nodeThreeObjectExtend(true) // Keep the sphere node
    .onNodeClick(handleNodeClick)
    .onBackgroundClick(() => {
        showSidebar.value = false
        selectedNode.value = null
        resetHighlight()
    })
}

// [NEW] Highlighting Logic
const highlightNodes = ref(new Set())
const highlightLinks = ref(new Set())

const resetHighlight = () => {
    highlightNodes.value.clear()
    highlightLinks.value.clear()
    if (graphInstance.value) {
        // Reset colors logic
        graphInstance.value.nodeColor(graphInstance.value.nodeColor())
        graphInstance.value.linkColor(graphInstance.value.linkColor())
    }
}

const applyHighlight = (subgraphData) => {
    if (!subgraphData || !graphInstance.value) return
    
    // Add IDs to sets
    subgraphData.nodes.forEach(id => highlightNodes.value.add(id))
    subgraphData.edges.forEach(e => highlightLinks.value.add(`${e.source}-${e.target}`))
    
    // Force graph update: NODE COLOR
     graphInstance.value.nodeColor(node => {
        if (highlightNodes.value.has(node.id)) {
            return '#ffff00' // Bright Yellow for active thought
        }
        return getNodeColor(node) // Original color
    })
    
    // Force graph update: LINK COLOR
    graphInstance.value.linkColor(link => {
        // Ensure we handle object vs string ID
        const s = typeof link.source === 'object' ? link.source.id : link.source
        const t = typeof link.target === 'object' ? link.target.id : link.target
        const id1 = `${s}-${t}`
        const id2 = `${t}-${s}` // Check both directions just in case
        
        if (highlightLinks.value.has(id1) || highlightLinks.value.has(id2)) {
            return '#ffff00'
        }
        return 'rgba(255,255,255,0.2)' // Default dim color
    })
    
    // Force graph update: LINK WIDTH
     graphInstance.value.linkWidth(link => {
        const s = typeof link.source === 'object' ? link.source.id : link.source
        const t = typeof link.target === 'object' ? link.target.id : link.target
        const id1 = `${s}-${t}`
        if (highlightLinks.value.has(id1)) return 2.0
        return 0.5
    })

    // [NEW] Camera Auto-Focus
    // Calculate geometric center of highlighted nodes
    if (subgraphData.nodes.length > 0) {
        let sumX = 0, sumY = 0, sumZ = 0, count = 0
        nodes.value.forEach(n => {
            if (highlightNodes.value.has(n.id)) {
                sumX += n.x || 0
                sumY += n.y || 0
                sumZ += n.z || 0
                count++
            }
        })
        
        if (count > 0) {
            const centerX = sumX / count
            const centerY = sumY / count
            const centerZ = sumZ / count
            
            const distance = 100 // Proper distance to view the cluster
            
            graphInstance.value.cameraPosition(
                { x: centerX, y: centerY, z: centerZ + distance }, // Position
                { x: centerX, y: centerY, z: centerZ }, // LookAt
                2000 // Transition ms
            )
        }
    }
}

const handleNodeClick = (node) => {
    selectedNode.value = node
    showSidebar.value = true
    
    // Focus camera on node
    const distance = 40
    const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z)

    graphInstance.value.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        node, // lookAt ({ x, y, z })
        3000  // ms transition duration
    )
}

const fetchData = async () => {
    // Only fetch if in Global Mode
    if (fileId.value) return

    loading.value = true
    try {
        const res = await axios.get('/api/graph/data')
        nodes.value = res.data.nodes || []
        links.value = res.data.links || []
        
        // [NEW] Compute clusters for coloring
        computeClusters(nodes.value, links.value)
        
        // Refresh graph
        if (graphInstance.value) {
            graphInstance.value.graphData({ nodes: nodes.value, links: links.value })
        } else {
            // Delay init slightly to ensure DOM is ready
            setTimeout(initGraph, 100)
        }
    } catch (e) {
        console.error("Failed to fetch graph data", e)
    } finally {
        loading.value = false
    }
}

// Window resize handler
const onResize = () => {
    if (graphInstance.value && graphRef.value) {
        graphInstance.value.width(graphRef.value.clientWidth)
        graphInstance.value.height(graphRef.value.clientHeight)
    }
}

const handleSearch = () => {
    if (!searchQuery.value) return
    const target = nodes.value.find(n => n.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
    if (target) {
        handleNodeClick(target)
    }
}

const sendChat = async () => {
    if (!chatInput.value.trim()) return
    
    const question = chatInput.value
    chatHistory.value.push({ role: 'user', content: question })
    chatInput.value = ''
    chatLoading.value = true
    
    try {
        const res = await axios.post('/api/graph/qa', { question })
        
        // [NEW] Update Chat UI
        chatHistory.value.push({ 
            role: 'assistant', 
            content: res.data.answer,
            context: res.data.context,
            entities: res.data.extracted_entities
        })
        
        // [NEW] Trigger Graph Highlight
        if (res.data.context_data) {
             applyHighlight(res.data.context_data)
        }
        
    } catch (e) {
        chatHistory.value.push({ role: 'assistant', content: "Error: " + (e.response?.data?.detail || e.message) })
    } finally {
        chatLoading.value = false
    }
}

// Watchers and Lifecycle
onMounted(() => {
    fetchData()
    window.addEventListener('resize', onResize)
})

onUnmounted(() => {
    window.removeEventListener('resize', onResize)
})

watch(fileId, (newId) => {
    if (!newId) {
        // Return to global mode, fetch data
        fetchData()
    }
})
</script>

<template>
  <div>
      <!-- MODE 1: FILE SPECIFIC MANAGER -->
      <div v-if="fileId" class="min-h-screen bg-zinc-50 p-6">
        <div class="max-w-4xl mx-auto space-y-6">
          <!-- Header -->
          <div class="flex items-center gap-4">
            <button @click="goBack" class="p-2 -ml-2 text-zinc-400 hover:text-zinc-600 rounded-lg hover:bg-zinc-100 transition-colors">
              <ArrowLeft :size="24" />
            </button>
            <div>
               <h1 class="text-2xl font-bold text-zinc-900">知识库管理 (Brain Manager)</h1>
               <p class="text-sm text-zinc-500">查看并管理 AI 针对该文档学到的所有规则</p>
            </div>
          </div>

          <!-- Main Content -->
          <div class="bg-white rounded-2xl shadow-sm border border-zinc-200 min-h-[600px] flex flex-col overflow-hidden">
             <BrainManager :file-id="fileId" />
          </div>
        </div>
      </div>

      <!-- MODE 2: GLOBAL 3D BRAIN -->
      <div v-else class="relative w-full h-[calc(100vh-8rem)] bg-zinc-950 rounded-2xl overflow-hidden shadow-2xl border border-zinc-800 flex">
        
        <!-- 3D Canvas -->
        <div ref="graphRef" class="w-full h-full cursor-move"></div>

        <!-- Loading Overlay -->
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-black/50 z-50">
            <div class="text-white flex flex-col items-center">
                <Sparkles class="animate-spin mb-2" />
                <span>Loading Global Brain...</span>
            </div>
        </div>

        <!-- UI Overlay: Search -->
        <div class="absolute top-4 left-4 z-10 w-80">
            <div class="relative group">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search class="h-5 w-5 text-zinc-400 group-focus-within:text-white transition-colors" />
                </div>
                <input 
                    v-model="searchQuery" 
                    @keyup.enter="handleSearch"
                    type="text" 
                    class="block w-full pl-10 pr-3 py-2 border border-zinc-700 rounded-xl leading-5 bg-zinc-900/80 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:bg-zinc-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 sm:text-sm backdrop-blur-md transition-all" 
                    placeholder="Search concepts, documents..."
                >
            </div>
        </div>

        <!-- UI Overlay: Stats/Legend -->
        <div class="absolute bottom-4 left-4 z-10 p-4 bg-zinc-900/80 backdrop-blur-md rounded-xl border border-zinc-800 text-xs text-zinc-400">
            <div class="mb-2 font-bold text-zinc-300">Graph Stats</div>
            <div class="flex items-center gap-2 mb-1">
                <span class="w-2 h-2 rounded-full bg-zinc-500"></span> 
                {{ nodes.length }} Concepts
            </div>
            <div class="flex items-center gap-2 mb-2">
                 <span class="w-2 h-2 rounded-full bg-zinc-600 h-px w-4"></span> 
                 {{ links.length }} Relations
            </div>
             <div class="text-[10px] opacity-60 mt-2">
                * Colors represent connected knowledge clusters
            </div>
        </div>

        <!-- Chat Interface -->
        <div class="absolute bottom-4 right-4 z-20 flex flex-col items-end">
            <!-- Chat Toggle -->
            <button @click="showChat = !showChat" class="bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-full shadow-lg transition-colors mb-4">
                <Sparkles :size="24" />
            </button>

            <!-- Chat Panel -->
            <transition name="slide-up">
                <div v-if="showChat" class="w-96 h-[500px] bg-zinc-900/95 backdrop-blur-xl border border-zinc-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
                    <div class="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-800/50">
                        <h3 class="font-bold text-white flex items-center gap-2">
                            <Sparkles :size="16" class="text-indigo-400" />
                            GraphRAG Assistant
                        </h3>
                        <button @click="showChat = false" class="text-zinc-500 hover:text-white">
                            <X :size="16" />
                        </button>
                    </div>
                    
                    <div class="flex-1 overflow-y-auto p-4 space-y-4">
                        <div v-for="(msg, idx) in chatHistory" :key="idx" class="flex flex-col gap-1">
                            <div :class="['max-w-[85%] rounded-lg p-3 text-sm', msg.role === 'user' ? 'bg-indigo-600 text-white self-end' : 'bg-zinc-800 text-zinc-200 self-start']">
                                <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
                                <div v-else>{{ msg.content }}</div>
                            </div>
                            <!-- Context Debug info for Assistant -->
                            <div v-if="msg.context" class="ml-1 text-[10px] text-zinc-500 self-start">
                                Logic Path: Found {{ msg.entities?.length }} concepts.
                            </div>
                        </div>
                         <div v-if="chatLoading" class="flex gap-2 items-center text-zinc-500 text-xs ml-2">
                            <span class="animate-bounce">●</span>
                            <span class="animate-bounce delay-100">●</span>
                            <span class="animate-bounce delay-200">●</span>
                            Thinking with Graph knowledge...
                        </div>
                    </div>

                    <div class="p-4 border-t border-zinc-800 bg-zinc-800/30">
                        <input 
                            v-model="chatInput" 
                            @keyup.enter="sendChat"
                            type="text" 
                            class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                            placeholder="Ask about concepts relationships..."
                        >
                    </div>
                </div>
            </transition>
        </div>

        <!-- Sidebar: Node Details -->
        <transition name="slide-right">
            <div v-if="showSidebar && selectedNode" class="absolute right-0 top-0 bottom-0 w-80 bg-zinc-900/95 backdrop-blur-xl border-l border-zinc-800 p-6 overflow-y-auto shadow-2xl z-20">
                <div class="flex items-start justify-between mb-6">
                    <div class="flex-1">
                        <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-2"
                            :style="{ backgroundColor: getNodeColor(selectedNode) + '20', color: getNodeColor(selectedNode) }">
                            {{ selectedNode.group }}
                        </span>
                        <h2 class="text-xl font-bold text-white break-words">{{ selectedNode.name }}</h2>
                    </div>
                    <button @click="showSidebar = false" class="text-zinc-500 hover:text-white transition-colors">
                        <X :size="20" />
                    </button>
                </div>

                <div class="space-y-6">
                    <div v-if="selectedNode.desc" class="prose prose-invert prose-sm">
                        <h3 class="text-zinc-400 text-xs font-bold uppercase tracking-widest mb-2">Summary</h3>
                        <p class="text-zinc-300 leading-relaxed">{{ selectedNode.desc }}</p>
                    </div>

                    <div>
                        <h3 class="text-zinc-400 text-xs font-bold uppercase tracking-widest mb-2">Reasoning & Insights</h3>
                        <div class="bg-zinc-800/50 rounded-lg p-3 text-sm text-zinc-400 italic">
                            Select another node to find paths or ask a question about this concept.
                        </div>
                    </div>

                     <div>
                        <h3 class="text-zinc-400 text-xs font-bold uppercase tracking-widest mb-2">Neighbors</h3>
                        <div class="flex flex-wrap gap-2">
                             <!-- Simplified neighbor logic for display -->
                             <div v-for="link in links.filter(l => l.source.id === selectedNode.id || l.target.id === selectedNode.id).slice(0, 5)" :key="link.source.id + link.target.id"
                                class="px-2 py-1 bg-zinc-800 rounded border border-zinc-700 text-xs text-zinc-300">
                                 {{ link.source.id === selectedNode.id ? link.target.name : link.source.name }}
                             </div>
                        </div>
                     </div>
                </div>
            </div>
        </transition>

      </div>
  </div>
</template>

<style scoped>
.slide-right-enter-active,
.slide-right-leave-active,
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

/* Markdown Styles for Chat */
.markdown-body :deep(p) {
    margin-bottom: 0.5em;
}
.markdown-body :deep(p:last-child) {
    margin-bottom: 0;
}
.markdown-body :deep(strong) {
    font-weight: 700;
    color: #e4e4e7; /* zinc-200 */
}
.markdown-body :deep(ul) {
    list-style-type: disc;
    padding-left: 1.2em;
    margin-bottom: 0.5em;
}
.markdown-body :deep(ol) {
    list-style-type: decimal;
    padding-left: 1.2em;
    margin-bottom: 0.5em;
}
.markdown-body :deep(li) {
    margin-bottom: 0.25em;
}
</style>
