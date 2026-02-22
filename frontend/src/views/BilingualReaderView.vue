<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'

// ========== API 基址（推荐用 Vite 代理；没配就走 8000） ==========
const API_BASE = import.meta.env?.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  timeout: 120000, // 批量翻译可能较慢，适当放大
})

const files = ref([])
const selectedFileId = ref('')
const selectedFileName = ref('')

/**
 * 段落数据结构：
 * { index: number, text: string, status: 'idle'|'translating'|'done'|'error', errorMsg?: string, expanded?: boolean }
 */
const paragraphs = ref([])
const translations = ref({}) // { [index]: translation }

const loadingFiles = ref(false)
const loadingParas = ref(false)
const translatingAll = ref(false)

const mode = ref('translate') // translate | polish
const progress = ref({ done: 0, total: 0 })

// 全局错误提示（比如批量接口报错）
const globalError = ref('')

const hasData = computed(() => paragraphs.value.length > 0)

const statusText = (s) => {
  if (s === 'translating') return '翻译中'
  if (s === 'done') return '已翻译'
  if (s === 'error') return '失败'
  return '未翻译'
}

// 长段落折叠：超过多少字符就折叠
const COLLAPSE_AT = 700
const previewText = (t) => {
  if (!t) return ''
  if (t.length <= COLLAPSE_AT) return t
  return t.slice(0, COLLAPSE_AT) + '…'
}

const loadFiles = async () => {
  loadingFiles.value = true
  globalError.value = ''
  try {
    const res = await api.get('/files', { params: { page: 1, page_size: 50, file_type: 'pdf' } })
    if (res.data?.status === 'success') {
      files.value = res.data.files || []
    } else {
      files.value = []
      globalError.value = res.data?.message || '获取文件列表失败（接口返回非 success）'
    }
  } catch (e) {
    console.error('loadFiles error:', e)
    files.value = []
    globalError.value = e?.response?.data?.detail || e?.message || '获取文件列表失败（网络/服务端错误）'
  } finally {
    loadingFiles.value = false
  }
}

const loadParagraphs = async () => {
  if (!selectedFileId.value) return
  loadingParas.value = true
  globalError.value = ''
  translations.value = {}
  try {
    const res = await api.get(`/api/files/${selectedFileId.value}/paragraphs`)
    if (res.data?.status === 'success') {
      selectedFileName.value = res.data.filename || ''
      const paras = res.data.paragraphs || []
      paragraphs.value = paras.map(p => ({
        index: p.index,
        text: p.text,
        status: 'idle',
        errorMsg: '',
        expanded: false,
      }))
    } else {
      paragraphs.value = []
      selectedFileName.value = ''
      globalError.value = res.data?.message || '加载段落失败（接口返回非 success）'
    }
  } catch (e) {
    console.error('loadParagraphs error:', e)
    paragraphs.value = []
    selectedFileName.value = ''
    globalError.value = e?.response?.data?.detail || e?.message || '加载段落失败（网络/服务端错误）'
  } finally {
    loadingParas.value = false
  }
}

const translateOne = async (p) => {
  if (!p?.text) return
  if (p.status === 'translating') return

  globalError.value = ''
  p.status = 'translating'
  p.errorMsg = ''

  try {
    const res = await api.post('/api/translate', { text: p.text, type: mode.value })
    if (res.data?.status === 'success') {
      translations.value = { ...translations.value, [p.index]: res.data.translation }
      p.status = 'done'
    } else {
      p.status = 'error'
      p.errorMsg = res.data?.message || '翻译失败（接口返回非 success）'
    }
  } catch (e) {
    console.error('translateOne error:', e)
    p.status = 'error'
    // 兼容 FastAPI HTTPException(detail=...) 以及你后端 return {message:...}
    p.errorMsg =
      e?.response?.data?.message ||
      e?.response?.data?.detail ||
      e?.message ||
      '翻译失败（网络/服务端错误）'
  }
}

