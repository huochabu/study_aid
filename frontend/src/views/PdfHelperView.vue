<template>
  <div class="page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <h1 class="title">PDF 助手</h1>
        <p class="subtitle">支持图片提取、文本提取、压缩、旋转、拆分与合并等常用处理。</p>
      </div>

      <div class="header-right">
        <div class="pill" v-if="selectedFileId">
          <span class="dot"></span>
          当前选择：{{ selectedFileName ||selectedFileId }}
        </div>
      </div>
    </header>

    <!-- Delete Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="cancelDelete">
      <div class="modal">
        <div class="modal-title">确认删除文件</div>
        <div class="modal-desc">确定要删除此文件吗？此操作不可恢复。</div>
        <div class="modal-actions">
          <button class="btn btn-danger" @click="confirmDelete">确认删除</button>
          <button class="btn btn-ghost" @click="cancelDelete">取消</button>
        </div>
      </div>
    </div>

    <!-- Main -->
    <section class="grid">
      <!-- Left: File Manager -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">文件管理</div>
            <div class="card-desc">上传并选择 PDF 文件进行处理</div>
          </div>

          <div class="card-head-right">
            <input
              type="file"
              id="pdf-upload"
              accept=".pdf"
              class="hidden-input"
              @change="handleFileUpload"
            />
            <label for="pdf-upload" class="btn btn-primary" :class="{ disabled: uploading }">
              {{ uploading ? '上传中...' : '上传 PDF' }}
            </label>
          </div>
        </div>

        <div class="toolbar">
          <div class="toolbar-left">
            <span class="meta">共 {{ totalFiles }} 个</span>
            <span class="meta">第 {{ currentPage }} / {{ totalPages || 1 }} 页</span>
          </div>
          <div class="toolbar-right">
            <button class="btn-link btn-link-primary" @click="loadFileList" :disabled="loading" type="button">
              {{ loading ? '刷新中...' : '刷新' }}
            </button>

            <button
              class="btn-link btn-link-danger"
              @click="deleteAllFiles"
              :disabled="loading || fileList.length === 0"
              type="button"
            >
              删除所有
            </button>
          </div>
        </div>

        <div class="list">
          <div v-if="fileList.length" class="list-inner">
            <button
              v-for="file in fileList"
              :key="file.file_id"
              class="list-item"
              :class="{ active: selectedFileId === file.file_id }"
              @click="selectFile(file.file_id)"
              type="button"
            >
              <div class="file-main">
                <div class="file-name" :title="file.filename">{{ file.filename }}</div>
                <div class="file-sub">
                  <span>{{ formatFileSize(file.size) }}</span>
                  <span class="sep">·</span>
                  <span>{{ formatDate(file.upload_time) }}</span>
                </div>
              </div>

              <div class="file-side">
                <input
                  class="file-id"
                  :value="file.file_id"
                  readonly
                  @click.stop="$event.target.select()"
                />
                <button
                  class="btn-link btn-link-danger"
                  @click.stop="showDeleteConfirm(file.file_id)"
                  :disabled="deletingFiles.includes(file.file_id)"
                  type="button"
                >
                  {{ deletingFiles.includes(file.file_id) ? '删除中...' : '删除' }}
                </button>
              </div>
            </button>
          </div>

          <div v-else class="empty">
            <div class="empty-title">暂无文件</div>
            <div class="empty-desc">上传一个 PDF 后即可开始操作。</div>
          </div>
        </div>

        <div class="pager">
          <button class="btn btn-ghost" @click="prevPage" :disabled="currentPage === 1">上一页</button>
          <button class="btn btn-ghost" @click="nextPage" :disabled="currentPage === totalPages || totalPages === 0">下一页</button>

          <div class="page-size">
            <span class="meta">每页</span>
            <select v-model="pageSize" @change="handlePageSizeChange" class="select">
              <option :value="5">5</option>
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Right: Operations -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">操作面板</div>
            <div class="card-desc">选择文件后可执行操作</div>
          </div>
          <div class="card-head-right">
            <span class="badge" :class="selectedFileId ? 'ok' : 'muted'">
              {{ selectedFileId ? '已选择文件' : '未选择文件' }}
            </span>
          </div>
        </div>

        <div class="section">
          <div class="section-title">提取</div>
          <div class="btn-row">
            <button class="btn btn-secondary" @click="extractImages" :disabled="!selectedFileId">提取图片</button>
            <button class="btn btn-secondary" @click="extractText" :disabled="!selectedFileId">提取文本</button>
            <button class="btn btn-secondary" @click="getMetadata" :disabled="!selectedFileId">获取元数据</button>
          </div>
        </div>

        <div class="section">
          <div class="section-title">处理</div>
          <div class="btn-row">
            <button class="btn btn-secondary" @click="compressPDF" :disabled="!selectedFileId">压缩 PDF</button>

            <div class="inline">
              <input
                type="number"
                v-model.number="rotationAngle"
                class="input"
                placeholder="角度（如 90/-90）"
              />
              <button class="btn btn-secondary" @click="rotatePDF" :disabled="!selectedFileId || rotationAngle === 0">
                旋转
              </button>
            </div>
          </div>
        </div>

        <div class="section">
          <div class="section-title">页面管理</div>

          <div class="block">
            <label class="label">按位置拆分（从第 N 页开始拆开）</label>
            <div class="inline">
              <input type="number" v-model.number="splitPage" min="1" class="input" placeholder="输入页码（>=1）" />
              <button class="btn btn-secondary" @click="splitPDF" :disabled="!selectedFileId || splitPage === 0">拆分</button>
            </div>
          </div>

          <div class="block">
            <label class="label">合并（输入多个 file_id，用英文逗号分隔）</label>
            <div class="inline">
              <input type="text" v-model="mergeFileIds" class="input" placeholder="例如：id1,id2,id3" />
              <button class="btn btn-secondary" @click="mergePDFs" :disabled="!mergeFileIds">合并</button>
            </div>
          </div>
        </div>

        <div class="hint">
          提示：点击文件 ID 可一键选中复制。
        </div>
      </div>
    </section>

    <!-- Result -->
    <section class="card result-card">
      <div class="card-head">
        <div class="card-head-left">
          <div class="card-title">操作结果</div>
          <div class="card-desc">结果会显示在下方对应区域</div>
        </div>
      </div>

      <div v-if="message" class="toast" :class="messageType">
        {{ message }}
      </div>

      <!-- Images -->
      <div v-if="extractedImages.length > 0" class="result-block">
        <div class="result-head">
          <div class="result-title">提取的图片（{{ extractedImages.length }}）</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveImagesResult">下载全部</button>
          </div>
        </div>

        <div class="images-grid">
          <div v-for="(image, index) in extractedImages" :key="index" class="img-card">
            <div class="img-wrap">
              <img :src="getImageUrl(image.path)" alt="Extracted" />
            </div>
            <div class="img-meta">
              <div class="img-info">页 {{ image.page }} · {{ formatFileSize(image.size) }}</div>
              <button class="btn btn-ghost btn-sm" @click="saveSingleImage(image, index)">下载</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Text -->
      <div v-if="extractedText" class="result-block">
        <div class="result-head">
          <div class="result-title">提取的文本</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveTextResult">下载文本</button>
          </div>
        </div>

        <div class="code">
          <pre>{{ extractedText }}</pre>
        </div>
      </div>

      <!-- Metadata -->
      <div v-if="metadata" class="result-block">
        <div class="result-head">
          <div class="result-title">PDF 元数据</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveMetadataResult">下载元数据</button>
          </div>
        </div>

        <div class="kv">
          <div v-for="(value, key) in metadata" :key="key" class="kv-row">
            <div class="kv-k">{{ key }}</div>
            <div class="kv-v">{{ value }}</div>
          </div>
        </div>
      </div>

      <!-- Split -->
      <div v-if="splitResult" class="result-block">
        <div class="result-head">
          <div class="result-title">拆分结果</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveSplitResult">下载全部</button>
          </div>
        </div>

        <div class="note">
          拆分位置：第 {{ splitResult.splitPage }} 页
        </div>

        <ul class="file-links">
          <li v-for="(file, index) in splitResult.files" :key="index">
            <a :href="getDownloadUrl(file)" :download="getFileName(file)">{{ getFileName(file) }}</a>
          </li>
        </ul>
      </div>

      <!-- Merge -->
      <div v-if="mergeResult" class="result-block">
        <div class="result-head">
          <div class="result-title">合并结果</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveMergeResult">下载</button>
          </div>
        </div>

        <div class="note">
          合并文件数：{{ mergeResult.fileIds.length }} 个
        </div>

        <ul class="file-links">
          <li>
            <a :href="getDownloadUrl(mergeResult.path)" :download="getFileName(mergeResult.path)">{{ getFileName(mergeResult.path) }}</a>
          </li>
        </ul>
      </div>

      <!-- Compress -->
      <div v-if="compressResult" class="result-block">
        <div class="result-head">
          <div class="result-title">压缩结果</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveCompressResult" :disabled="!compressResult.path">下载</button>
          </div>
        </div>

        <div class="note">
          <div v-if="compressResult.originalSize">原始大小：{{ formatFileSize(compressResult.originalSize) }}</div>
          <div v-if="compressResult.compressedSize">压缩后大小：{{ formatFileSize(compressResult.compressedSize) }}</div>
          <div v-if="compressResult.compressionRatio">压缩率：{{ (100 - compressResult.compressionRatio).toFixed(1) }}%</div>
          <div v-if="compressResult.status">{{ compressResult.status }}</div>
        </div>

        <ul class="file-links" v-if="compressResult.path">
          <li>
            <a :href="getDownloadUrl(compressResult.path)" :download="getFileName(compressResult.path)">{{ getFileName(compressResult.path) }}</a>
          </li>
        </ul>
      </div>

      <!-- Rotate -->
      <div v-if="rotateResult" class="result-block">
        <div class="result-head">
          <div class="result-title">旋转结果</div>
          <div class="result-actions">
            <button class="btn btn-primary" @click="saveRotateResult" :disabled="!rotateResult.path">下载</button>
          </div>
        </div>

        <div class="note">
          旋转角度：{{ rotateResult.angle }} 度
        </div>

        <ul class="file-links" v-if="rotateResult.path">
          <li>
            <a :href="getDownloadUrl(rotateResult.path)" :download="getFileName(rotateResult.path)">{{ getFileName(rotateResult.path) }}</a>
          </li>
        </ul>
      </div>

      <div v-if="!message && !extractedText && !metadata && !extractedImages.length && !splitResult && !mergeResult && !compressResult && !rotateResult" class="result-empty">
        <div class="empty-title">暂无结果</div>
        <div class="empty-desc">选择文件并执行任意操作后，这里会显示输出。</div>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'PdfHelperView',
  data() {
    return {
      fileList: [],
      selectedFileId: '',
      rotationAngle: 0,
      splitPage: 0,
      mergeFileIds: '',
      extractedImages: [],
      extractedText: '',
      metadata: null,
      splitResult: null,
      mergeResult: null,
      compressResult: null,
      rotateResult: null,
      message: '',
      messageType: '',
      uploading: false,
      loading: false,
      currentPage: 1,
      pageSize: 10,
      totalFiles: 0,
      totalPages: 0,
      deletingFiles: [],
      showDeleteModal: false,
      fileIdToDelete: '',
      selectedFileName: ''
    }
  },
  mounted() {
    this.loadFileList()
  },
  methods: {
    async loadFileList() {
      try {
        this.loading = true
        const response = await this.$axios.get('/files', {
          params: {
            page: this.currentPage,
            page_size: this.pageSize,
            file_type: 'pdf'
          },
          timeout: 10000
        })
        this.fileList = response.data.files
        this.totalFiles = response.data.pagination.total
        this.totalPages = response.data.pagination.total_pages
      } catch (error) {
        this.showMessage('加载文件列表失败', 'error')
        console.error('Failed to load file list:', error)
      } finally {
        this.loading = false
      }
    },

    showDeleteConfirm(fileId) {
      this.fileIdToDelete = fileId
      this.showDeleteModal = true
    },

    async confirmDelete() {
      try {
        await this.$axios.delete(`/files/${this.fileIdToDelete}`)
        this.showMessage('文件删除成功', 'success')
        this.loadFileList()
        if (this.selectedFileId === this.fileIdToDelete) {
          this.selectedFileId = ''
          this.selectedFileName = ''
        }
      } catch (error) {
        this.showMessage('文件删除失败', 'error')
        console.error('Failed to delete file:', error)
      } finally {
        this.showDeleteModal = false
        this.fileIdToDelete = ''
      }
    },

    cancelDelete() {
      this.showDeleteModal = false
      this.fileIdToDelete = ''
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--
        this.loadFileList()
      }
    },

    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++
        this.loadFileList()
      }
    },

    handlePageSizeChange() {
      this.currentPage = 1
      this.loadFileList()
    },

    async deleteAllFiles() {
      if (this.fileList.length === 0) {
        this.showMessage('没有文件可以删除', 'info')
        return
      }

      if (confirm('确定要删除所有文件吗？此操作不可恢复。')) {
        try {
          await this.$axios.delete('/files')
          this.showMessage('所有文件删除成功', 'success')
          this.loadFileList()
          this.selectedFileId = ''
        } catch (error) {
          this.showMessage('删除所有文件失败', 'error')
          console.error('Failed to delete all files:', error)
        }
      }
    },

    selectFile(fileId) {
      this.selectedFileId = fileId

      const f = this.fileList.find(x => x.file_id === fileId)
      this.selectedFileName = f ? f.filename : ''

      this.resetResults()
    },


    resetResults() {
      this.extractedImages = []
      this.extractedText = ''
      this.metadata = null
      this.splitResult = null
      this.mergeResult = null
      this.compressResult = null
      this.rotateResult = null
      this.message = ''
      this.messageType = ''
    },

    showMessage(msg, type = 'info') {
      this.message = msg
      this.messageType = type
      setTimeout(() => {
        this.message = ''
        this.messageType = ''
      }, 3000)
    },

    formatFileSize(bytes) {
      if (!bytes || bytes < 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    formatDate(timestamp) {
      const date = new Date(timestamp * 1000)
      return date.toLocaleString()
    },

    async extractImages() {
      try {
        this.resetResults()
        const response = await this.$axios.post('/api/pdf/extract-images', { file_id: this.selectedFileId })
        if (response.data.success) {
          this.extractedImages = response.data.data
          console.log('extractedImages:', this.extractedImages)
          console.log('first img url:', this.getImageUrl(this.extractedImages?.[0]?.path))

          this.showMessage('图片提取成功', 'success')
        }
      } catch (error) {
        this.showMessage('图片提取失败', 'error')
        console.error('Failed to extract images:', error)
      }
    },

    async extractText() {
      try {
        this.resetResults()
        const response = await this.$axios.post('/api/pdf/extract-text', { file_id: this.selectedFileId })

        if (response.data.success) {
          const d = response.data.data
          this.extractedText =
            typeof d === 'string'
              ? d
              : (d?.text || d?.extracted_text || d?.content || '')

          if (this.extractedText) this.showMessage('文本提取成功', 'success')
          else this.showMessage('提取成功，但返回为空文本', 'warning')
        }
      } catch (error) {
        this.showMessage('文本提取失败', 'error')
        console.error('Failed to extract text:', error)
      }
    },

    async getMetadata() {
      try {
        this.resetResults()
        const response = await this.$axios.get(`/api/pdf/metadata/${this.selectedFileId}`)
        if (response.data.success) {
          this.metadata = response.data.data
          this.showMessage('元数据获取成功', 'success')
        }
      } catch (error) {
        this.showMessage('元数据获取失败', 'error')
        console.error('Failed to get metadata:', error)
      }
    },

    async compressPDF() {
      try {
        this.resetResults()
        const response = await this.$axios.post('/api/pdf/compress', { file_id: this.selectedFileId })
        if (response.data.success) {
          const compressedPath = response.data.data?.output_path || null
          this.compressResult = {
            path: compressedPath,
            originalSize: response.data.data?.original_size,
            compressedSize: response.data.data?.compressed_size,
            compressionRatio: response.data.data?.compression_ratio,
            status: response.data.data?.status
          }
          this.showMessage('PDF压缩成功', 'success')
          this.loadFileList()
        }
      } catch (error) {
        this.showMessage('PDF压缩失败', 'error')
        console.error('Failed to compress PDF:', error)
      }
    },

    async rotatePDF() {
      try {
        this.resetResults()
        const response = await this.$axios.post('/api/pdf/rotate', {
          file_id: this.selectedFileId,
          angle: this.rotationAngle
        })
        if (response.data.success) {
          const rotatedPath = response.data.data?.output_path || null
          this.rotateResult = {
            path: rotatedPath,
            angle: this.rotationAngle,
            rotatedPages: response.data.data?.rotated_pages
          }
          this.showMessage('PDF旋转成功', 'success')
          this.loadFileList()
        }
      } catch (error) {
        this.showMessage('PDF旋转失败', 'error')
        console.error('Failed to rotate PDF:', error)
      }
    },

    async splitPDF() {
      try {
        if (!this.splitPage || this.splitPage < 1) {
          this.showMessage('请输入有效的拆分页面位置', 'warning')
          return
        }
        this.resetResults()
        const response = await this.$axios.post('/api/pdf/split', {
          file_id: this.selectedFileId,
          split_page: this.splitPage
        })
        if (response.data.success) {
          const splitFiles = response.data.data.split_files || []
          this.splitResult = {
            files: splitFiles,
            splitPage: this.splitPage
          }
          this.showMessage('PDF拆分成功', 'success')
          this.loadFileList()
        }
      } catch (error) {
        this.showMessage('PDF拆分失败', 'error')
        console.error('Failed to split PDF:', error)
      }
    },

    async mergePDFs() {
      try {
        this.resetResults()
        const fileIds = this.mergeFileIds.split(',').map(id => id.trim()).filter(Boolean)
        const response = await this.$axios.post('/api/pdf/merge', {
          file_ids: fileIds
        })
        if (response.data.success) {
          const mergedPath = response.data.data.merged_path
          this.mergeResult = {
            path: mergedPath,
            fileIds: fileIds
          }
          this.showMessage('PDF合并成功', 'success')
          this.loadFileList()
        }
      } catch (error) {
        this.showMessage('PDF合并失败', 'error')
        console.error('Failed to merge PDFs:', error)
      }
    },

    saveTextResult() {
      const blob = new Blob([this.extractedText], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `extracted-text-${Date.now()}.txt`
      a.click()
      URL.revokeObjectURL(url)
    },

    saveMetadataResult() {
      const jsonStr = JSON.stringify(this.metadata, null, 2)
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pdf-metadata-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    },

    getImageUrl(p) {
      if (!p) return ''

      // 统一成 / 分隔
      const normalized = String(p).replace(/\\/g, '/')

      // 取出 downloads 之后的相对部分（含 uuid/filename）
      // 支持：.../downloads/<uuid>/<file>  或  downloads/<uuid>/<file>  或  <uuid>/<file>
      let rel = normalized

      const idx = normalized.lastIndexOf('/downloads/')
      if (idx >= 0) {
        rel = normalized.slice(idx + '/downloads/'.length) // <uuid>/<file>
      } else if (normalized.startsWith('downloads/')) {
        rel = normalized.slice('downloads/'.length)        // <uuid>/<file>
      } else {
        // 可能已经是 <uuid>/<file>
        rel = normalized.replace(/^\/+/, '')
      }

      // 用后端 8000 提供静态资源（关键）
      return `http://localhost:8000/downloads/${encodeURI(rel)}`
    },



    getDownloadUrl(filePath) {
      if (!filePath) return ''
      const filename = filePath.split(/[\/]/).pop()
      return `/downloads/${filename}`
    },

    getFileName(filePath) {
      if (!filePath) return ''
      return filePath.split(/[\/]/).pop()
    },

    saveSplitResult() {
      if (!this.splitResult || !this.splitResult.files.length) return
      this.splitResult.files.forEach((file, index) => {
        const filename = this.getFileName(file)
        const a = document.createElement('a')
        a.href = this.getDownloadUrl(file)
        a.download = filename
        setTimeout(() => a.click(), index * 120)
      })
      this.showMessage('开始下载拆分文件', 'success')
    },

    saveMergeResult() {
      if (!this.mergeResult || !this.mergeResult.path) return
      const filename = this.getFileName(this.mergeResult.path)
      const a = document.createElement('a')
      a.href = this.getDownloadUrl(this.mergeResult.path)
      a.download = filename
      a.click()
      this.showMessage('开始下载合并文件', 'success')
    },

    saveCompressResult() {
      if (!this.compressResult || !this.compressResult.path) return
      const filename = this.getFileName(this.compressResult.path)
      const a = document.createElement('a')
      a.href = this.getDownloadUrl(this.compressResult.path)
      a.download = filename
      a.click()
      this.showMessage('开始下载压缩文件', 'success')
    },

    saveRotateResult() {
      if (!this.rotateResult || !this.rotateResult.path) return
      const filename = this.getFileName(this.rotateResult.path)
      const a = document.createElement('a')
      a.href = this.getDownloadUrl(this.rotateResult.path)
      a.download = filename
      a.click()
      this.showMessage('开始下载旋转文件', 'success')
    },

    async saveImagesResult() {
      try {
        this.showMessage('正在准备下载图片...', 'info')
        for (let i = 0; i < this.extractedImages.length; i++) {
          const image = this.extractedImages[i]
          const filename = `image-${i + 1}-page-${image.page}-${Date.now()}.${image.path.split('.').pop()}`

          const response = await this.$axios.get(this.getImageUrl(image.path), {
            responseType: 'blob'
          })

          const url = URL.createObjectURL(response.data)
          const a = document.createElement('a')
          a.href = url
          a.download = filename
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)

          if (i < this.extractedImages.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 120))
          }
        }

        this.showMessage('图片下载完成', 'success')
      } catch (error) {
        this.showMessage('图片下载失败', 'error')
        console.error('Failed to download images:', error)
      }
    },

    async saveSingleImage(image, index) {
      try {
        this.showMessage('正在准备下载图片...', 'info')
        const filename = `image-${index + 1}-page-${image.page}-${Date.now()}.${image.path.split('.').pop()}`
        const response = await this.$axios.get(this.getImageUrl(image.path), { responseType: 'blob' })
        const url = URL.createObjectURL(response.data)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        this.showMessage('图片下载完成', 'success')
      } catch (error) {
        console.error('下载图片失败:', error)
        this.showMessage('下载图片失败', 'error')
      }
    },

    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      try {
        this.uploading = true
        this.showMessage('开始上传 PDF 文件...', 'info')

        const formData = new FormData()
        formData.append('file', file)

        const response = await this.$axios.post('/upload-simple', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        if (response.data) {
          this.showMessage('PDF 文件上传成功', 'success')
          await this.loadFileList()
          this.selectedFileId = response.data.file_id
          this.selectedFileName = file.name
        }
      } catch (error) {
        this.showMessage('PDF 文件上传失败', 'error')
        console.error('Failed to upload PDF file:', error)
      } finally {
        this.uploading = false
        event.target.value = ''
      }
    }
  }
}
</script>

