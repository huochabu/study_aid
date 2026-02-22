<!-- src/components/FileManager.vue -->
<template>
  <div class="file-manager">
    <!-- header -->
    <div class="manager-header">
      <div class="header-left">
        <div class="title">
          <Folder :size="16" />
          <span>文件管理</span>
        </div>

        <span class="chip">
          共 {{ files.length }} 个文件
        </span>

        <button
          class="btn-lite"
          @click="fetchFiles"
          :disabled="refreshing"
          title="刷新"
        >
          <RefreshCw v-if="!refreshing" :size="14" />
          <Loader2 v-else :size="14" class="spin" />
          <span class="btn-text">{{ refreshing ? '刷新中' : '刷新' }}</span>
        </button>
      </div>

      <button
        class="btn-danger-lite"
        @click="showDeleteAllConfirm"
        :disabled="files.length === 0 || deletingAll"
        title="删除所有文件"
      >
        <Loader2 v-if="deletingAll" :size="14" class="spin" />
        <Trash2 v-else :size="14" />
        <span class="btn-text">{{ deletingAll ? '删除中' : '删除所有' }}</span>
      </button>
    </div>

    <!-- list -->
    <div v-if="files.length > 0" class="file-list">
      <div 
        v-for="file in files" 
        :key="file.file_id" 
        class="file-item" 
        :class="{ 'selected': isSelectionMode && selectedFiles.includes(file.file_id) }"
        @click="isSelectionMode && toggleSelection(file.file_id)"
      >
        <div class="file-left">
          <div v-if="isSelectionMode" class="mr-3 flex items-center">
             <div 
               class="w-5 h-5 rounded border flex items-center justify-center transition-colors"
               :class="selectedFiles.includes(file.file_id) ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 bg-white'"
             >
                <Check v-if="selectedFiles.includes(file.file_id)" :size="14" stroke-width="3" />
             </div>
          </div>
          <div class="file-icon" :class="file.type">
            <component :is="getFileLucideIcon(file.type)" :size="16" />
          </div>

          <div class="file-details">
            <div class="file-name" :title="file.filename">
              {{ file.filename }}
            </div>
            <div class="file-meta">
              <span>{{ formatSize(file.size) }}</span>
              <span class="dot">•</span>
              <span>{{ formatDate(file.upload_time) }}</span>
            </div>
          </div>
        </div>

        <button
          class="btn-icon-danger"
          @click="showDeleteConfirm(file.file_id)"
          :disabled="deletingFiles.includes(file.file_id)"
          title="删除"
        >
          <Loader2 v-if="deletingFiles.includes(file.file_id)" :size="16" class="spin" />
          <Trash2 v-else :size="16" />
        </button>
      </div>
    </div>

    <!-- empty -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <Inbox :size="20" />
      </div>
      <div class="empty-text">
        <div class="empty-title">暂无上传的文件</div>
        <div class="empty-desc">上传后会显示在这里，便于管理与删除。</div>
      </div>
    </div>

    <!-- pagination -->
    <div v-if="pagination.total > 0" class="pagination">
      <button class="page-btn" @click="prevPage" :disabled="currentPage <= 1" title="上一页">
        <ChevronLeft :size="16" />
      </button>

      <div class="page-info">
        第 <b>{{ currentPage }}</b> / {{ pagination.total_pages }} 页
      </div>

      <button class="page-btn" @click="nextPage" :disabled="currentPage >= pagination.total_pages" title="下一页">
        <ChevronRight :size="16" />
      </button>

      <div class="page-size">
        <span class="page-size-label">每页</span>
        <select v-model.number="pageSize" @change="changePageSize" class="page-size-input">
          <option value="5">5</option>
          <option value="10">10</option>
          <option value="20">20</option>
          <option value="50">50</option>
        </select>
      </div>

      <div class="total-info">
        共 {{ pagination.total }} 个
      </div>
    </div>

    <!-- message -->
    <div v-if="message" :class="['message', message.type]">
      <Info v-if="message.type === 'info'" :size="14" />
      <CheckCircle2 v-else-if="message.type === 'success'" :size="14" />
      <AlertTriangle v-else :size="14" />
      <span>{{ message.text }}</span>
    </div>

    <!-- confirm dialog -->
    <div v-if="confirmVisible" class="confirm-overlay" @click.self="cancelAction">
      <div class="confirm-dialog">
        <div class="confirm-head">
          <div class="confirm-icon">
            <AlertTriangle :size="18" />
          </div>
          <div class="confirm-title">
            <h4>{{ confirmTitle }}</h4>
            <p>{{ confirmMessage }}</p>
          </div>
        </div>

        <div class="confirm-buttons">
          <button @click="cancelAction" class="btn-lite">
            取消
          </button>
          <button @click="confirmAction" class="btn-danger-lite">
            确认删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineProps } from 'vue'
import axios from 'axios'

// lucide icons
import {
  Folder,
  RefreshCw,
  Trash2,
  Loader2,
  FileText,
  Image as ImageIcon,
  Inbox,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Info,
  Check // [NEW]
} from 'lucide-vue-next'

