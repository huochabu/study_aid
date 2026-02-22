<!-- src/components/HistoryManager.vue -->
<template>
  <div class="history-manager">
    <!-- header -->
    <div class="manager-header">
      <div class="header-left">
        <div class="title">
          <BookOpen :size="16" />
          <span>历史分析记录</span>
        </div>

        <span class="chip">共 {{ pagination.total }} 条</span>

        <button
          class="btn-lite"
          @click="fetchHistory"
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
        @click="deleteAllHistory"
        :disabled="history.length === 0 || deletingAll"
        title="删除所有记录"
      >
        <Loader2 v-if="deletingAll" :size="14" class="spin" />
        <Trash2 v-else :size="14" />
        <span class="btn-text">{{ deletingAll ? '删除中' : '删除所有' }}</span>
      </button>
    </div>

    <!-- list -->
    <div v-if="history.length > 0" class="history-list">
      <div v-for="item in history" :key="item.id" class="history-item">
        <div class="history-left">
          <div class="history-icon">
            <BarChart3 :size="16" />
          </div>

          <div class="history-details">
            <div class="history-filename" :title="item.filename">
              {{ item.filename }}
            </div>
            <div class="history-meta">
              <Clock :size="12" />
              <span>{{ formatDate(item.analysis_time) }}</span>
            </div>
          </div>
        </div>

        <div class="history-actions">
          <button class="btn-primary-lite" @click="loadHistory(item)" title="加载分析结果">
            <ArrowDownToLine :size="14" />
            <span class="btn-text">Load</span>
          </button>

          <button
            class="btn-icon-danger"
            @click="deleteHistory(item)"
            :disabled="deletingHistory.includes(item.id)"
            title="删除"
          >
            <Loader2 v-if="deletingHistory.includes(item.id)" :size="16" class="spin" />
            <Trash2 v-else :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- empty -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <Inbox :size="20" />
      </div>
      <div class="empty-text">
        <div class="empty-title">暂无历史分析记录</div>
        <div class="empty-desc">分析过的文件会出现在这里，便于一键加载结果。</div>
      </div>
    </div>

    <!-- pagination -->
    <div v-if="pagination.total > 0" class="pagination">
      <button @click="prevPage" :disabled="currentPage <= 1" class="page-btn" title="上一页">
        <ChevronLeft :size="16" />
      </button>

      <div class="page-info">
        第 <b>{{ currentPage }}</b> / {{ pagination.total_pages }} 页
      </div>

      <button @click="nextPage" :disabled="currentPage >= pagination.total_pages" class="page-btn" title="下一页">
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

      <div class="total-info">共 {{ pagination.total }} 条</div>
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
          <button @click="cancelAction" class="btn-lite">取消</button>
          <button @click="confirmAction" class="btn-danger-lite">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// lucide icons
import {
  BookOpen,
  RefreshCw,
  Trash2,
  Loader2,
  BarChart3,
  Clock,
  Inbox,
  ChevronLeft,
  ChevronRight,
  ArrowDownToLine,
  AlertTriangle,
  CheckCircle2,
  Info
} from 'lucide-vue-next'

// 历史记录相关状态
const history = ref([])
const refreshing = ref(false)
const deletingAll = ref(false)
const deletingHistory = ref([])
const message = ref(null)

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(10)
const pagination = ref({
  total: 0,
  page: 1,
  page_size: 10,
  total_pages: 1
})

// 确认对话框状态
const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmHistoryItem = ref(null)
const confirmIsDeleteAll = ref(false)

// 事件
const emit = defineEmits(['load-history', 'history-deleted'])

// 格式化日期（逻辑不动）
const formatDate = (timestamp) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 获取历史记录（逻辑不动）
const fetchHistory = async () => {
  try {
    refreshing.value = true
    message.value = null

    const response = await axios.get('/history', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value
      },
      timeout: 30000
    })

    if (response.data.status === 'success') {
      console.log('获取的历史记录:', response.data.data)
      history.value = response.data.data
      pagination.value = {
        total: response.data.total,
        page: response.data.page,
        page_size: response.data.page_size,
        total_pages: Math.ceil(response.data.total / response.data.page_size)
      }
    } else {
      throw new Error('获取历史记录失败')
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
    message.value = {
      text: error.response?.data?.detail || '获取历史记录失败',
      type: 'error'
    }
  } finally {
    refreshing.value = false
  }
}