const translateAll = async () => {
  if (!paragraphs.value.length) return

  translatingAll.value = true
  globalError.value = ''

  // 只翻译未翻译的段落（避免重复耗费）
  const items = paragraphs.value
    .filter(p => !translations.value[p.index])
    .map(p => ({ index: p.index, text: p.text }))

  // 若都翻译过了
  if (items.length === 0) {
    translatingAll.value = false
    return
  }

  progress.value = { done: 0, total: items.length }

  // 标记状态
  for (const p of paragraphs.value) {
    if (!translations.value[p.index]) {
      p.status = 'translating'
      p.errorMsg = ''
    }
  }

  try {
    const res = await api.post('/api/translate/batch', { type: mode.value, items })

    if (res.data?.status === 'success') {
      const map = { ...translations.value }
      const arr = res.data.translations || []

      // 写入翻译结果
      for (let i = 0; i < arr.length; i++) {
        const it = arr[i]
        map[it.index] = it.translation
        progress.value = { done: i + 1, total: progress.value.total }
      }

      translations.value = map

      // 更新每段状态
      for (const p of paragraphs.value) {
        if (translations.value[p.index]) {
          p.status = 'done'
          p.errorMsg = ''
        } else if (p.status === 'translating') {
          p.status = 'idle'
        }
      }
    } else {
      globalError.value = res.data?.message || '批量翻译失败（接口返回非 success）'
      // 批量失败：把 translating 标记成 error
      for (const p of paragraphs.value) {
        if (p.status === 'translating') {
          p.status = 'error'
          p.errorMsg = globalError.value
        }
      }
    }
  } catch (e) {
    console.error('translateAll error:', e)
    globalError.value =
      e?.response?.data?.message ||
      e?.response?.data?.detail ||
      e?.message ||
      '批量翻译失败（网络/服务端错误）'
    for (const p of paragraphs.value) {
      if (p.status === 'translating') {
        p.status = 'error'
        p.errorMsg = globalError.value
      }
    }
  } finally {
    translatingAll.value = false
  }
}

const toggleExpand = (p) => {
  p.expanded = !p.expanded
}

watch(selectedFileId, () => {
  paragraphs.value = []
  translations.value = {}
  selectedFileName.value = ''
  progress.value = { done: 0, total: 0 }
  globalError.value = ''
})

onMounted(loadFiles)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="header-left">
        <h1 class="title">全文双语对照</h1>
        <p class="subtitle">每段一张卡片，左侧原文，右侧译文</p>
      </div>

      
    </header>

    <section class="card">
      <div class="card-head">
        <div class="card-head-left">
          <div class="card-title">选择文件</div>
          <div class="card-desc">从已上传 PDF 中选择并加载段落</div>
        </div>
      </div>

      <div class="toolbar">
        <select v-model="selectedFileId" class="select w-420">
          <option value="">-- 请选择 PDF --</option>
          <option v-for="f in files" :key="f.file_id" :value="f.file_id">
            {{ f.filename }}
          </option>
        </select>

        <button class="btn btn-primary" :disabled="!selectedFileId || loadingParas" @click="loadParagraphs">
          {{ loadingParas ? '加载中...' : '加载全文' }}
        </button>

        <button class="btn btn-secondary" :disabled="!hasData || translatingAll" @click="translateAll">
          {{ translatingAll ? `翻译中...(${progress.done}/${progress.total})` : '一键翻译全文' }}
        </button>

        <div class="meta" v-if="selectedFileName">
          当前：{{ selectedFileName }}（{{ paragraphs.length }} 段）
        </div>
      </div>


      <div v-if="globalError" class="global-error">
        {{ globalError }}
      </div>
    </section>

    <section v-if="!hasData && !loadingParas" class="empty">
      <div class="empty-title">暂无内容</div>
      <div class="empty-desc">请选择文件并点击“加载全文”。</div>
    </section>

    <section v-if="loadingParas" class="meta">正在加载全文段落…</section>

    <section v-if="hasData" class="list">
      <div v-for="p in paragraphs" :key="p.index" class="para-card">
        <div class="para-head">
          <div class="para-title">段落 {{ p.index + 1 }}</div>

          <div class="para-actions">
            <span class="badge" :class="p.status" :title="p.errorMsg || ''">
              {{ statusText(p.status) }}
            </span>

            <button class="btn btn-sm btn-ghost" @click="translateOne(p)" :disabled="p.status==='translating'">
              翻译本段
            </button>
          </div>
        </div>

        <div class="para-grid">
          <div class="col">
            <div class="col-title">原文</div>

            <!--  长段落折叠 -->
            <div class="para-text">
              {{ p.expanded ? p.text : previewText(p.text) }}
            </div>
            <button
              v-if="(p.text || '').length > COLLAPSE_AT"
              class="btn-link"
              @click="toggleExpand(p)"
            >
              {{ p.expanded ? '收起' : '展开全文' }}
            </button>
          </div>

          <div class="col">
            <div class="col-title">{{ mode === 'polish' ? '润色结果（英文）' : '中文翻译' }}</div>

            <div class="para-text muted" v-if="!translations[p.index] && p.status!=='translating'">
              （未翻译）
            </div>
            <div class="para-text" v-else>
              {{ translations[p.index] }}
            </div>

            <!--  显示失败原因 -->
            <div v-if="p.status==='error' && p.errorMsg" class="error-msg">
              失败原因：{{ p.errorMsg }}
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page{
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px 40px;
  color:#111827;
}

