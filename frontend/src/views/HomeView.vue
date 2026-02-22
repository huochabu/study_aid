<script setup>
  import { ref, computed, onMounted, nextTick } from 'vue'
  import axios from 'axios'
  
  // components
  import MindMap from '@/components/MindMap.vue'
  import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
  import FileUploader from '@/components/FileUploader.vue'
  import FileManager from '@/components/FileManager.vue'
  import HistoryManager from '@/components/HistoryManager.vue'
  import EvaluationScore from '@/components/EvaluationScore.vue'
  import FeedbackWidget from '@/components/FeedbackWidget.vue'
  import PDFViewer from '@/components/PDFViewer.vue' // [NEW]
  import ImageViewer from '@/components/ImageViewer.vue' // [NEW]
  import AgentAnalysisWindow from '@/components/AgentAnalysisWindow.vue' // [NEW]
  import BrainManager from '@/components/BrainManager.vue' // [NEW]
  import ReviewScoreCard from '@/components/ReviewScoreCard.vue' // [NEW]
  import MarkdownIt from 'markdown-it'
  
  const md = new MarkdownIt({ html: true, linkify: true, breaks: true })  
  // icons
  import {
    Network,
    Share2,
    MessageSquareText,
    Download,
    Upload,
    Plus,
    Minus,
    FileJson,
    Image as ImageIcon,
    Search,
    Bot,
    Loader2,
    ArrowUp,
    FileText, // [NEW]
    AlertTriangle, // [NEW]
    Trash2, // [NEW]
    Brain, // [NEW]

    RefreshCw, // [NEW]
    ScrollText, // [NEW]
    Award // [NEW]
  } from 'lucide-vue-next'
  
  // --- 逻辑保持不变 ---
  const analysisResult = ref(null)
  const errorMsg = ref('')
  const anomalyReport = ref('') // [NEW]
  
  const currentView = ref('graph')
  const question = ref('')
  const answer = ref('')
  const evidenceList = ref([])
  const history = ref([])
  const isAsking = ref(false)
  const isPolling = ref(false) // [NEW] Status of polling
  const currentEvaluation = ref(null) // [NEW] { faithfulness: 0, relevancy: 0, reason: '' }
  const highlightText = ref('') // [NEW] Text to highlight in document view
  const docViewRef = ref(null) // [NEW] Reference to doc view container
  
  // [NEW] Agent Visualization State
  const showAgentWindow = ref(false)
  const agentLogs = ref([])
  const analysisStatus = ref('idle') // idle, analyzing, generating, completed
  const analysisProgress = ref(0)
  const currentPhase = ref('准备就绪')
  const thinkingAgent = ref(null) // [NEW] Who is thinking
  
  // [NEW] Peer Review State
  const reviewData = ref(null)
  const isReviewLoading = ref(false)

  const handleReviewTabClick = async () => {
    currentView.value = 'review'
    if (!reviewData.value && analysisResult.value?.file_id) {
       await fetchReview()
    }
  }

  const fetchReview = async () => {
    if (!analysisResult.value?.file_id) return
    isReviewLoading.value = true
    try {
        // Prepare request
        // We can pass file_id, or if we have text we can pass text.
        // The API /api/review/generate expects JSON body with text or file_id?
        // Let's check review.py. It uses ReviewRequest with file_id optional.
        const res = await axios.post('/api/review/generate', {
            file_id: analysisResult.value.file_id
        })
        if (res.data.status === 'success') {
            reviewData.value = res.data.data
        } else {
            alert('Review generation failed: ' + res.data.message)
        }
    } catch (e) {
        console.error("Fetch review failed", e)
        alert('Failed to generate review.')
    } finally {
        isReviewLoading.value = false
    }
  }
  
  // 缓存与计算属性
  const cachedMindmapData = ref(null)
  const mindmapDataForComponent = computed(() => {
    const raw = analysisResult.value?.mindmap
    if (!raw) {
      cachedMindmapData.value = null
      return null
    }
    let newData
    if (raw.rootTopic && !raw.root) {
      newData = { root: { id: 'root', topic: raw.rootTopic, children: Array.isArray(raw.children) ? raw.children : [] } }
    } else if (raw.root && typeof raw.root === 'object') {
      newData = raw
    } else {
      newData = { root: { id: raw.id || 'root', topic: raw.topic || '默认主题', children: Array.isArray(raw.children) ? raw.children : [] } }
    }
    if (!cachedMindmapData.value || JSON.stringify(newData) !== JSON.stringify(cachedMindmapData.value)) {
      cachedMindmapData.value = newData
    }
    return cachedMindmapData.value
  })
  
  const isMindMapValid = computed(() => {
    const data = mindmapDataForComponent.value
    if (!data || typeof data !== 'object') return false
    const root = data.root
    return !!root?.topic
  })
  
  const knowledgeGraphData = computed(() => {
    const raw = analysisResult.value?.knowledge_graph
    if (!raw) return { nodes: [], edges: [] }
    return { nodes: Array.isArray(raw.nodes) ? raw.nodes : [], edges: Array.isArray(raw.edges) ? raw.edges : [] }
  })
  
  const isKnowledgeGraphValid = computed(() => {
    const data = analysisResult.value?.knowledge_graph
    return data && typeof data === 'object' && Array.isArray(data.nodes) && Array.isArray(data.edges)
  })

  // [NEW] Computed for BrainManager
  const currentFileId = computed(() => analysisResult.value?.file_id || '')
  
  // refs
  const fileManager = ref(null)
  const historyManager = ref(null)
  const mindMapComponent = ref(null)
  const mindMapKey = ref(0) // [NEW] Key for forcing re-render
  const knowledgeGraphComponent = ref(null)
  const importFileInput = ref(null)
  const importKnowledgeGraphInput = ref(null)
  const resultsSection = ref(null) // [NEW] Ref for auto-scroll
  const currentAnalyzingFilename = ref('') // [NEW] Ref for filename display during analysis
  const selectedNodeId = ref(null) // [NEW] Selected node ID for mindmap operations
  
  // handlers
  const handleUploadError = (errorMessage) => { errorMsg.value = errorMessage }
  
  const handleAddNode = () => { if (mindMapComponent.value) mindMapComponent.value.addNode(selectedNodeId.value) }
  const handleDeleteNode = () => { if (mindMapComponent.value) mindMapComponent.value.deleteNode(selectedNodeId.value) }
  const handleNodeSelect = (nodeId) => { selectedNodeId.value = nodeId }
  
  // Persistence Logic
  const saveCurrentFileState = (fileId) => {
      localStorage.setItem('last_analyzed_file_id', fileId)
  }
  
  const clearCurrentFileState = () => {
      localStorage.removeItem('last_analyzed_file_id')
  }

  const handleUploadComplete = (responseData) => {
    console.log("🚀 [DEBUG] handleUploadComplete CALLED with:", responseData)
    
    try {
        errorMsg.value = ''
        anomalyReport.value = ''

        // Check if processing
        if (responseData.status === 'processing') {
           console.log("Status is processing, ignoring result update.")
           isPolling.value = true
           analysisStatus.value = 'analyzing'
           showAgentWindow.value = true
           agentLogs.value = []
           analysisProgress.value = 10
           currentPhase.value = '文件上传完成，开始分析...'
           currentAnalyzingFilename.value = responseData.filename || '未知文件'
           
           setupWebSocket(responseData.file_id)
           return 
        }

        currentView.value = 'graph'
        
        // Construct safe result
        const safeResult = {
          file_id: responseData.file_id || '',
          filename: responseData.filename || 'Unknown File',
          mindmap: responseData.mindmap || { root: { topic: '无数据', children: [] } },
          knowledge_graph: responseData.knowledge_graph || { nodes: [], edges: [] },
          extracted_text: responseData.extracted_text || '',
          summary: responseData.summary || '', // [NEW] Preserve summary
          layout_data: responseData.layout_data || [],
          agent_types: responseData.agent_types || [] // [NEW] Store agent types
        }
        
        // Ensure root
        if (!safeResult.mindmap.root) {
            safeResult.mindmap = { root: safeResult.mindmap.topic ? safeResult.mindmap : { topic: '数据异常', children: [] } }
        }
        
        // [RESET] Clear previous Q&A history/state when loading a new file
        history.value = [] 
        question.value = ''
        answer.value = ''
        evidenceList.value = []
        highlightText.value = ''

        // SET THE VALUE
        analysisResult.value = safeResult
        console.log("✅ [DEBUG] analysisResult SET:", analysisResult.value)
        
        // Force rendering updates
        mindMapKey.value++ 
        isPolling.value = false // Stop polling indicator
        
        // Handle anomaly report
        if (responseData.summary && responseData.summary.includes("异常")) {
           if (responseData.extra_context) {
               anomalyReport.value = responseData.extra_context
           }
        }
        
        saveCurrentFileState(responseData.file_id)
        if (fileManager.value) fileManager.value.refreshFiles()
        
        // Auto-scroll
        nextTick(() => {
            if (resultsSection.value) {
                resultsSection.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
        })
        
    } catch (e) {
        console.error("❌ [CRITICAL] Error in handleUploadComplete:", e)
        errorMsg.value = "渲染结果出错: " + e.message
    }
  }
  
  // Restore on mount
  // Restore on mount
  // [MODIFIED] User requested to NOT auto-restore session. Commenting out.
  /*
  onMounted(async () => {
      const lastId = localStorage.getItem('last_analyzed_file_id')
      if (lastId) {
          try {
              const res = await axios.get(`/analysis/${lastId}/status`)
              if (res.data.status === 'completed') {
                  const result = res.data // Status endpoint returns direct dict or result field?
                  // In main.py: return result (the dict directly)
                  if (result) {
                      handleUploadComplete(result)
                  }
              }
          } catch (e) {
              console.error("Failed to restore session", e)
              clearCurrentFileState()
          }
      }
  })
  */

  // [NEW] WebSocket Logic
    const setupWebSocket = (fileId) => {
        if (!fileId) return
        
        // Determine WS protocol and host
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        // Use the same backend port as axios (which is configured in main.js as 8000)
        const host = 'localhost:8000' 
        const wsUrl = `${protocol}//${host}/ws/${fileId}`
        
        console.log("[DEBUG] Connecting to WS:", wsUrl)
        const ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
            console.log("[DEBUG] WebSocket Connected")
        }
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                console.log("[DEBUG] WS Message:", data)
                
                if (data.type === 'status_update') {
                    analysisStatus.value = data.status
                    analysisProgress.value = data.progress || analysisProgress.value
                    currentPhase.value = data.message
                    // Add to logs as system message
                    agentLogs.value.push({
                        type: 'status_update',
                        message: data.message,
                        timestamp: Date.now()
                    })
                } else if (data.type === 'agent_log') {
                    thinkingAgent.value = null // Stop thinking when msg arrives
                    agentLogs.value.push({
                        id: Date.now(),
                        name: data.name,
                        content: data.content,
                        type: 'agent_log',
                        timestamp: Date.now()
                    })
                } else if (data.type === 'agent_thinking') {
                    thinkingAgent.value = data.name
                    // Optionally scroll to bottom to show thinking?
                } else if (data.status === 'completed' || data.mindmap) {
                     // Finalize
                    analysisStatus.value = 'completed'
                    analysisProgress.value = 100
                    currentPhase.value = '分析完成'
                    thinkingAgent.value = null
                    
                    // Force view update
                    console.log("🔥 [WS] Analysis Completed. Calling handleUploadComplete...", data)
                    
                    // Call directly without nextTick to ensure immediate execution
                    handleUploadComplete(data)
                    
                    ws.close() // Close after success
                } else if (data.status === 'failed') {
                    errorMsg.value = `分析失败: ${data.error}`
                    analysisStatus.value = 'failed'
                    currentPhase.value = '分析失败'
                    ws.close()
                }
            } catch (e) {
                console.error("WS Parse Error", e)
            }
        }
        
        ws.onerror = (e) => {
            console.error("WS Error", e)
            // Fallback to polling or show error?
            // For now, simple error log.
        }
        
        ws.onclose = () => {
            console.log("[DEBUG] WebSocket Closed")
        }
    }

   const pollAnalysisStatus = (file_id) => {
      // Deprecated in favor of WS
      console.warn("Polling is deprecated, using WebSocket.")
   }
  
  const handleLoadHistory = (historyItem) => {
    errorMsg.value = ''
    anomalyReport.value = ''
    
    // [RESET] Clear Q&A state from previous file
    answer.value = ''
    question.value = ''
    evidenceList.value = []
    highlightText.value = ''
    
    currentView.value = 'graph'
    analysisResult.value = {
      file_id: historyItem.result.file_id || '',
      filename: historyItem.result.filename || '',
      mindmap: historyItem.result.mindmap || { topic: '无数据', children: [] },
      knowledge_graph: historyItem.result.knowledge_graph || { nodes: [], edges: [] },
      extracted_text: historyItem.result.extracted_text || '',
      summary: historyItem.result.summary || '', // [NEW] Restore summary from history
      layout_data: historyItem.result.layout_data || [], // [NEW]
      agent_types: historyItem.result.agent_types || [] // [NEW]
    }
    
    // [NEW] Load Q&A history
    fetchQAHistory(historyItem.result.file_id)
  }
  
  // [NEW] Fetch Q&A History
  const fetchQAHistory = async (file_id) => {
    try {
      if (!file_id) return
      
      // Clear current history first to avoid mixing
      history.value = []
      
      const res = await axios.get(`/api/qa-history/${file_id}`)
      if (res.data.status === 'success') {
         history.value = res.data.data.map(item => ({
             id: item.id,
             question: item.question,
             answer: item.answer,
             evidence: item.evidence || [],
             evaluation: item.evaluation
         }))
      }
    } catch (e) {
      console.error("Failed to fetch QA history", e)
    }
  }

  // [NEW] Delete Q&A Item
  const deleteQAHistoryItem = async (qa_id) => {
      if (!confirm("确定要删除这条问答记录吗？")) return
      
      try {
          await axios.delete(`/api/qa-history/${qa_id}`)
          // Remove from local list
          history.value = history.value.filter(item => item.id !== qa_id)
      } catch (e) {
          console.error("Failed to delete QA item", e)
          alert("删除失败")
      }
  }
  
  const handleHistoryDeleted = async (deletedInfo) => {
    if (deletedInfo.all || (analysisResult.value && analysisResult.value.file_id === deletedInfo.file_id)) {
      analysisResult.value = null
      cachedMindmapData.value = null
      history.value = []
      answer.value = ''
      question.value = ''
      evidenceList.value = []
      currentView.value = 'graph'
    }
    if (fileManager.value) fileManager.value.refreshFiles()
  }

  // [NEW] Locate Evidence
  const handleLocateEvidence = async (text) => {
      highlightText.value = text
      currentView.value = 'doc'
      
      // If text/log, scroll logic using mark tag
      // If PDF/Image, the component handles it via prop update
      
      // Wait for view change and render for text view
      // For PDF/Image, this might not be needed if props are reactive
      if (documentFileType.value === 'text') {
        setTimeout(() => {
            const mark = document.querySelector('mark#current-highlight')
            if (mark) {
                mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }
        }, 300)
      }
  }

  // [NEW] Computed file type helpers
  const documentFileType = computed(() => {
      if (!analysisResult.value || !analysisResult.value.filename) return 'text'
      const ext = analysisResult.value.filename.split('.').pop().toLowerCase()
      if (['pdf'].includes(ext)) return 'pdf'
      if (['jpg', 'jpeg', 'png'].includes(ext)) return 'image'
      return 'text'
  })

  // [NEW] Computed source URL (for images/PDFs)
  // We need to serve the file content. 
  // IMPORTANT: We need an endpoint to serve the file content by file_id or filename!
  // Start with: `/uploads/{filename}`? OLD logic stored in `uploads/` dir. 
  // Backend config `app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")`
  // So file URL is `/static/{file_id}.{ext}`
  const documentSourceUrl = computed(() => {
      if (!analysisResult.value) return ''
      const ext = analysisResult.value.filename.split('.').pop().toLowerCase()
      // Note: file_id is available in analysisResult
      return `http://localhost:8000/static/${analysisResult.value.file_id}.${ext}`
  })

  // [NEW] Render Document with Highlight
  const renderDocumentWithHighlight = (text) => {
      if (!text) return ''
      if (!highlightText.value) return text
      
      // Escape regex special characters
      const safeKeyword = highlightText.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      // Simple replace first occurrence (or all? usually RAG cites specific chunk)
      // Highlighting ALL occurrences might be noisy if the chunk is short/common. 
      // But RAG chunks are usually distinct sentences. Let's highlight all for now or first.
      // Let's try to highlight the exact chunk match.
      return text.replace(new RegExp(safeKeyword, 'g'), `<mark id="current-highlight" class="bg-yellow-200 text-zinc-900 rounded px-0.5">${highlightText.value}</mark>`)
  }
  
  const highlightReferences = (text) =>
    text.replace(/\[引用(\d+)\]/g, '<span class="text-blue-600 font-bold cursor-pointer hover:underline">$&</span>')
  
  // [NEW] Render Markdown content
  const renderMarkdown = (text) => {
    if (!text) return ''
    // First render markdown to HTML
    let html = md.render(text)
    // Then apply reference highlighting (simple regex replace on the resulting HTML)
    // Note: This is a simple approach. For more complex cases, a custom markdown-it plugin would be better.
    return highlightReferences(html)
  }  
  const submitQuestion = async () => {
    if (!analysisResult.value || !analysisResult.value.file_id) {
      answer.value = '请先上传并分析文件后再提问！'
      return
    }
    const trimedQuestion = question.value.trim()
    if (!trimedQuestion) return
  
    isAsking.value = true
    answer.value = ''
    evidenceList.value = []
    currentEvaluation.value = null // Reset eval
    
    try {
      const res = await axios.get('/ask', {
        params: { file_id: analysisResult.value.file_id, question: trimedQuestion },
        timeout: 60000,
        paramsSerializer: params => new URLSearchParams(params).toString()
      })
      answer.value = res.data.answer || '抱歉，未能生成答案。'
      evidenceList.value = res.data.evidence || []
      
      const newHistoryItem = { 
          id: res.data.qa_id, // [NEW] Use the persistent ID from backend
          question: trimedQuestion, 
          answer: res.data.answer,
          evidence: res.data.evidence || [],
          evaluation: null // Placeholder
      }
      history.value.push(newHistoryItem)
      const reactiveItem = history.value[history.value.length - 1] // Capture reactive proxy
      
      // Clear current answer to avoid double display
      answer.value = ''
      evidenceList.value = []
      
      question.value = ''
      
      // [Async] Trigger Evaluation
      const contextText = reactiveItem.evidence.map(e => e.text).join('\n')
      axios.post('/evaluate', {
          question: trimedQuestion,
          answer: res.data.answer,
          context: contextText || "无上下文"
      }).then(evalRes => {
          currentEvaluation.value = evalRes.data
          // Update history item (must update reactive proxy)
          reactiveItem.evaluation = evalRes.data
      }).catch(e => console.error("Eval failed", e))
      
    } catch (err) {
      console.error('问答请求失败:', err)
      answer.value = err.response ? `错误 [${err.response.status}]` : '请求超时或服务未响应'
    } finally {
      isAsking.value = false
    }
  }
  
  const exportDropdown = ref('')
  const toggleExportDropdown = (type) => {
    exportDropdown.value = exportDropdown.value === type ? '' : type
  }
  
  const handleExportMindMap = (format = 'json') => {
    if (mindMapComponent.value) mindMapComponent.value.exportMindMap(format)
    exportDropdown.value = ''
  }
  
  const handleImportFile = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const jsonData = JSON.parse(e.target.result)
        handleImportSuccess(jsonData.mindmap)
        event.target.value = ''
      } catch (err) {
        alert('解析错误')
      }
    }
    reader.readAsText(file)
  }
  
  const handleImportSuccess = (mindmapData) => {
    if (analysisResult.value) analysisResult.value.mindmap = mindmapData
    else analysisResult.value = { file_id: 'imported', filename: 'Imported', mindmap: mindmapData, knowledge_graph: { nodes: [], edges: [] }, extracted_text: '' }
    currentView.value = 'graph'
  }
  

  const handleExportData = (d) => console.log('Export:', d)
  const handleNodeUpdate = (updateData) => {
  console.log('节点更新:', updateData)
  
  if (!analysisResult.value || !analysisResult.value.mindmap) return
  
  // 辅助函数：根据ID查找节点
  const findNode = (node, id) => {
    if (node.id === id) return node
    if (node.children) {
      for (const child of node.children) {
        const found = findNode(child, id)
        if (found) return found
      }
    }
    return null
  }
  
  // 辅助函数：深拷贝对象
  const deepCopy = (obj) => JSON.parse(JSON.stringify(obj))
  
  // 深拷贝思维导图数据，避免直接修改原始数据
  const mindmapCopy = deepCopy(analysisResult.value.mindmap)
  
  // 确保思维导图数据结构正确
  let root = mindmapCopy.root
  if (!root) {
    // 如果没有root，尝试使用其他结构
    root = mindmapCopy.rootTopic ? { id: 'root', topic: mindmapCopy.rootTopic, children: mindmapCopy.children || [] } : { id: 'root', topic: '默认主题', children: [] }
    mindmapCopy.root = root
  }
  
  if (updateData.action === 'add') {
    // 添加节点
    const parent = findNode(root, updateData.parentId)
    if (parent) {
      if (!parent.children) parent.children = []
      parent.children.push(updateData.newNode)
      // 更新结果数据
      analysisResult.value.mindmap = mindmapCopy
      // 更新缓存数据
      cachedMindmapData.value = null
    }
  } else if (updateData.action === 'delete') {
    // 删除节点
    const removeNode = (parent, id) => {
      if (parent.children) {
        const index = parent.children.findIndex(child => child.id === id)
        if (index !== -1) {
          parent.children.splice(index, 1)
          return true
        }
        for (const child of parent.children) {
          if (removeNode(child, id)) return true
        }
      }
      return false
    }
    removeNode(root, updateData.nodeId)
    // 更新结果数据
    analysisResult.value.mindmap = mindmapCopy
    // 更新缓存数据
    cachedMindmapData.value = null
  } else if (updateData.topic) {
    // 更新节点内容
    const node = findNode(root, updateData.nodeId)
    if (node) {
      node.topic = updateData.topic
      // 更新结果数据
      analysisResult.value.mindmap = mindmapCopy
      // 更新缓存数据
      cachedMindmapData.value = null
    }
  }
}
  const handleNodeMove = (d) => { /* 保留 */ }
  
  const handleExportKnowledgeGraph = (format = 'json') => {
    if (knowledgeGraphComponent.value) knowledgeGraphComponent.value.exportKnowledgeGraph(format)
    exportDropdown.value = ''
  }
  
  const handleImportKnowledgeGraphFile = async (event) => { /* 保留 */ }
  const handleKnowledgeGraphImport = (d) => { if (knowledgeGraphComponent.value) knowledgeGraphComponent.value.importKnowledgeGraph(d) }
  const handleKnowledgeGraphImportSuccess = (d) => { /* 保留 */ }
  const handleKnowledgeGraphExportData = (d) => { /* 保留 */ }
  </script>
  
  <template>
    <div class="space-y-6 pb-20">
    
      <!-- Agent Analysis Window -->
      <AgentAnalysisWindow 
        :is-visible="showAgentWindow"
        :logs="agentLogs"
        :status="analysisStatus"
        :progress="analysisProgress"
        :current-phase="currentPhase"
        :thinking-agent="thinkingAgent"
        :filename="currentAnalyzingFilename"
        @close="showAgentWindow = false"
      />
  
      <!-- header -->
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-xl font-semibold text-zinc-900">智能文档分析</h2>
          <p class="text-sm text-zinc-500 mt-1">上传文档，生成思维导图与知识图谱，并进行深度问答。</p>
  
          <p v-if="errorMsg" class="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
            {{ errorMsg }}
          </p>
        </div>
  

        <div class="flex items-center gap-3">
             <!-- Brain Manager Button -->
             <button v-if="analysisResult" 
                     @click="() => currentFileId && $router.push(`/brain?file_id=${currentFileId}`)"
                     class="flex items-center gap-2 px-4 py-2 bg-pink-50 text-pink-700 rounded-lg text-sm font-medium hover:bg-pink-100 transition-colors border border-pink-100 shadow-sm"
             >
                 <Brain :size="16" />
                 <span>知识库管理</span>
             </button>

            <div v-if="analysisResult" class="hidden md:flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium border border-emerald-100 animate-fade-in-up">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              当前分析：{{ analysisResult.filename }}
            </div>
            <div v-else-if="isPolling || showAgentWindow" class="hidden md:flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium border border-blue-100">
                 <Loader2 :size="12" class="animate-spin" />
                 正在后台深入分析中...
            </div>
        </div>
        
        <!-- [NEW] Manual Refresh Trigger (Fallback) -->
         <button v-if="!analysisResult && !isPolling" @click="fileManager && fileManager.refreshFiles()" class="text-xs text-zinc-400 hover:text-zinc-600 underline">
            刷新状态
         </button>
      </div>
  
      <!-- Top Grid -->
      <div class="grid grid-cols-1 gap-6">




  <!-- 上传新文件 -->
  <div class="card overflow-hidden flex flex-col">
    <div class="p-4 border-b border-zinc-100 bg-zinc-50/50 flex items-center gap-2">
      <Upload :size="16" class="text-zinc-500" />
      <span class="text-sm font-medium text-zinc-700">上传新文件</span>
    </div>
    <div class="p-4">
      <FileUploader
        @upload-complete="handleUploadComplete"
        @upload-error="handleUploadError"
      />
    </div>
  </div>

  <!-- 文件库 -->
  <div class="card overflow-hidden flex flex-col">
    <div class="p-4 border-b border-zinc-100 bg-zinc-50/50 flex items-center gap-2">
      <FileJson :size="16" class="text-zinc-500" />
      <span class="text-sm font-medium text-zinc-700">文件库</span>
    </div>
    <div class="p-2">
      <FileManager ref="fileManager" :file-type="null" />
    </div>
  </div>

  <!-- 历史记录 -->
  <div class="card overflow-hidden flex flex-col">
    <div class="p-4 border-b border-zinc-100 bg-zinc-50/50 flex items-center gap-2">
      <Search :size="16" class="text-zinc-500" />
      <span class="text-sm font-medium text-zinc-700">历史记录</span>
    </div>
    <div class="p-2">
      <HistoryManager
        ref="historyManager"
        @load-history="handleLoadHistory"
        @history-deleted="handleHistoryDeleted"
      />
    </div>
  </div>