// props
const props = defineProps({
  fileType: {
    type: String,
    default: null
  },
  isSelectionMode: {
    type: Boolean,
    default: false
  },
  selectedFiles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:selectedFiles', 'refresh'])

// state
const files = ref([])
const deletingFiles = ref([])
const deletingAll = ref(false)
const refreshing = ref(false)
const message = ref(null)

// pagination
const currentPage = ref(1)
const pageSize = ref(10)
const pagination = ref({
  total: 0,
  page: 1,
  page_size: 10,
  total_pages: 1
})

// confirm
const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmFileId = ref(null)
const confirmIsDeleteAll = ref(false)

// fetch
const fetchFiles = async () => {
  try {
    refreshing.value = true

    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (props.fileType) {
      params.file_type = props.fileType
    }

    const response = await axios.get('/files', {
      params,
      timeout: 30000
    })

    if (response.data.status === 'success') {
      files.value = response.data.files
      pagination.value = response.data.pagination || {
        total: 0,
        page: 1,
        page_size: pageSize.value,
        total_pages: 1
      }
      currentPage.value = pagination.value.page
    }
  } catch (error) {
    let errorMessage = '获取文件列表失败: ' + (error.message || '未知错误')
    if (error.message?.includes('timeout')) {
      errorMessage += '（请求超时，建议刷新页面重试）'
    } else if (error.response) {
      errorMessage += `（HTTP ${error.response.status}）`
    } else if (error.request) {
      errorMessage += '（未收到响应）'
    }
    showMessage(errorMessage, 'error')
  } finally {
    refreshing.value = false
  }
}

// confirm
const showDeleteConfirm = (fileId) => {
  confirmTitle.value = '确认删除'
  confirmMessage.value = '确定要删除这个文件吗？'
  confirmFileId.value = fileId
  confirmIsDeleteAll.value = false
  confirmVisible.value = true
}

const showDeleteAllConfirm = () => {
  confirmTitle.value = '确认删除所有文件'
  confirmMessage.value = '确定要删除所有文件吗？此操作不可恢复！'
  confirmIsDeleteAll.value = true
  confirmVisible.value = true
}

const executeConfirm = async () => {
  if (confirmIsDeleteAll.value) {
    try {
      deletingAll.value = true
      const response = await axios.delete('/files', { timeout: 30000 })

      if (response.data.status === 'success') {
        files.value = []
        showMessage(`所有文件已删除，共删除 ${response.data.deleted_count} 个文件`, 'success')
      } else {
        showMessage('删除所有文件失败: ' + (response.data.detail || '未知错误'), 'error')
      }
    } catch (error) {
      let errorMessage = '删除所有文件失败: ' + (error.message || '未知错误')
      if (error.message?.includes('timeout')) {
        errorMessage += '（请求超时，建议刷新页面重试）'
      } else if (error.response) {
        errorMessage += `（HTTP ${error.response.status}）`
        if (error.response.data?.detail) {
          errorMessage += ': ' + error.response.data.detail
        }
      } else if (error.request) {
        errorMessage += '（未收到响应）'
      }
      showMessage(errorMessage, 'error')
    } finally {
      deletingAll.value = false
      confirmVisible.value = false
    }
  } else {
    const fileId = confirmFileId.value
    if (!fileId) return

    try {
      deletingFiles.value.push(fileId)
      const response = await axios.delete(`/files/${fileId}`, { timeout: 30000 })

      if (response.status >= 200 && response.status < 300) {
        files.value = files.value.filter(file => file.file_id !== fileId)
        showMessage('文件删除成功', 'success')
      } else {
        showMessage('删除文件失败: HTTP ' + response.status, 'error')
      }
    } catch (error) {
      let errorMessage = '删除文件失败: ' + (error.message || '未知错误')
      if (error.message?.includes('timeout')) {
        errorMessage += '（请求超时，建议刷新页面重试）'
      } else if (error.response) {
        errorMessage += `（HTTP ${error.response.status}）`
        if (error.response.data?.detail) {
          errorMessage += ': ' + error.response.data.detail
        }
      } else if (error.request) {
        errorMessage += '（未收到响应）'
      }
      showMessage(errorMessage, 'error')
    } finally {
      deletingFiles.value = deletingFiles.value.filter(id => id !== fileId)
      confirmVisible.value = false
    }
  }
}

const confirmAction = () => executeConfirm()
const cancelAction = () => { confirmVisible.value = false }

// icons
const getFileLucideIcon = (type) => {
  const t = (type || '').toLowerCase()
  if (['jpg', 'jpeg', 'png'].includes(t)) return ImageIcon
  return FileText
}

// helpers
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatDate = (timestamp) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

// pagination
const nextPage = () => {
  if (currentPage.value < pagination.value.total_pages) {
    currentPage.value++
    fetchFiles()
  }
}
const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchFiles()
  }
}
const changePageSize = () => {
  currentPage.value = 1
  fetchFiles()
}