.page-header{
  display:flex;
  justify-content: space-between;
  align-items:flex-start;
  gap:14px;
  padding: 16px 16px;
  border-radius: 16px;
  border: 1px solid #f0f0f0;
  background: #fafafa;
  margin-bottom: 14px;
}

.title{ margin:0; font-size:20px; font-weight:900; }
.subtitle{ margin:6px 0 0; font-size:13px; color:#6b7280; line-height:1.5; }

.header-right{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }

.card{
  background:#fff;
  border:1px solid #eef2f7;
  border-radius: 16px;
  box-shadow: 0 8px 22px rgba(0,0,0,0.06);
  overflow:hidden;
  margin-bottom: 12px;
}

.card-head{
  padding: 14px 14px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(to bottom, #ffffff, #fbfbfb);
}
.card-title{ font-size:14px; font-weight:900; }
.card-desc{ margin-top:4px; font-size:12px; color:#6b7280; }

.toolbar{
  display:flex;
  gap:10px;
  align-items:center;
  flex-wrap:wrap;
  padding: 12px 14px;
}

.meta{ font-size:12px; color:#6b7280; }

.select{
  height: 38px;
  border-radius: 12px;
  border: 1px solid #eef2f7;
  background: #fff;
  padding: 0 12px;
  font-size: 13px;
  outline:none;
}
.w-420{ min-width: 320px; max-width: 520px; }

.btn{
  height: 38px;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 800;
  border: 1px solid transparent;
  cursor:pointer;
}
.btn:disabled{ opacity: .55; cursor:not-allowed; }

.btn-primary{ background:#111827; color:#fff; }
.btn-primary:hover{ background:#0f172a; }

.btn-secondary{ background:#2563eb; color:#fff; }
.btn-secondary:hover{ background:#1d4ed8; }

.btn-ghost{ background:transparent; border-color:#eef2f7; color:#111827; }
.btn-ghost:hover{ background:#f8fafc; }

.btn-sm{ height: 32px; padding: 0 10px; font-size: 12px; border-radius: 10px; }

.global-error{
  padding: 10px 14px 14px;
  font-size: 12px;
  color: #b91c1c;
  background: #fef2f2;
  border-top: 1px solid #fee2e2;
}

.empty{
  padding: 28px 14px;
  text-align:center;
  border: 1px dashed #e5e7eb;
  border-radius: 16px;
  background: #fff;
}
.empty-title{ font-weight:900; }
.empty-desc{ margin-top:6px; font-size:12px; color:#6b7280; }

.list{
  display:flex;
  flex-direction:column;
  gap: 10px;
}

.para-card{
  background:#fff;
  border:1px solid #eef2f7;
  border-radius: 16px;
  overflow:hidden;
  box-shadow: 0 8px 22px rgba(0,0,0,0.04);
}

.para-head{
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:center;
  padding: 12px 12px;
  border-bottom: 1px solid #f1f5f9;
  background: #fbfbfb;
}
.para-title{ font-size:13px; font-weight:900; }
.para-actions{ display:flex; gap:10px; align-items:center; }

.badge{
  font-size:12px;
  font-weight:800;
  padding: 6px 10px;
  border-radius: 999px;
  border:1px solid #eef2f7;
  background:#f8fafc;
  color:#475569;
}
.badge.translating{ background:#eff6ff; border-color:#dbeafe; color:#1d4ed8; }
.badge.done{ background:#ecfdf5; border-color:#d1fae5; color:#065f46; }
.badge.error{ background:#fef2f2; border-color:#fee2e2; color:#b91c1c; }

.para-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px 12px 14px;
}
@media (max-width: 960px){
  .para-grid{ grid-template-columns: 1fr; }
}

.col-title{
  font-size:12px;
  font-weight:900;
  color:#374151;
  margin-bottom: 8px;
}

/*  更清楚：字号/行距上调 */
.para-text{
  font-size: 15px;
  line-height: 1.85;
  color:#111827;
  white-space: pre-wrap;
  word-break: break-word;
}

.muted{ color:#6b7280; }

.btn-link{
  margin-top: 8px;
  padding: 0;
  border: none;
  background: transparent;
  color: #2563eb;
  font-weight: 800;
  font-size: 12px;
  cursor: pointer;
}
.btn-link:hover{ text-decoration: underline; }

.error-msg{
  margin-top: 10px;
  font-size: 12px;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 12px;
  padding: 10px 10px;
}
</style>