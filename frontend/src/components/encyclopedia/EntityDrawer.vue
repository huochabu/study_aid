<script setup>
import { ref, watch, onMounted, computed, nextTick } from 'vue'
import { Network } from 'lucide-vue-next'
import { Network as VisNetwork } from 'vis-network'
import { DataSet } from 'vis-data'
import { X, FileText, Share2, ZoomIn, ExternalLink } from 'lucide-vue-next'

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  entity: { type: Object, default: null }, // Current selected node
  allNodes: { type: Array, default: () => [] }, // Needed for neighbor lookup
  allEdges: { type: Array, default: () => [] }  // Needed for graph building
})

const emit = defineEmits(['close'])

const activeTab = ref('micrograph') // 'relations', 'micrograph', 'evidence'
const networkContainer = ref(null)
let networkInstance = null

// --- Micro-Graph Logic ---
const initMicroGraph = () => {
  if (!networkContainer.value || !props.entity) return
  
  // 1. Filter neighbors
  // Find all edges connected to this node
  const connectedEdges = props.allEdges.filter(e => 
    e.source === props.entity.id || e.target === props.entity.id
  )
  
  // Find all neighbor nodes
  const neighborIds = new Set()
  connectedEdges.forEach(e => {
    neighborIds.add(e.source)
    neighborIds.add(e.target)
  })
  
  // Build Mini Data
  const miniNodes = props.allNodes.filter(n => neighborIds.has(n.id)).map(n => ({
    id: n.id,
    label: n.name || n.id,
    // Highlight center node
    color: n.id === props.entity.id ? '#ef4444' : '#3b82f6',
    size: n.id === props.entity.id ? 40 : 25,
    font: { size: 14, color: '#333' },
    shape: 'dot'
  }))
  
  const miniEdges = connectedEdges.map(e => ({
    from: e.source,
    to: e.target,
    label: e.relation || 'link',
    font: { size: 10, align: 'middle' },
    color: '#cbd5e1'
  }))

  const data = {
    nodes: new DataSet(miniNodes),
    edges: new DataSet(miniEdges)
  }
  
  const options = {
    nodes: { borderWidth: 2, shadow: true },
    physics: {
      stabilization: false,
      barnesHut: { gravitationalConstant: -2000, springLength: 100 }
    },
    interaction: { zoomView: true, dragView: true }
  }
  
  if (networkInstance) networkInstance.destroy()
  networkInstance = new VisNetwork(networkContainer.value, data, options)
}

// Watchers to trigger graph render
watch(() => [props.isVisible, props.entity, activeTab.value], async ([vis, ent, tab]) => {
  if (vis && ent && tab === 'micrograph') {
    await nextTick()
    initMicroGraph()
  }
})

// --- Data Helpers ---
const relationsList = computed(() => {
  if (!props.entity || !props.allEdges) return []
  return props.allEdges.filter(e => e.source === props.entity.id || e.target === props.entity.id)
    .map(e => {
      const isSource = e.source === props.entity.id
      const otherId = isSource ? e.target : e.source
      const otherNode = props.allNodes.find(n => n.id === otherId)
      return {
        type: isSource ? 'Out (推论)' : 'In (来源)',
        relation: e.relation || 'related',
        targetName: otherNode ? (otherNode.name || otherNode.id) : otherId
      }
    })
})

const parseDocs = (docStr) => {
  try {
    return JSON.parse(docStr || '[]')
  } catch (e) {
    return []
  }
}
</script>

