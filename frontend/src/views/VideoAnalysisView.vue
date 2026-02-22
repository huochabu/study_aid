<template>
  <div class="page">
    <!-- Header -->
    <header class="header">
      <div class="header-title">
        <h1>智能视频分析</h1>
        <p>输入 BV号 / 视频URL，选择任务类型，生成信息、摘要、思维导图、问答与笔记。</p>
      </div>
    </header>

    <!-- Input -->
    <section class="card">
      <div class="card-hd">
        <div class="card-hd-title">
          <span class="dot"></span>
          视频分析参数
        </div>
      </div>

      <div class="card-bd">
        <form class="form" @submit.prevent="processVideo">
          <div class="field">
            <label for="videoId">视频ID / BV号 / URL</label>
            <input
              id="videoId"
              v-model.trim="formData.videoId"
              type="text"
              placeholder="例如：BV1xx411c7mD 或 https://www.bilibili.com/video/BV..."
              autocomplete="off"
              required
            />
          </div>

          <div class="field">
            <label for="taskType">任务类型</label>
            <select id="taskType" v-model="formData.taskType" required>
              <option value="play">播放（获取视频信息）</option>
              <option value="summary">视频摘要</option>
              <option value="mindmap">思维导图</option>
              <option value="qa">视频问答</option>
              <option value="notes">笔记生成</option>
            </select>
          </div>

          <div class="field" v-if="formData.taskType === 'qa'">
            <label for="question">问题</label>
            <textarea
              id="question"
              v-model.trim="formData.question"
              placeholder="请输入你想问视频内容的问题"
              rows="3"
              required
            ></textarea>
          </div>

          <div class="actions">
            <button class="btn primary" type="submit" :disabled="loading">
              <span v-if="loading">处理中…</span>
              <span v-else>开始分析</span>
            </button>

            <button
              class="btn ghost"
              type="button"
              :disabled="loading"
              @click="resetAll"
              title="清空输入与结果"
            >
              清空
            </button>
          </div>
        </form>

        <p v-if="error" class="alert">
          {{ error }}
        </p>
      </div>
    </section>

    <!-- Result -->
    <section v-if="result" class="card">
      <div class="card-hd">
        <div class="card-hd-title">
          <span class="dot"></span>
          分析结果
        </div>
        <div class="card-hd-sub" v-if="resultMetaText">{{ resultMetaText }}</div>
      </div>

      <div class="card-bd">
        <!-- Play -->
        <div v-if="formData.taskType === 'play'" class="panel">
          <div class="panel-title">{{ result?.data?.title || '视频信息' }}</div>

          <div class="video-frame">
            <iframe
              v-if="result?.data?.embed_url"
              :src="result.data.embed_url"
              class="video-player"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            ></iframe>
            <div v-else class="empty">
              没有可用的 embed_url
            </div>
          </div>

          <div class="kv">
            <div class="kv-item">
              <div class="k">UP主</div>
              <div class="v">{{ result?.data?.author || '-' }}</div>
            </div>
            <div class="kv-item">
              <div class="k">时长</div>
              <div class="v">{{ result?.data?.duration || '-' }}</div>
            </div>
          </div>

          <div class="desc" v-if="result?.data?.description">
            {{ result.data.description }}
          </div>
        </div>

        <!-- Summary -->
        <div v-else-if="formData.taskType === 'summary'" class="panel">
          <div class="panel-title">视频摘要</div>
          <pre class="extract">{{ normalizeMarkdownText(result?.data || '') }}</pre>
        </div>

        <!-- MindMap -->
        <div v-else-if="formData.taskType === 'mindmap'" class="panel">
          <div class="panel-row">
            <div class="panel-title">思维导图</div>

            <div class="toolstrip">
              <!-- import -->
              <input
                ref="importFileInput"
                type="file"
                class="hidden"
                accept=".json"
                @change="handleImportFile"
              />
              <button class="btn" type="button" @click="triggerImport">
                导入
              </button>

              <!-- export -->
              <div class="dropdown">
                <button class="btn" type="button" @click="toggleExportDropdown('mindmap')">
                  导出
                </button>
                <div v-if="exportDropdown === 'mindmap'" class="menu">
                  <button type="button" @click="handleExportMindMap('json')">JSON</button>
                  <button type="button" @click="handleExportMindMap('png')">PNG</button>
                  <button type="button" @click="handleExportMindMap('jpeg')">JPEG</button>
                </div>
              </div>

              <div class="divider"></div>

              <button class="btn" type="button" @click="handleAddNode">增加节点</button>
              <button class="btn danger" type="button" @click="handleDeleteNode">删除节点</button>
            </div>
          </div>

          <div class="canvas">
            <MindMap
              ref="mindMapComponent"
              :dataObj="result.data"
              @import-success="handleImportSuccess"
              @export-data="handleExportData"
              @node-update="handleNodeUpdate"
              @node-move="handleNodeMove"
              @node-select="handleNodeSelect"
            />
          </div>
        </div>

        <!-- QA -->
        <div v-else-if="formData.taskType === 'qa'" class="panel">
          <div class="panel-title">问答结果</div>
          <div class="qa">
            <div class="qa-q">
              <div class="tag">问题</div>
              <div class="text">{{ formData.question }}</div>
            </div>
            <div class="qa-a">
              <div class="tag">回答</div>
              <div class="rich" v-html="result?.data?.answer || ''"></div>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div v-else-if="formData.taskType === 'notes'" class="panel">
          <div class="panel-title">笔记</div>
          <pre class="extract">{{ normalizeMarkdownText(result?.data || '') }}</pre>
        </div>
        <div v-else class="empty">
          暂无展示内容
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import axios from 'axios'
import MindMap from '@/components/MindMap.vue'

