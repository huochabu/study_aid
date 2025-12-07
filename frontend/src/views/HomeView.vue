<template>
  <div class="home-container">
    <header class="header">
      <h1>🧠 DocMind Pro - 智能文档分析系统</h1>
    </header>

    <section class="upload-section">
      <h2>📤 上传文档</h2>
      <div class="upload-box">
        <input 
          ref="fileInput" 
          type="file" 
          @change="handleFileSelect" 
          accept=".pdf,.txt,.log,.jpg,.jpeg,.png"
          class="file-input"
        />
        <p v-if="selectedFileName" class="file-name">已选择: {{ selectedFileName }}</p>
        <button 
          @click="handleUpload" 
          :disabled="!selectedFile || isLoading"
          class="upload-btn"
        >
          {{ isLoading ? '🔄 AI分析中...' : '🚀 开始分析' }}
        </button>
        <p v-if="errorMsg" class="error-msg">❌ {{ errorMsg }}</p>
      </div>
    </section>

    <section v-if="analysisResult" class="result-section">
      <div class="view-toggle">
        <button 
          @click="currentView = 'graph'" 
          :class="{ active: currentView === 'graph' }"
          class="toggle-btn"
        >
          📊 查看图谱
        </button>
        <button 
          @click="currentView = 'qa'" 
          :class="{ active: currentView === 'qa' }"
          class="toggle-btn"
        >
          💬 智能问答
        </button>
      </div>

      <!-- 核心修复：强制两栏等高 + 等宽 -->
      <div v-if="currentView === 'graph'" class="result-grid">
        <!-- 左侧思维导图卡片 -->
        <div class="result-card">
          <h3>🧠 思维导图</h3>
          <div class="graph-content">
            <MindMap 
              v-if="isMindMapValid && mindmapDataForComponent" 
              :dataObj="mindmapDataForComponent"
            />
            <div v-else class="loading-placeholder">
              ⏳ {{ isMindMapValid ? '加载中...' : '数据格式异常' }}
            </div>
          </div>
        </div>

        <!-- 右侧知识图谱卡片 -->
        <div class="result-card">
          <h3>🔍 知识图谱</h3>
          <div class="graph-content">
            <KnowledgeGraph 
              v-if="isKnowledgeGraphValid" 
              :data="knowledgeGraphData"
            />
            <div v-else class="loading-placeholder">
              ⏳ {{ isKnowledgeGraphValid ? '加载中...' : '数据格式异常' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 问答视图 -->
      <div v-if="currentView === 'qa'" class="qa-view">
        <h2>💬 基于《{{ analysisResult.filename }}》的智能问答</h2>
        <div class="input-section">
          <label>请输入问题：</label>
          <textarea
            v-model="question"
            placeholder="例如：合同的有效期是多久？"
            rows="3"
            maxlength="500"
          ></textarea>
          <button 
            @click="submitQuestion" 
            :disabled="!question.trim() || isAsking"
            class="ask-btn"
          >
            {{ isAsking ? '🤔 回答中...' : '提问' }}
          </button>
        </div>

        <div v-if="answer" class="result-section">
          <h3>回答：</h3>
          <div class="answer-text" v-html="highlightReferences(answer)"></div>
          <h3>引用来源：</h3>
          <div v-for="(evidence, index) in evidenceList" :key="index" class="evidence-item">
            <strong>[引用{{ index + 1 }}]</strong>
            <p><em>来源：{{ evidence.source }} 第{{ evidence.page }}页</em></p>
            <p>{{ evidence.text }}</p>
          </div>
        </div>

        <div v-if="history.length > 0" class="history-section">
          <h3>历史记录：</h3>
          <ul>
            <li v-for="(item, idx) in history" :key="idx" @click="loadHistory(item)">
              {{ item.question }}
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import MindMap from '@/components/MindMap.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'

// 状态、数据预处理、上传/问答逻辑保持不变
const fileInput = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const isLoading = ref(false)
const errorMsg = ref('')
const analysisResult = ref(null)

const currentView = ref('graph')
const question = ref('')
const answer = ref('')
const evidenceList = ref([])
const history = ref([])
const isAsking = ref(false)

const mindmapDataForComponent = computed(() => {
  const raw = analysisResult.value?.mindmap
  if (!raw) return null
  if (raw.rootTopic && !raw.root) {
    return { root: { id: 'root', topic: raw.rootTopic, children: Array.isArray(raw.children) ? raw.children : [] } }
  }
  if (raw.root && typeof raw.root === 'object') return raw
  return { root: { id: raw.id || 'root', topic: raw.topic || '默认主题', children: Array.isArray(raw.children) ? raw.children : [] } }
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
  const data = knowledgeGraphData.value
  return data && typeof data === 'object' && Array.isArray(data.nodes) && Array.isArray(data.edges)
})

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    selectedFileName.value = file.name
    errorMsg.value = ''
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) return
  isLoading.value = true
  errorMsg.value = ''
  analysisResult.value = null
  currentView.value = 'graph'
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  try {
    const response = await axios.post('http://127.0.0.1:8000/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 450000,
      transformResponse: [(data) => {
        try { return JSON.parse(data) } 
        catch (e) {
          console.error('JSON解析失败:', e);
          return { mindmap: { topic: '解析失败', children: [] }, knowledge_graph: { nodes: [], edges: [] } }
        }
      }]
    })
    const safeResult = {
      file_id: response.data.file_id || '',
      filename: response.data.filename || selectedFileName.value,
      mindmap: response.data.mindmap || { topic: '无数据', children: [] },
      knowledge_graph: response.data.knowledge_graph || { nodes: [], edges: [] },
      extracted_text: response.data.extracted_text || ''
    }
    analysisResult.value = safeResult
    if (fileInput.value) fileInput.value.value = ''
    selectedFileName.value = ''
  } catch (err) {
    analysisResult.value = { mindmap: { topic: '上传失败', children: [] }, knowledge_graph: { nodes: [], edges: [] } }
    errorMsg.value = err.response?.data ? `请求失败：${err.response.data}` : '后端服务未响应'
  } finally { isLoading.value = false }
}