<style scoped>
/* ========== Page ========== */
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px 40px;
  color: #111827;
}

/* ========== Header ========== */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 18px;
  border-radius: 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  margin-bottom: 18px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #ecfdf5;
  border: 1px solid #d1fae5;
  color: #065f46;
  font-size: 12px;
  font-weight: 600;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

/* ========== Grid ========== */
.grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

@media (max-width: 960px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

/* ========== Card ========== */
.card {
  background: #fff;
  border: 1px solid #f1f5f9;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 14px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(to bottom, #ffffff, #fbfbfb);
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.card-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.card-head-left {
  min-width: 0;
}

.card-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ========== Toolbar ========== */
.toolbar {
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta {
  font-size: 12px;
  color: #6b7280;
}

/* ========== List ========== */
.list {
  padding: 0 14px 12px;
}

.list-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-item {
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 14px;
  padding: 12px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.list-item:hover {
  border-color: #e5e7eb;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
  transform: translateY(-1px);
}

.list-item.active {
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.10);
  background: #fbfdff;
}

.file-main {
  min-width: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-sub {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sep {
  opacity: 0.6;
}

.file-side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;          /* 关键：允许换行 */
  max-width: 360px;         /* 防止右侧无限占宽（可按需调） */
}

/*响应式布局适配 针对移动端*/
@media (max-width: 720px) {
  .list-item {
    align-items: flex-start;
  }
  .file-side {
    max-width: 100%;
    justify-content: flex-start;
  }
  .file-id {
    width: 100%;
    max-width: 100%;
  }
}

.file-id {
  width: 210px;
  max-width: 38vw;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #eef2f7;
  background: #f8fafc;
  color: #334155;
  outline: none;
  cursor: text;
}

.file-id:focus {
  background: #fff;
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.10);
}

.empty {
  padding: 26px 8px 18px;
  text-align: center;
}

.empty-title {
  font-weight: 700;
  font-size: 14px;
  color: #111827;
}

.empty-desc {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

/* ========== Pager ========== */
.pager {
  padding: 10px 14px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.page-size {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.select {
  height: 34px;
  border-radius: 10px;
  border: 1px solid #eef2f7;
  background: #fff;
  padding: 0 10px;
  font-size: 12px;
  color: #111827;
  outline: none;
}

.select:focus {
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.10);
}

/* ========== Operations ========== */
.section {
  padding: 12px 14px;
  border-top: 1px solid #f1f5f9;
}

.section:first-of-type {
  border-top: none;
}

.section-title {
  font-size: 12px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 10px;
}

.btn-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.inline {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: center;
  flex-wrap: wrap;
}

.block {
  margin-top: 10px;
}

.label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}

.input {
  flex: 1;
  min-width: 200px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid #eef2f7;
  background: #fff;
  padding: 0 12px;
  font-size: 13px;
  color: #111827;
  outline: none;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.input:focus {
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.10);
}

.hint {
  padding: 12px 14px 14px;
  font-size: 12px;
  color: #6b7280;
  border-top: 1px solid #f1f5f9;
}

/* ========== Badge ========== */
.badge {
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #eef2f7;
  color: #475569;
  background: #f8fafc;
}
.badge.ok {
  background: #ecfeff;
  border-color: #cffafe;
  color: #155e75;
}
.badge.muted {
  opacity: 0.8;
}

/* ========== Buttons ========== */
.btn {
  height: 38px;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease, border-color 0.12s ease;
  user-select: none;
}

.btn:active {
  transform: translateY(1px);
}

.btn-primary {
  background: #111827;
  color: #fff;
  box-shadow: 0 10px 20px rgba(17, 24, 39, 0.12);
}
.btn-primary:hover {
  background: #0f172a;
}

.btn-secondary {
  background: #f8fafc;
  border-color: #eef2f7;
  color: #111827;
}
.btn-secondary:hover {
  background: #f1f5f9;
}

.btn-ghost {
  background: transparent;
  border-color: #eef2f7;
  color: #111827;
}
.btn-ghost:hover {
  background: #f8fafc;
}

.btn-danger {
  background: #ef4444;
  color: #fff;
  box-shadow: 0 10px 20px rgba(239, 68, 68, 0.14);
}
.btn-danger:hover {
  background: #dc2626;
}

.btn-sm {
  height: 32px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 10px;
}

.danger-hover:hover {
  border-color: rgba(239, 68, 68, 0.35);
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.06);
}

.btn:disabled,
.btn.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

/* hidden input */
.hidden-input {
  display: none;
}

/* ========== Result ========== */
.result-card {
  padding-bottom: 10px;
}

.toast {
  margin: 12px 14px 0;
  padding: 10px 12px;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid transparent;
}

.toast.info {
  background: #eff6ff;
  border-color: #dbeafe;
  color: #1d4ed8;
}
.toast.success {
  background: #ecfdf5;
  border-color: #d1fae5;
  color: #065f46;
}
.toast.error {
  background: #fef2f2;
  border-color: #fee2e2;
  color: #b91c1c;
}
.toast.warning {
  background: #fffbeb;
  border-color: #fef3c7;
  color: #92400e;
}

.result-block {
  margin: 12px 14px;
  border: 1px solid #eef2f7;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 12px;
  border-bottom: 1px solid #f1f5f9;
  background: #fbfbfb;
}

.result-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
}

.result-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.note {
  padding: 12px 12px;
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

.code {
  padding: 12px 12px;
  background: #ffffff;                /* 白底 */
  color: #0f172a;                     /* 黑字 */
  font-size: 12px;
  overflow: auto;
  border-top: 1px solid #f1f5f9;     
}

.code pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  color: inherit;   
}

/* metadata */
.kv {
  padding: 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kv-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 12px;
  padding: 10px 10px;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  background: #fafafa;
}

.kv-k {
  font-size: 12px;
  font-weight: 800;
  color: #111827;
}

.kv-v {
  font-size: 12px;
  color: #334155;
  word-break: break-all;
}

@media (max-width: 720px) {
  .kv-row {
    grid-template-columns: 1fr;
  }
}

/* links */
.file-links {
  padding: 0 12px 12px;
  margin: 0;
  list-style: none;
}

.file-links li {
  padding: 8px 0;
  border-top: 1px solid #f1f5f9;
}

.file-links li:first-child {
  border-top: none;
}

.file-links a {
  color: #2563eb;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
}

.file-links a:hover {
  text-decoration: underline;
}

/* images */
.images-grid {
  padding: 12px 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 10px;
}

.img-card {
  border: 1px solid #eef2f7;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}

.img-wrap {
  width: 100%;
  height: 120px;
  display: grid;
  place-items: center;
  background: #f8fafc;
}

.img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.img-meta {
  padding: 10px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.img-info {
  font-size: 12px;
  color: #475569;
  font-weight: 700;
}

/* empty result */
.result-empty {
  padding: 26px 14px 18px;
  text-align: center;
}

/* ========== Modal ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  display: grid;
  place-items: center;
  z-index: 9999;
  padding: 16px;
}

.modal {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #eef2f7;
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.25);
  padding: 16px;
}

.modal-title {
  font-size: 14px;
  font-weight: 900;
  color: #111827;
}

.modal-desc {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

.modal-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

/* ========== Link Buttons ========== */
.btn-link {
  background: transparent;
  border: none;
  padding: 0;
  height: auto;
  line-height: 1;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  color: #111827;
}

.btn-link:hover {
  text-decoration: underline;
}

.btn-link:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  text-decoration: none;
}

.btn-link-danger {
  color: #dc2626;
}

.btn-link-danger:hover {
  color: #b91c1c;
}

.btn-link-primary {
  color: #2563eb; /* blue */
}

.btn-link-primary:hover {
  color: #1d4ed8;
}
</style>