// 上一页
const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchHistory()
  }
}

// 下一页
const nextPage = () => {
  if (currentPage.value < pagination.value.total_pages) {
    currentPage.value++
    fetchHistory()
  }
}

// 改变每页显示数量
const changePageSize = () => {
  currentPage.value = 1
  fetchHistory()
}

// 加载历史记录
const loadHistory = (item) => {
  emit('load-history', item)
}

// 删除单个历史记录 - 显示确认对话框
const deleteHistory = (item) => {
  confirmHistoryItem.value = item
  confirmIsDeleteAll.value = false
  confirmTitle.value = '确认删除'
  confirmMessage.value = `确定要删除文件 "${item.filename}" 及其分析记录吗？`
  confirmVisible.value = true
}

// 删除所有历史记录
const deleteAllHistory = () => {
  confirmIsDeleteAll.value = true
  confirmTitle.value = '确认删除所有记录'
  confirmMessage.value = '确定要删除所有文件及其分析记录吗？此操作无法撤销。'
  confirmVisible.value = true
}

// 执行确认操作
const executeConfirm = async () => {
  if (confirmIsDeleteAll.value) {
    try {
      deletingAll.value = true
      message.value = null

      const response = await axios.delete('/history', {
        timeout: 30000
      })

      if (response.data.status === 'success') {
        message.value = {
          text: `成功删除所有 ${response.data.deleted_count} 个文件及其分析记录`,
          type: 'success'
        }
        emit('history-deleted', { all: true })
        fetchHistory()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      console.error('删除所有历史记录失败:', error)
      message.value = {
        text: error.response?.data?.detail || '删除所有历史记录失败',
        type: 'error'
      }
    } finally {
      deletingAll.value = false
      confirmVisible.value = false
    }
  } else {
    const item = confirmHistoryItem.value
    if (!item) return

    try {
      deletingHistory.value.push(item.id)
      message.value = null

      if (!item.file_id) {
        throw new Error('文件ID不存在，无法删除')
      }

      console.log('删除请求参数:', item)
      console.log('完整请求URL:', `/history/${item.id}`)

      const response = await axios.delete(`/history/${item.id}`, {
        timeout: 30000
      })

      if (response.data.status === 'success') {
        message.value = {
          text: `成功删除文件 "${item.filename}" 及其分析记录`,
          type: 'success'
        }
        emit('history-deleted', { file_id: item.file_id })
        fetchHistory()
      } else {
        throw new Error(response.data.detail || '删除失败')
      }
    } catch (error) {
      console.error('删除历史记录失败:', error)
      let errorText = '删除历史记录失败'
      if (error.message) {
        errorText += `: ${error.message}`
      } else if (error.response?.data?.detail) {
        errorText += `: ${error.response.data.detail}`
      } else if (error.response?.statusText) {
        errorText += `: ${error.response.statusText}`
      }
      message.value = {
        text: errorText,
        type: 'error'
      }
    } finally {
      deletingHistory.value = deletingHistory.value.filter(id => id !== item.id)
      confirmVisible.value = false
    }
  }
}

// 确认/取消
const confirmAction = () => executeConfirm()
const cancelAction = () => { confirmVisible.value = false }

// 组件挂载时获取历史记录
onMounted(() => {
  fetchHistory()
})

// 提供外部刷新方法
defineExpose({
  refreshHistory: fetchHistory
})
</script>

<style scoped>
.history-manager {
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

.btn-primary-lite {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(212, 212, 216, 1);
  background: rgba(24, 24, 27, 1);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: transform .06s ease, background .12s ease;
}

.btn-primary-lite:hover {
  background: rgba(39, 39, 42, 1);
}

.btn-primary-lite:active {
  transform: scale(0.99);
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
.history-list {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(228, 228, 231, 1);
  border-radius: 14px;
  background: #fff;
  margin-bottom: 10px;
  transition: background .12s ease, box-shadow .12s ease;
}

.history-item:hover {
  background: rgba(250, 250, 250, 1);
  box-shadow: 0 1px 2px rgba(0,0,0,.06);
}

.history-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.history-icon {
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

.history-details {
  min-width: 0;
  flex: 1;
}

.history-filename {
  font-size: 13px;
  font-weight: 600;
  color: rgba(24, 24, 27, 1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(113, 113, 122, 1);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.history-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

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