const highlightReferences = (text) => text.replace(/\[引用(\d+)\]/g, '<span class="ref">$&</span>')

// ✅ 核心修复：新增超时配置 + 详细错误日志 + 参数校验
const submitQuestion = async () => {
  // 1. 严格参数校验
  if (!analysisResult.value) {
    answer.value = '请先上传并分析文件后再提问！'
    return
  }
  if (!analysisResult.value.file_id) {
    answer.value = '文件ID不存在，请重新上传文件！'
    return
  }
  const trimedQuestion = question.value.trim()
  if (!trimedQuestion) {
    answer.value = '问题不能为空，请输入有效问题！'
    return
  }

  isAsking.value = true
  answer.value = ''
  evidenceList.value = []
  try {
    // 2. 添加超时配置（60秒）+ 完整错误捕获
    const res = await axios.get('http://127.0.0.1:8000/ask', {
      params: { 
        file_id: analysisResult.value.file_id, 
        question: trimedQuestion 
      },
      timeout: 60000, // ✅ 新增：60秒超时
      // ✅ 新增：确保参数正确编码
      paramsSerializer: params => {
        return new URLSearchParams(params).toString()
      }
    })
    answer.value = res.data.answer || '抱歉，未能生成答案。'
    evidenceList.value = res.data.evidence || []
    history.value.unshift({ question: trimedQuestion, answer: res.data.answer })
    question.value = ''
  } catch (err) {
    // ✅ 新增：详细错误信息提示
    console.error('问答请求失败:', err)
    if (err.response) {
      // 后端返回错误（404/500等）
      answer.value = `问答请求失败 [${err.response.status}]：${err.response.data?.detail || '接口不存在或参数错误'}`
    } else if (err.request) {
      // 请求已发送但无响应
      answer.value = '问答请求超时：后端服务未响应，请检查后端是否运行'
    } else {
      // 请求构建错误
      answer.value = `请求构建失败：${err.message}`
    }
  } finally {
    isAsking.value = false
  }
}

const loadHistory = (item) => { 
  question.value = item.question; 
  answer.value = item.answer 
}
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
  min-height: 100vh;
  box-sizing: border-box;
}

.header { text-align: center; margin-bottom: 30px; }

.upload-section { margin-bottom: 40px; }
.upload-box { padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background: #f9f9f9; }
.file-input { margin-bottom: 10px; padding: 8px; width: 100%; }
.file-name { margin: 10px 0; color: #666; }
.upload-btn { padding: 10px 20px; background: #1890ff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
.upload-btn:disabled { background: #999; cursor: not-allowed; }
.error-msg { color: #ff4d4f; margin: 10px 0 0 0; }

.result-section { margin-top: 30px; }

/* 核心修复：强制两栏等宽 + 等高 */
.result-grid {
  display: flex;
  gap: 20px;
  width: 100%;
  min-height: 800px; /* 基础高度 */
  height: calc(100vh - 220px); /* 强制高度 = 视口高度 - 顶部区域高度 */
}

/* 强制每个卡片尺寸完全一致 */
.result-card {
  flex: 1;
  min-width: 0; /* 解决内容溢出导致宽度不一致 */
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  display: flex;
  flex-direction: column;
  height: 100%; /* 占满父容器高度 */
}

.result-card h3 {
  margin: 0 0 10px 0;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

/* 核心修复：内部内容容器强制占满高度 */
.graph-content {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #f9fafb;
  border-radius: 8px;
  overflow: auto; /* 内容超出时滚动 */
}

.loading-placeholder {
  width: 100%;
  height: 100%;
  display:flex;
  align-items:center;
  justify-content:center;
  color:#999;
  font-size:16px;
}

.view-toggle { margin-bottom: 20px; text-align: center; }
.toggle-btn { padding: 8px 16px; margin: 0 8px; border: 1px solid #ccc; background: #f5f5f5; border-radius: 4px; cursor: pointer; }
.toggle-btn.active { background: #1890ff; color: white; border-color: #1890ff; }

.qa-view { padding: 20px; background: #fafafa; border-radius: 8px; }
.input-section { margin: 15px 0; }
.input-section textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; resize: vertical; }
.ask-btn { margin-top: 10px; padding: 8px 16px; background: #52c41a; color: white; border: none; border-radius: 4px; cursor: pointer; }
.ask-btn:disabled { background: #bfbfbf; cursor: not-allowed; }

.answer-text { line-height: 1.6; margin: 10px 0; }
.ref { color: #1890ff; font-weight: bold; }
.evidence-item { margin: 10px 0; padding: 10px; background: white; border: 1px solid #eee; border-radius: 4px; }

.history-section ul { list-style: none; padding: 0; }
.history-section li { padding: 8px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
.history-section li:hover { background: #f0f0f0; }
</style>