</div>

  
      <!-- main section -->
      <section v-if="analysisResult" ref="resultsSection" class="space-y-4 animate-fade-in-up">
  
        <!-- tab switch -->
        <div class="flex justify-center">
          <div class="bg-zinc-100 p-1 rounded-lg inline-flex shadow-inner">
            <button
              @click="currentView = 'graph'"
              class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-medium transition-all duration-200"
              :class="currentView === 'graph' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'"
            >
              <Network :size="16" />
              <span>全景图谱</span>
            </button>
  
            <button
              @click="currentView = 'qa'"
              class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-medium transition-all duration-200"
              :class="currentView === 'qa' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'"
            >
              <MessageSquareText :size="16" />
              <span>智能问答</span>
            </button>

            <!-- [NEW] Report Tab -->
            <button
              @click="currentView = 'report'"
              class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-medium transition-all duration-200"
              :class="currentView === 'report' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'"
            >
              <Bot :size="16" />
              <span>深度分析</span>
            </button>

            <button
              @click="currentView = 'doc'"
              class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-medium transition-all duration-200"
              :class="currentView === 'doc' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'"
            >
              <FileText :size="16" />
              <span>文档原文</span>
            </button>

            <!-- [NEW] Peer Review Tab (Conditionally shown for academic papers) -->
            <button
              v-if="analysisResult?.agent_types?.includes('academic')"
              @click="handleReviewTabClick"
              class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-medium transition-all duration-200"
              :class="currentView === 'review' ? 'bg-white text-purple-700 shadow-sm' : 'text-zinc-500 hover:text-purple-700'"
            >
              <Award :size="16" />
              <span>AI 同行评审</span>
            </button>
          </div>
        </div>
  
        <!-- report view -->
        <div v-if="currentView === 'report'" class="grid grid-cols-1 animate-fade-in-up">
           <div class="card p-8 bg-white/80 backdrop-blur-xl border border-white/40 shadow-xl rounded-2xl">
               <div class="prose prose-sm md:prose-base max-w-none prose-zinc dark:prose-invert">
                   <div v-html="renderMarkdown(analysisResult.summary || '暂无分析总结。')"></div>
               </div>
           </div>
        </div>



        <!-- graph view -->
        <div
          v-if="currentView === 'graph'"
          class="grid grid-cols-1 gap-6 2xl:grid-cols-2 items-stretch"
        >
  
          <!-- mindmap -->
          <div class="card overflow-hidden flex flex-col h-[520px]">
            <div class="h-14 border-b border-zinc-100 px-4 flex items-center justify-between bg-zinc-50/30">
              <div class="flex items-center gap-2 text-zinc-700 font-medium">
                <div class="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 grid place-items-center">
                  <Network :size="18" />
                </div>
                思维导图
              </div>
  
              <div class="flex items-center gap-1">
                <input type="file" ref="importFileInput" class="hidden" accept=".json" @change="handleImportFile" />
  
                <div class="flex items-center bg-zinc-100 rounded-lg p-1 gap-1">
                  <button @click="$refs.importFileInput.click()" :disabled="!isMindMapValid" class="tool-btn" title="导入">
                    <Upload :size="14" />
                  </button>
  
                  <div class="relative">
                    <button @click="toggleExportDropdown('mindmap')" :disabled="!isMindMapValid" class="tool-btn" title="导出">
                      <Download :size="14" />
                    </button>
  
                    <div
                      v-if="exportDropdown === 'mindmap'"
                      class="absolute right-0 top-full mt-2 w-32 bg-white border border-zinc-200 rounded-lg shadow-xl z-50 py-1 overflow-hidden"
                    >
                      <button @click="handleExportMindMap('json')" class="dropdown-item">
                        <FileJson :size="12" /> JSON
                      </button>
                      <button @click="handleExportMindMap('png')" class="dropdown-item">
                        <ImageIcon :size="12" /> PNG
                      </button>
                      <button @click="handleExportMindMap('jpeg')" class="dropdown-item">
                        <ImageIcon :size="12" /> JPEG
                      </button>
                    </div>
                  </div>
  
                  <div class="w-px h-4 bg-zinc-300 mx-1"></div>
  
                  <button @click="handleAddNode" :disabled="!isMindMapValid" class="tool-btn hover:text-blue-600" title="增加节点">
                    <Plus :size="14" />
                  </button>
                  <button @click="handleDeleteNode" :disabled="!isMindMapValid" class="tool-btn hover:text-red-600" title="删除节点">
                    <Minus :size="14" />
                  </button>
                </div>
              </div>
            </div>
  
            <div class="flex-1 bg-zinc-50 relative overflow-hidden">
              <MindMap
                ref="mindMapComponent"
                :key="mindMapKey" 
                v-if="isMindMapValid && mindmapDataForComponent"
                :dataObj="mindmapDataForComponent"
                @import-success="handleImportSuccess"
                @export-data="handleExportData"
                @node-update="handleNodeUpdate"
                @node-move="handleNodeMove"
                @node-select="handleNodeSelect"
              />
              <div v-show="!isMindMapValid || !mindmapDataForComponent" class="absolute inset-0 flex flex-col items-center justify-center text-zinc-400">
                <Network :size="48" class="mb-2 opacity-20" />
                <span>{{ isMindMapValid ? '加载中...' : '等待数据...' }}</span>
              </div>
            </div>
          </div>
  
          <!-- knowledge graph -->
          <!-- knowledge graph -->
          <div class="card overflow-hidden flex flex-col h-[520px]">
            <div class="h-14 border-b border-zinc-100 px-4 flex items-center justify-between bg-zinc-50/30">
              <div class="flex items-center gap-2 text-zinc-700 font-medium">
                <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 grid place-items-center">
                  <Share2 :size="18" />
                </div>
                知识图谱
              </div>
  
              <div class="flex items-center gap-1">
                <input type="file" ref="importKnowledgeGraphInput" class="hidden" accept=".json" @change="handleImportKnowledgeGraphFile" />
                <div class="flex items-center bg-zinc-100 rounded-lg p-1 gap-1">
                  <button @click="$refs.importKnowledgeGraphInput.click()" :disabled="!isKnowledgeGraphValid" class="tool-btn" title="导入">
                    <Upload :size="14" />
                  </button>
  
                  <div class="relative">
                    <button @click="toggleExportDropdown('knowledgegraph')" :disabled="!isKnowledgeGraphValid" class="tool-btn" title="导出">
                      <Download :size="14" />
                    </button>
  
                    <div
                      v-if="exportDropdown === 'knowledgegraph'"
                      class="absolute right-0 top-full mt-2 w-32 bg-white border border-zinc-200 rounded-lg shadow-xl z-50 py-1 overflow-hidden"
                    >
                      <button @click="handleExportKnowledgeGraph('json')" class="dropdown-item">
                        <FileJson :size="12" /> JSON
                      </button>
                      <button @click="handleExportKnowledgeGraph('png')" class="dropdown-item">
                        <ImageIcon :size="12" /> PNG
                      </button>
                      <button @click="handleExportKnowledgeGraph('jpeg')" class="dropdown-item">
                        <ImageIcon :size="12" /> JPEG
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
  
            <div class="flex-1 bg-zinc-50 relative overflow-hidden">
              <KnowledgeGraph
                ref="knowledgeGraphComponent"
                v-if="isKnowledgeGraphValid"
                :data="knowledgeGraphData"
                @import-success="handleKnowledgeGraphImportSuccess"
                @export-data="handleKnowledgeGraphExportData"
              />
              <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-zinc-400">
                <Share2 :size="48" class="mb-2 opacity-20" />
                <span>{{ isKnowledgeGraphValid ? '加载中...' : '等待数据...' }}</span>
              </div>
            </div>
          </div>
        </div>
  
        <!-- qa view -->
        <div v-if="currentView === 'qa'" class="mx-auto max-w-4xl">
          <div class="card overflow-hidden flex flex-col min-h-[600px]">
  
            <div class="p-6 border-b border-zinc-100 flex items-center gap-3">
              <div class="h-10 w-10 rounded-full bg-zinc-900 text-white grid place-items-center shadow-lg shadow-zinc-200">
                <Bot :size="20" />
              </div>
              <div>
                <h3 class="font-semibold text-zinc-900">AI Assistant</h3>
                <p class="text-xs text-zinc-500">基于 《{{ analysisResult.filename }}》 进行回答</p>
              </div>
            </div>
  
            <div class="flex-1 p-6 space-y-6 overflow-y-auto bg-zinc-50/50">
              <!-- History Items -->
              <div v-for="(item, idx) in history" :key="item.id" class="space-y-4 opacity-90 transition-opacity">
                <div class="flex justify-end group"> <!-- Added group for hover effect -->
                  <div class="bg-zinc-900 text-white px-4 py-2 rounded-2xl rounded-tr-sm max-w-[80%] text-sm relative">
                    {{ item.question }}
                    <!-- Delete Button (Visible on hover) -->
                    <button 
                        @click="deleteQAHistoryItem(item.id)"
                        class="absolute -left-8 top-1/2 -translate-y-1/2 p-1.5 text-zinc-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="删除记录"
                    >
                        <Trash2 :size="14" />
                    </button>
                  </div>
                </div>
                <div class="flex justify-start">
                  <div class="max-w-[90%] space-y-2">
                    <div
                      class="bg-white border border-zinc-200 text-zinc-700 px-4 py-3 rounded-2xl rounded-tl-sm text-sm shadow-sm prose prose-sm max-w-none"
                      v-html="renderMarkdown(item.answer)"
                    ></div>
                    
                    <!-- Evaluation & Feedback -->
                    <EvaluationScore 
                      v-if="item.evaluation" 
                      :faithfulness="item.evaluation.faithfulness_score"
                      :relevancy="item.evaluation.relevancy_score"
                      :reason="item.evaluation.reason"
                    />

                    <!-- History Item Evidence -->
                    <div v-if="item.evidence && item.evidence.length" class="bg-blue-50/50 border border-blue-100 rounded-xl p-3 space-y-2 mt-2">
                      <div class="text-xs font-bold text-blue-700 flex items-center gap-1">
                        <Search :size="12" /> 引用来源 (点击定位)
                      </div>
                      <div
                        v-for="(evidence, index) in item.evidence"
                        :key="index"
                        class="text-xs text-blue-900/70 bg-white/60 p-2 rounded border border-blue-100 cursor-pointer hover:bg-white hover:border-blue-300 hover:shadow-sm transition-all group/evidence"
                        @click="handleLocateEvidence(evidence.text)"
                        title="点击查看原文"
                      >
                        <div class="flex items-start gap-1">
                            <span class="font-medium shrink-0">[P{{ evidence.page }}]</span>
                            <span class="group-hover/evidence:text-blue-700">{{ evidence.text }}</span>
                        </div>
                      </div>
                    </div>

                    <FeedbackWidget 
                      :file-id="analysisResult.file_id"
                      :qa-id="item.id"
                      :question="item.question"
                      :answer="item.answer"
                    />
                  </div>
                </div>
              </div>
  
              <!-- Current Result -->
              <div v-if="answer" class="space-y-4">
                <div class="flex justify-start gap-3">
                  <div class="h-8 w-8 rounded-full bg-emerald-100 text-emerald-600 grid place-items-center shrink-0 mt-1">
                    <Bot :size="16" />
                  </div>
                  <div class="space-y-3 max-w-[90%]">
                    <div
                      class="bg-white border border-zinc-200 text-zinc-700 px-4 py-3 rounded-2xl rounded-tl-sm text-sm shadow-sm"
                      v-html="highlightReferences(answer)"
                    ></div>
  
                    <div v-if="evidenceList.length" class="bg-blue-50/50 border border-blue-100 rounded-xl p-3 space-y-2">
                      <div class="text-xs font-bold text-blue-700 flex items-center gap-1">
                        <Search :size="12" /> 引用来源 (点击定位)
                      </div>
                      <div
                        v-for="(evidence, index) in evidenceList"
                        :key="index"
                        class="text-xs text-blue-900/70 bg-white/60 p-2 rounded border border-blue-100 cursor-pointer hover:bg-white hover:border-blue-300 hover:shadow-sm transition-all group/evidence"
                        @click="handleLocateEvidence(evidence.text)"
                         title="点击查看原文"
                      >
                        <div class="flex items-start gap-1">
                            <span class="font-medium shrink-0">[P{{ evidence.page }}]</span>
                            <span class="group-hover/evidence:text-blue-700">{{ evidence.text }}</span>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Eval (Current) -->
                    <EvaluationScore 
                      v-if="currentEvaluation" 
                      :faithfulness="currentEvaluation.faithfulness_score"
                      :relevancy="currentEvaluation.relevancy_score"
                      :reason="currentEvaluation.reason"
                    />
                    <!-- Feedback (Current) - Disabled to avoid 422 errors (no qa_id) -->
                    <!-- 
                    <FeedbackWidget 
                      v-if="!isAsking"
                      :file-id="analysisResult.file_id"
                      :question="question" 
                      :answer="answer"
                    />
                    -->
                  </div>
                </div>
              </div>
            </div>
  
            <div v-if="anomalyReport" class="p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-3 text-amber-800 text-sm mb-4">
              <AlertTriangle :size="20" class="shrink-0 mt-0.5" />
              <div>
                <div class="font-bold">⚠️ 日志异常检测报告</div>
                <div class="whitespace-pre-wrap mt-1">{{ anomalyReport }}</div>
              </div>
            </div>

            <div class="p-4 bg-white border-t border-zinc-200">
              <div class="relative">
                <textarea
                  v-model="question"
                  placeholder="询问关于文档的问题..."
                  class="w-full bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-400 transition resize-none"
                  rows="1"
                  @keydown.enter.prevent="submitQuestion"
                ></textarea>
  
                <button
                  @click="submitQuestion"
                  :disabled="!question.trim() || isAsking"
                  class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-2 rounded-lg bg-zinc-900 text-white hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  title="发送"
                >
                  <Loader2 v-if="isAsking" :size="16" class="animate-spin" />
                  <ArrowUp v-else :size="16" />
                </button>
              </div>
  
              <p class="text-[10px] text-center text-zinc-400 mt-2">AI 可能会产生错误信息，请核对重要事实。</p>
            </div>
          </div>
        </div>
        <!-- Document View -->
        <div v-if="currentView === 'doc'" class="mx-auto max-w-4xl">
             <div class="card overflow-hidden flex flex-col h-[700px]">
                <div class="p-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
                    <div class="flex items-center gap-2">
                        <FileText :size="18" class="text-zinc-600"/>
                        <span class="font-medium text-zinc-900">文档全文 ({{ documentFileType.toUpperCase() }})</span>
                    </div>
                    <div v-if="highlightText" class="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded border border-yellow-200">
                        正在定位: {{ highlightText.slice(0, 10) }}...
                    </div>
                </div>
                
                <div class="flex-1 overflow-hidden relative bg-white">
                    <!-- PDF Viewer -->
                    <PDFViewer 
                        v-if="documentFileType === 'pdf'"
                        :source="documentSourceUrl"
                        :layout-data="analysisResult.layout_data"
                        :highlight-text="highlightText"
                    />

                    <!-- Image Viewer -->
                    <ImageViewer
                        v-else-if="documentFileType === 'image'"
                        :source="documentSourceUrl"
                        :layout-data="analysisResult.layout_data"
                        :highlight-text="highlightText"
                    />

                    <!-- Text/Log Viewer (Fallback) -->
                    <div 
                        v-else 
                        class="h-full overflow-y-auto p-8 prose prose-zinc max-w-none text-sm font-mono whitespace-pre-wrap selection:bg-blue-100"
                        v-html="renderDocumentWithHighlight(analysisResult.extracted_text)"
                        ref="docViewRef"
                    ></div>
                </div>
             </div>
        </div>

        <!-- Review View -->
        <div v-if="currentView === 'review'" class="mx-auto max-w-4xl animate-fade-in-up">
            <div v-if="isReviewLoading" class="flex flex-col items-center justify-center h-[400px] text-zinc-500">
                <Loader2 :size="48" class="animate-spin mb-4 text-purple-600" />
                <p class="text-lg font-medium">AI 评审专家正在审阅论文...</p>
                <p class="text-sm opacity-70">评估创新性、方法论与实验严谨性</p>
            </div>
            <ReviewScoreCard v-else-if="reviewData" :reviewData="reviewData" />
            <div v-else class="text-center p-12 text-zinc-400">
                <p>暂无评审数据，请点击刷新重试。</p>
            </div>
        </div>

      </section>
    </div>
  </template>
  
  <style scoped>
  /* 淡入上浮动画 */
  .animate-fade-in-up {
    animation: fadeInUp 0.5s ease-out;
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  /* 滚动条 */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: #e4e4e7;
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #d4d4d8;
  }
  </style>
  