function normalizeMarkdownText(text) {
  if (!text) return ''

  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/^\s*---\s*$/gm, '')
    .replace(/^- /gm, '• ')
    .replace(/\n{3,}/g, '\n\n')
}

const formData = ref({
  videoId: '',
  taskType: 'play',
  question: ''
})

const result = ref(null)
const loading = ref(false)
const error = ref(null)

const exportDropdown = ref(null)
const selectedNodeId = ref(null)

const importFileInput = ref(null)
const mindMapComponent = ref(null)

const resultMetaText = computed(() => {
  const id = formData.value.videoId?.trim()
  if (!id) return ''
  return `输入：${id}`
})

function resetAll() {
  error.value = null
  result.value = null
  selectedNodeId.value = null
  exportDropdown.value = null
}

async function processVideo() {
  loading.value = true
  error.value = null
  result.value = null
  exportDropdown.value = null

  try {
    const payload = {
      video_id: formData.value.videoId,
      task_type: formData.value.taskType,
      question: formData.value.taskType === 'qa' ? formData.value.question : null
    }
    const response = await axios.post('/api/process-video', payload)
    result.value = response.data
  } catch (err) {
    error.value = err?.response?.data?.error || '处理失败，请稍后重试'
    console.error('视频分析错误:', err)
  } finally {
    loading.value = false
  }
}

// ---- MindMap actions ----
function toggleExportDropdown(type) {
  exportDropdown.value = exportDropdown.value === type ? null : type
}

function triggerImport() {
  importFileInput.value?.click?.()
}

function handleImportFile(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const importedData = JSON.parse(e.target.result)
      mindMapComponent.value?.importMindMap?.(importedData)
    } catch (err) {
      console.error('导入文件解析错误:', err)
      alert('导入失败：文件格式不正确')
    } finally {
      event.target.value = ''
    }
  }
  reader.readAsText(file)
}

function handleImportSuccess(importedData) {
  // 这里以“覆盖当前结果中的 mindmap data”为准
  if (result.value) result.value.data = importedData
  alert('导入成功')
}

function handleExportMindMap(format) {
  mindMapComponent.value?.exportMindMap?.(format)
  exportDropdown.value = null
}

function handleExportData(data, format) {
  if (format === 'json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mindmap_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } else {
    console.log('导出数据:', format, data)
  }
}

function handleAddNode() {
  mindMapComponent.value?.addNode?.(selectedNodeId.value)
}

function handleDeleteNode() {
  mindMapComponent.value?.deleteNode?.(selectedNodeId.value)
}

function handleNodeUpdate(updateData) {
  console.log('节点更新:', updateData)
  
  if (!result.value || !result.value.data || !result.value.data.root) return
  
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
  
  // 深拷贝根节点，避免直接修改原始数据
  const root = deepCopy(result.value.data.root)
  
  if (updateData.action === 'add') {
    // 添加节点
    const parent = findNode(root, updateData.parentId)
    if (parent) {
      if (!parent.children) parent.children = []
      parent.children.push(updateData.newNode)
      // 更新结果数据
      result.value.data.root = root
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
    result.value.data.root = root
  } else if (updateData.topic) {
    // 更新节点内容
    const node = findNode(root, updateData.nodeId)
    if (node) {
      node.topic = updateData.topic
      // 更新结果数据
      result.value.data.root = root
    }
  }
}

function handleNodeMove(moveData) {
  console.log('节点移动:', moveData)
}

function handleNodeSelect(nodeId) {
  selectedNodeId.value = nodeId
}
</script>

<style scoped>
/* page */
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 16px 60px;
  color: #111827;
}

