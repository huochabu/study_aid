<!-- src/components/FileUploader.vue -->
<template>
  <div class="uploader">
    <h2>📄 文件上传</h2>
    <input
      ref="fileInput"
      type="file"
      @change="onFileChange"
      accept=".pdf,.txt,.log,.jpg,.jpeg,.png"
      style="margin-bottom: 10px;"
    />
    <p v-if="selectedFileName">已选择: {{ selectedFileName }}</p>
    <button
      :disabled="!selectedFile || uploading"
      @click="handleUpload"
      class="upload-btn"
    >
      {{ uploading ? '上传中...' : '🚀 开始分析' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="success">{{ success }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['upload-complete'])

const fileInput = ref(null)
const selectedFile = ref(null)
const selectedFileName = ref('')
const uploading = ref(false)
const error = ref('')
const success = ref('')

function onFileChange(event) {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    selectedFileName.value = file.name
    error.value = ''
    success.value = ''
  } else {
    reset()
  }
}

async function handleUpload() {
  if (!selectedFile.value) return

  uploading.value = true
  error.value = ''
  success.value = ''

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await axios.post('http://localhost:8000/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 60秒超时（大文件/OCR可能慢）
    })

    success.value = '✅ 分析成功！正在加载结果...'
    emit('upload-complete', response.data)

    // 清空 input，允许重新选择同名文件
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch (err) {
    console.error('上传失败:', err)
    error.value = `❌ ${err.response?.data?.error || '上传失败，请重试'}`
  } finally {
    uploading.value = false
  }
}

function reset() {
  selectedFile.value = null
  selectedFileName.value = ''
  if (fileInput.value) fileInput.value.value = ''
}
</script>

<style scoped>
.uploader {
  border: 1px solid #ddd;
  padding: 16px;
  border-radius: 8px;
  max-width: 400px;
  background: #fafafa;
}

.upload-btn {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.upload-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.error {
  color: #f56565;
  margin-top: 8px;
}

.success {
  color: #48bb78;
  margin-top: 8px;
}
</style>