<template>
  <!-- Backdrop -->
  <div v-if="isVisible" class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity" @click="$emit('close')"></div>

  <!-- Drawer -->
  <div 
    class="fixed top-0 right-0 h-full w-[600px] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col"
    :class="isVisible ? 'translate-x-0' : 'translate-x-full'"
  >
    <!-- Header -->
    <div class="p-6 border-b border-zinc-100 flex justify-between items-start bg-zinc-50/50">
      <div>
        <div class="flex items-center gap-2 mb-2">
            <span class="px-2 py-0.5 rounded textxs font-bold bg-blue-100 text-blue-700 uppercase tracking-wider">
                {{ entity?.category || 'Entity' }}
            </span>
            <span class="text-xs text-zinc-400 font-mono">ID: {{ entity?.id?.substring(0,8) }}...</span>
        </div>
        <h2 class="text-2xl font-bold text-zinc-900">{{ entity?.name || 'Unknown Entity' }}</h2>
      </div>
      <button @click="$emit('close')" class="p-2 hover:bg-zinc-200 rounded-full transition text-zinc-500">
        <X :size="20" />
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-zinc-200 px-6">
      <button 
        v-for="tab in ['micrograph', 'relations', 'evidence']" 
        :key="tab"
        @click="activeTab = tab"
        class="px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize flex items-center gap-2"
        :class="activeTab === tab ? 'border-zinc-900 text-zinc-900' : 'border-transparent text-zinc-500 hover:text-zinc-700'"
      >
        <span v-if="tab==='micrograph'">🕸️ 微观图谱</span>
        <span v-if="tab==='relations'">🔗 关系列表</span>
        <span v-if="tab==='evidence'">📄 溯源证据</span>
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6 bg-white relative">
      
      <!-- Tab: MicroGraph -->
      <div v-show="activeTab === 'micrograph'" class="h-full flex flex-col">
          <div class="bg-blue-50/50 border border-blue-100 p-3 rounded-lg text-sm text-blue-700 mb-4 flex items-center gap-2">
              <ZoomIn :size="16" />
              <span>显示当前节点及其直接关联的邻居节点（Ego-Network）</span>
          </div>
          <div class="flex-1 border border-zinc-200 rounded-xl bg-zinc-50 overflow-hidden relative" ref="networkContainer">
             <!-- Canvas injected here -->
          </div>
      </div>

      <!-- Tab: Relations -->
      <div v-if="activeTab === 'relations'" class="space-y-4">
        <table class="w-full text-sm text-left">
          <thead class="bg-zinc-50 text-zinc-500 font-medium">
            <tr>
              <th class="px-4 py-2 rounded-l-lg">方向</th>
              <th class="px-4 py-2">关系类型</th>
              <th class="px-4 py-2 rounded-r-lg">关联实体</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-100">
            <tr v-for="(rel, idx) in relationsList" :key="idx" class="hover:bg-zinc-50 transition">
              <td class="px-4 py-3 text-zinc-500 font-mono text-xs">{{ rel.type }}</td>
              <td class="px-4 py-3 font-medium text-blue-600">{{ rel.relation }}</td>
              <td class="px-4 py-3 font-bold text-zinc-800">{{ rel.targetName }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="relationsList.length === 0" class="text-center py-10 text-zinc-400">无关联记录</div>
      </div>

      <!-- Tab: Evidence -->
      <div v-if="activeTab === 'evidence'" class="space-y-6">
          <!-- Definition -->
          <div v-if="entity?.digest">
              <h3 class="text-sm font-bold text-zinc-900 mb-2 flex items-center gap-2">
                  <FileText :size="16" /> 核心定义 (AI Extracted)
              </h3>
              <div class="p-4 bg-yellow-50/50 border border-yellow-100 rounded-lg text-zinc-700 text-sm leading-relaxed">
                  {{ entity.digest }}
              </div>
          </div>

          <!-- Documents -->
          <div>
              <h3 class="text-sm font-bold text-zinc-900 mb-2 flex items-center gap-2">
                  <ExternalLink :size="16" /> 来源文档
              </h3>
              <div class="space-y-2">
                  <div v-for="(docId, i) in parseDocs(entity?.document_ids)" :key="i" class="flex items-center gap-3 p-3 border border-zinc-200 rounded-lg hover:border-blue-300 transition cursor-pointer group">
                      <div class="h-8 w-8 bg-zinc-100 rounded flex items-center justify-center text-zinc-500 group-hover:bg-blue-50 group-hover:text-blue-600">
                          <FileText :size="16" />
                      </div>
                      <div class="flex-1">
                          <div class="text-sm font-medium text-zinc-900 group-hover:text-blue-700">Document {{ docId }}</div>
                          <div class="text-xs text-zinc-400">Click to locate (Mock)</div>
                      </div>
                      <ExternalLink :size="14" class="text-zinc-300 group-hover:text-blue-400" />
                  </div>
              </div>
              <div v-if="parseDocs(entity?.document_ids).length === 0" class="text-xs text-zinc-400 italic">
                  未记录来源文档ID
              </div>
          </div>
      </div>

    </div>
    
  </div>
</template>