/* header */
.header {
  padding: 6px 2px 14px;
}
.header-title h1 {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.2px;
  margin: 0;
}
.header-title p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

/* card */
.card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(17, 24, 39, 0.06);
  overflow: hidden;
  margin-top: 14px;
}
.card-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(to bottom, #fafafa, #fff);
  border-bottom: 1px solid #f1f5f9;
}
.card-hd-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 650;
  font-size: 14px;
  color: #111827;
}
.card-hd-sub {
  font-size: 12px;
  color: #6b7280;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
}
.card-bd {
  padding: 16px;
}

/* form */
.form {
  display: grid;
  gap: 14px;
}
.field label {
  display: block;
  font-size: 12px;
  color: #374151;
  margin-bottom: 6px;
  font-weight: 600;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  outline: none;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}
.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* buttons */
.btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #111827;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: transform 0.05s ease, background 0.15s ease, border-color 0.15s ease;
  user-select: none;
}
.btn:hover {
  background: #f9fafb;
}
.btn:active {
  transform: translateY(1px);
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.primary {
  background: #111827;
  border-color: #111827;
  color: #fff;
}
.btn.primary:hover {
  background: #0b1220;
}

.btn.ghost {
  background: transparent;
}

.btn.danger {
  border-color: #fee2e2;
  color: #b91c1c;
}
.btn.danger:hover {
  background: #fff1f2;
}

/* alert */
.alert {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #fee2e2;
  background: #fff1f2;
  color: #b91c1c;
  font-size: 13px;
}

/* panels */
.panel {
  display: grid;
  gap: 12px;
}
.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}
.panel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.video-frame {
  border: 1px solid #eef2f7;
  border-radius: 14px;
  overflow: hidden;
  background: #0b1220;
}
.video-player {
  width: 100%;
  height: 450px;
  display: block;
  background: #0b1220;
}

.kv {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.kv-item {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
}
.kv-item .k {
  font-size: 11px;
  color: #6b7280;
}
.kv-item .v {
  margin-top: 2px;
  font-size: 13px;
  font-weight: 650;
  color: #111827;
}

.desc {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.8;
  padding: 10px 12px;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  background: #fbfdff;
}

.rich {
  font-size: 13px;
  line-height: 1.85;
  color: #111827;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}
/* 文档式提取文本 */
.extract{
  margin: 0;
  padding: 14px 14px;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  background: #fff;
  color: #111827;
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;    /* 关键：保留换行，同时自动换行 */
  word-break: break-word;   /* 超长词/链接也能断行 */
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}


/* mindmap area */
.canvas {
  border: 1px solid #eef2f7;
  background: #f8fafc;
  border-radius: 14px;
  overflow: hidden;
  min-height: 620px;
}
.hidden {
  display: none;
}

/* toolstrip + dropdown */
.toolstrip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.divider {
  width: 1px;
  height: 18px;
  background: #e5e7eb;
  margin: 0 2px;
}

.dropdown {
  position: relative;
}
.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 140px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(17, 24, 39, 0.12);
  overflow: hidden;
  z-index: 50;
}
.menu button {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  font-size: 13px;
  border: 0;
  background: #fff;
  cursor: pointer;
}
.menu button:hover {
  background: #f9fafb;
}

/* QA */
.qa {
  display: grid;
  gap: 10px;
}
.qa-q,
.qa-a {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}
.tag {
  font-size: 11px;
  color: #6b7280;
  font-weight: 700;
  margin-bottom: 6px;
}
.text {
  font-size: 13px;
  color: #111827;
  line-height: 1.8;
}

/* empty */
.empty {
  padding: 14px;
  border: 1px dashed #e5e7eb;
  background: #fafafa;
  border-radius: 12px;
  color: #6b7280;
  font-size: 13px;
}

/* responsive */
@media (max-width: 768px) {
  .video-player {
    height: 240px;
  }
  .kv {
    grid-template-columns: 1fr;
  }
  .canvas {
    min-height: 520px;
  }
}
</style>