// message
const showMessage = (text, type = 'info') => {
  message.value = { text, type }
  setTimeout(() => { message.value = null }, 3000)
}

onMounted(() => fetchFiles())

defineExpose({ refreshFiles: fetchFiles })

const toggleSelection = (fileId) => {
  if (!props.isSelectionMode) return
  const newSelection = [...props.selectedFiles]
  const index = newSelection.indexOf(fileId)
  if (index > -1) {
    newSelection.splice(index, 1)
  } else {
    newSelection.push(fileId)
  }
  console.log("Selection changed:", newSelection)
  emit('update:selectedFiles', newSelection)
}
</script>

<style scoped>
.file-manager {
  padding: 12px;
}

/* header */
.manager-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(39, 39, 42, 1);
}

.chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(228, 228, 231, 1);
  background: rgba(250, 250, 250, 1);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(82, 82, 91, 1);
}

/* buttons */
.btn-text { margin-left: 8px; }

.btn-lite {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: #fff;
  color: rgba(63, 63, 70, 1);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background .12s ease;
}

.btn-lite:hover:not(:disabled) {
  background: rgba(244, 244, 245, 1);
}

.btn-lite:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.btn-danger-lite {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(254, 202, 202, 1);
  background: rgba(254, 242, 242, 1);
  color: rgba(185, 28, 28, 1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background .12s ease;
}

.btn-danger-lite:hover:not(:disabled) {
  background: rgba(254, 226, 226, 1);
}

.btn-danger-lite:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.btn-icon-danger {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(254, 202, 202, 1);
  background: rgba(254, 242, 242, 1);
  color: rgba(185, 28, 28, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background .12s ease;
}

.btn-icon-danger:hover:not(:disabled) {
  background: rgba(254, 226, 226, 1);
}

.btn-icon-danger:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* list */
.file-list {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 10px;
  border: 1px solid rgba(228, 228, 231, 1);
  border-radius: 14px;
  background: #fff;
  margin-bottom: 10px;
  transition: background .12s ease, box-shadow .12s ease;
}

.file-item:hover {
  background: rgba(250, 250, 250, 1);
  box-shadow: 0 1px 2px rgba(0,0,0,.06);
}

.file-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(228, 228, 231, 1);
  background: rgba(244, 244, 245, 1);
  color: rgba(63, 63, 70, 1);
  flex: 0 0 auto;
}

.file-details {
  min-width: 0;
  flex: 1;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: rgba(24, 24, 27, 1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(113, 113, 122, 1);
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot { opacity: .7; }

/* empty */
.empty-state {
  border: 1px dashed rgba(228, 228, 231, 1);
  border-radius: 16px;
  padding: 18px;
  background: rgba(250, 250, 250, 1);
  display: flex;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(244, 244, 245, 1);
  border: 1px solid rgba(228, 228, 231, 1);
  display: grid;
  place-items: center;
  color: rgba(82, 82, 91, 1);
}

.empty-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(39, 39, 42, 1);
}

.empty-desc {
  font-size: 12px;
  color: rgba(113, 113, 122, 1);
  margin-top: 2px;
}

/* pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(228, 228, 231, 1);
  flex-wrap: wrap;
}

.page-btn {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: #fff;
  color: rgba(63, 63, 70, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background .12s ease;
}

.page-btn:hover:not(:disabled) {
  background: rgba(244, 244, 245, 1);
}

.page-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.page-info {
  font-size: 12px;
  color: rgba(82, 82, 91, 1);
  padding: 0 6px;
}

.page-size {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(82, 82, 91, 1);
}

.page-size-input {
  height: 32px;
  border-radius: 10px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: #fff;
  padding: 0 10px;
  font-size: 12px;
  color: rgba(63, 63, 70, 1);
}

.total-info {
  font-size: 12px;
  color: rgba(82, 82, 91, 1);
}

/* message */
.message {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: #fff;
}

.message.success {
  border-color: rgba(187, 247, 208, 1);
  background: rgba(240, 253, 244, 1);
  color: rgba(21, 128, 61, 1);
}

.message.error {
  border-color: rgba(254, 202, 202, 1);
  background: rgba(254, 242, 242, 1);
  color: rgba(185, 28, 28, 1);
}

.message.info {
  border-color: rgba(191, 219, 254, 1);
  background: rgba(239, 246, 255, 1);
  color: rgba(29, 78, 216, 1);
}

/* confirm */
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 18px;
}

.confirm-dialog {
  width: 100%;
  max-width: 420px;
  border-radius: 18px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: #fff;
  box-shadow: 0 12px 30px rgba(0,0,0,.18);
  padding: 16px;
}

.confirm-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.confirm-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(254, 202, 202, 1);
  background: rgba(254, 242, 242, 1);
  color: rgba(185, 28, 28, 1);
  display: grid;
  place-items: center;
}

.confirm-title h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: rgba(24, 24, 27, 1);
}

.confirm-title p {
  margin: 6px 0 0;
  font-size: 12px;
  color: rgba(113, 113, 122, 1);
  line-height: 1.5;
}

.confirm-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}
</style>
