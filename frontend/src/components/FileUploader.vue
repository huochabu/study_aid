<!-- src/components/FileUploader.vue -->
<template>
  <div class="uploader">
    <!-- 顶部标题行 -->
    <div class="uploader-head">
      <div class="head-left">
        <div class="head-icon">
          <Upload :size="18" />
        </div>

        <div class="head-text">
          <div class="title-row">
            <h3 class="title">{{ uploadMode === 'simple' ? '简单上传' : '上传文档' }}</h3>
            <span class="mode-pill">{{ uploadMode === 'simple' ? 'Upload' : 'Analyze' }}</span>
          </div>
          <p class="subtitle">
            支持 {{ acceptLabel }}，最大 {{ formatFileSize(maxSize) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Dropzone -->
    <div
      class="dropzone"
      :class="{ 'is-dragover': isDragOver, 'has-file': !!selectedFile }"
      @click="openPicker"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden-input"
        :accept="acceptTypes"
        @change="onFileChange"
      />

      <div class="dropzone-left">
        <div class="dropzone-icon">
          <FileUp v-if="!selectedFile" :size="18" />
          <FileText v-else :size="18" />
        </div>

        <div class="dropzone-text">
          <div class="dz-title">
            {{ selectedFile ? '已选择文件' : '选择文件' }}
          </div>
          <div class="dz-sub">
            <template v-if="selectedFile">
              <span class="file-name">{{ selectedFileName }}</span>
              <span class="dot">·</span>
              <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
            </template>
            <template v-else>
              点击选择文件（也支持拖拽到此区域）
            </template>
          </div>
        </div>
      </div>

      <button
        type="button"
        class="btn-browse"
        @click.stop="openPicker"
      >
        浏览
      </button>
    </div>

    <!-- 主按钮 -->
    <button
      class="btn-primary"
      :disabled="!selectedFile || uploading"
      @click="handleUpload"
    >
      <Loader2 v-if="uploading" :size="16" class="spin" />
      <span v-else class="rocket">
        <Rocket :size="16" />
      </span>
      <span>
        {{ uploading ? '上传中...' : (uploadMode === 'simple' ? '上传文件' : '开始分析') }}
      </span>
    </button>

    <!-- 提示 -->
    <div v-if="error" class="msg error">
      <AlertTriangle :size="14" />
      <span>{{ error }}</span>
    </div>
    <div v-if="success" class="msg success">
      <CheckCircle2 :size="14" />
      <span>{{ success }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

// lucide icons
import {
  Upload,
  FileUp,
  FileText,
  Rocket,
  Loader2,
  AlertTriangle,
  CheckCircle2
} from 'lucide-vue-next'

const props = defineProps({
  uploadMode: {
    type: String,
    default: 'full',
    validator: (value) => ['full', 'simple'].includes(value)
  },
  acceptTypes: {
    type: String,
    default: '.pdf,.txt,.log,.jpg,.jpeg,.png'
  },
  maxSize: {
    type: Number,
    default: 100 * 1024 * 1024
  }
})

const emit = defineEmits(['upload-complete', 'upload-error'])

const fileInput = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const uploading = ref(false)
const error = ref('')
const success = ref('')

// drag state
const isDragOver = ref(false)

const uploadTimeout = computed(() => {
  return props.uploadMode === 'full' ? 120000 : 30000
})

const acceptLabel = computed(() => {
  // 仅用于展示，更好看一点
  return props.acceptTypes
    .replaceAll('.', '.')
    .split(',')
    .map(s => s.trim())
    .join(' / ')
})

function openPicker() {
  fileInput.value?.click()
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function validateFile(file) {
  // size
  if (file.size > props.maxSize) {
    error.value = `文件过大，最大允许 ${formatFileSize(props.maxSize)}`
    return false
  }

  // ext
  const allowedTypes = props.acceptTypes.split(',').map(type => type.trim())
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase()

  if (!allowedTypes.includes(fileExtension)) {
    error.value = `文件类型不支持，仅允许: ${props.acceptTypes}`
    return false
  }

  return true
}

function setFile(file) {
  if (!file) return
  error.value = ''
  success.value = ''
  if (!validateFile(file)) {
    selectedFile.value = null
    selectedFileName.value = ''
    return
  }
  selectedFile.value = file
  selectedFileName.value = file.name
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) {
    reset()
    return
  }
  setFile(file)
}

// drag handlers
function onDragEnter() {
  isDragOver.value = true
}
function onDragOver() {
  isDragOver.value = true
}
function onDragLeave() {
  isDragOver.value = false
}
function onDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  setFile(file)

  // 允许再次 drop 同名文件时也能触发：把 input 清空
  if (fileInput.value) fileInput.value.value = ''
}

async function handleUpload() {
  if (!selectedFile.value) return

  uploading.value = true
  error.value = ''
  success.value = ''

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const uploadUrl = props.uploadMode === 'full' ? '/upload' : '/upload-simple'
    const response = await axios.post(uploadUrl, formData, {
      timeout: uploadTimeout.value
    })

    success.value = props.uploadMode === 'full'
      ? '分析成功！正在加载结果...'
      : '上传成功！'

    emit('upload-complete', response.data)
    reset()
  } catch (err) {
    console.error('上传失败:', err)

    let errorMessage = props.uploadMode === 'full'
      ? '分析失败，请重试'
      : '上传失败，请重试'

    if (err.response?.data) {
      const data = err.response.data
      if (data.error) errorMessage = data.error
      else if (typeof data === 'object') errorMessage = JSON.stringify(data)
    } else if (err.message) {
      errorMessage = err.message
    }

    error.value = `${errorMessage}`
    emit('upload-error', errorMessage)
  } finally {
    uploading.value = false
  }
}

function reset() {
  selectedFile.value = null
  selectedFileName.value = ''
  error.value = ''
  success.value = ''
  if (fileInput.value) fileInput.value.value = ''
}
</script>

<style scoped>
/* 注意：不用 rounded-2xl 这类 @apply，避免之前的 tailwind unknown utility 报错 */

.uploader {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* header */
.uploader-head {
  padding: 6px 2px 2px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.head-icon {
  height: 44px;
  width: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: rgba(244, 244, 245, 1);
  border: 1px solid rgba(228, 228, 231, 1);
  color: rgba(63, 63, 70, 1);
}
.head-text .title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  line-height: 1.1;
}
.mode-pill {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(228, 228, 231, 1);
  background: rgba(250, 250, 250, 1);
  color: rgba(63, 63, 70, 1);
}
.subtitle {
  margin: 6px 0 0;
  color: rgba(113, 113, 122, 1);
  font-size: 13px;
}

/* dropzone */
.dropzone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;

  padding: 18px 18px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid rgba(228, 228, 231, 1);
  box-shadow: 0 1px 2px rgba(0,0,0,.06);

  cursor: pointer;
  user-select: none;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease, background .15s ease;
}

.dropzone:hover {
  box-shadow: 0 6px 16px rgba(0,0,0,.06);
  transform: translateY(-1px);
}

.dropzone.is-dragover {
  border-color: rgba(24, 24, 27, .35);
  background: rgba(250, 250, 250, 1);
}

.dropzone-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.dropzone-icon {
  height: 44px;
  width: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: rgba(244, 244, 245, 1);
  border: 1px solid rgba(228, 228, 231, 1);
  color: rgba(63, 63, 70, 1);
  flex: 0 0 auto;
}

.dropzone-text {
  min-width: 0;
}

.dz-title {
  font-size: 15px;
  font-weight: 700;
  color: rgba(24, 24, 27, 1);
  line-height: 1.2;
}

.dz-sub {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(113, 113, 122, 1);
  line-height: 1.2;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.file-name {
  font-weight: 600;
  color: rgba(63, 63, 70, 1);
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dot {
  opacity: .6;
}

.btn-browse {
  height: auto;
  padding: 6px 8px;
  border: none;
  background: transparent;
  color: rgba(63, 63, 70, 1);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.btn-browse:hover {
  text-decoration: underline;
}

.hidden-input {
  display: none;
}

/* main button */
.btn-primary {
  height: 54px;
  border-radius: 18px;
  border: none;
  background: rgba(24, 24, 27, 1);
  color: #fff;
  font-weight: 700;
  font-size: 15px;

  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;

  cursor: pointer;
  transition: transform .12s ease, background .12s ease, opacity .12s ease;
}
.btn-primary:hover {
  background: rgba(39, 39, 42, 1);
}
.btn-primary:active {
  transform: scale(0.995);
}
.btn-primary:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.rocket {
  display: inline-flex;
  align-items: center;
}

/* messages */
.msg {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid;
  font-size: 13px;
}
.msg.error {
  background: rgba(254, 242, 242, 1);
  border-color: rgba(254, 202, 202, 1);
  color: rgba(185, 28, 28, 1);
}
.msg.success {
  background: rgba(240, 253, 244, 1);
  border-color: rgba(187, 247, 208, 1);
  color: rgba(21, 128, 61, 1);
}
</style>
