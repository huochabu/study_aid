<template>
    <!-- 按钮组 -->
    <div
      v-if="showButton"
      class="btn-group"
      :style="{ top: buttonPos.top + 'px', left: buttonPos.left + 'px' }"
      @mousedown.stop 
    >
      <!-- 【修改点】把 @click 改成 @mousedown.prevent.stop -->
      <div class="action-btn" @mousedown.prevent.stop="handleAction('translate')">
        <span class="icon">🌐</span> 翻译
      </div>
      <div class="divider"></div>
      <div class="action-btn" @mousedown.prevent.stop="handleAction('polish')">
        <span class="icon">✨</span> 润色
      </div>
    </div>
  
    <!-- 结果卡片 -->
    <div
      v-if="showCard"
      class="translator-card"
      :style="{ top: cardPos.top + 'px', left: cardPos.left + 'px' }"
      @mousedown.stop
    >
      <div class="card-header" @mousedown="startDrag">
        <div class="header-left">
          <span class="icon">{{ currentMode === 'polish' ? '✨' : '📝' }}</span>
          <span class="title">{{ currentMode === 'polish' ? '学术润色' : '学术翻译' }}</span>
        </div>
        <span class="close" @mousedown.stop="closeCard">×</span>
      </div>
  
      <div class="card-body">
        <div class="original-text" v-if="selectedText">
          {{ selectedText.length > 50 ? selectedText.slice(0, 50) + '...' : selectedText }}
        </div>
        
        <div v-if="loading" class="loading">
          <div class="spinner"></div> 
          <span>AI 正在{{ currentMode === 'polish' ? '推敲措辞' : '阅读翻译' }}...</span>
        </div>
        
        <div v-else class="result-text" v-html="formatTranslation(translationResult)"></div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onUnmounted } from 'vue'
  import axios from 'axios'
  
  const showButton = ref(false)
  const showCard = ref(false)
  const loading = ref(false)
  const translationResult = ref('')
  const selectedText = ref('')
  const currentMode = ref('translate') 
  
  const buttonPos = ref({ top: 0, left: 0 })
  const cardPos = ref({ top: 0, left: 0 })
  
  const isDragging = ref(false)
  const dragOffset = ref({ x: 0, y: 0 })
  
  const startDrag = (e) => {
    if (e.button !== 0) return
    isDragging.value = true
    dragOffset.value = { x: e.clientX - cardPos.value.left, y: e.clientY - cardPos.value.top }
    document.addEventListener('mousemove', onDrag)
    document.addEventListener('mouseup', stopDrag)
  }
  const onDrag = (e) => {
    if (!isDragging.value) return
    cardPos.value = { left: e.clientX - dragOffset.value.x, top: e.clientY - dragOffset.value.y }
  }
  const stopDrag = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', onDrag)
    document.removeEventListener('mouseup', stopDrag)
  }
  
  const formatTranslation = (text) => text ? text.replace(/\n/g, '<br>') : ''
  
  const handleMouseUp = (e) => {
    if (showCard.value) return 
    const selection = window.getSelection()
    const text = selection.toString().trim()
  
    if (text && text.length > 2) { 
      selectedText.value = text
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      buttonPos.value = {
        top: rect.top + window.scrollY - 45, 
        left: rect.left + window.scrollX + (rect.width / 2) - 60
      }
      showButton.value = true
    } else {
      // 只有点击非按钮区域时才隐藏
      // 因为按钮用了 .stop，所以点击按钮不会触发这里的逻辑
      if (!showButton.value) return 
    }
  }
  
  const handleMouseDown = (e) => {
    if (!showCard.value && !e.target.closest('.btn-group')) {
      showButton.value = false
    }
  }
  
  // 核心逻辑
  const handleAction = async (type) => {
    console.log('🖱️ 按钮被点击了:', type) // [调试] 看控制台有没有这行字
    
    currentMode.value = type
    showButton.value = false
    
    cardPos.value = { top: buttonPos.value.top, left: buttonPos.value.left }
    showCard.value = true
    loading.value = true
    translationResult.value = ''
  
    try {
      console.log('🚀 准备发送请求...')
      // 强制指定后端地址
      const response = await axios.post('http://localhost:8000/api/translate', {
        text: selectedText.value,
        type: type
      })
  
      console.log('✅ 收到响应:', response.data)
  
      if (response.data.status === 'success') {
        translationResult.value = response.data.translation
      } else {
        translationResult.value = '<span style="color:red">请求失败：' + response.data.message + '</span>'
      }
    } catch (error) {
      console.error('❌ 请求出错:', error)
      translationResult.value = '<span style="color:red">网络错误：请按F12查看Console报错详情</span>'
    } finally {
      loading.value = false
    }
  }
  
  const closeCard = () => {
    showCard.value = false
    window.getSelection().removeAllRanges()
  }
  
  onMounted(() => {
    document.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('mousedown', handleMouseDown)
  })
  onUnmounted(() => {
    document.removeEventListener('mouseup', handleMouseUp)
    document.removeEventListener('mousedown', handleMouseDown)
    document.removeEventListener('mousemove', onDrag)
    document.removeEventListener('mouseup', stopDrag)
  })
  </script>
  
  <style scoped>
  /* 样式保持不变 */
  .btn-group {
    position: absolute;
    z-index: 9999;
    background: #ffffff;
    border-radius: 8px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    display: flex;
    align-items: center;
    padding: 4px;
    border: 1px solid #e5e7eb;
    animation: popIn 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }
  
  .action-btn {
    padding: 6px 12px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
    user-select: none; /* 防止按钮文字被选中 */
  }
  
  .action-btn:hover {
    background: #f3f4f6;
    color: #000;
  }
  
  .divider {
    width: 1px;
    height: 16px;
    background: #e5e7eb;
    margin: 0 2px;
  }
  
  .translator-card {
    position: absolute;
    z-index: 9999;
    width: 320px;
    min-height: 120px;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.1);
    border: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  
  .card-header {
    background: linear-gradient(to right, #e0f7fa, #e3f2fd);
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #bae6fd;
    cursor: move;
    user-select: none;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 14px;
    color: #0284c7;
  }
  .card-header .close {
    cursor: pointer;
    font-size: 18px;
    color: #7dd3fc;
    padding: 0 4px;
  }
  .card-header .close:hover {
    color: #0284c7;
  }
  
  .card-body {
    padding: 14px;
    font-size: 14px;
    line-height: 1.6;
    color: #1f2937;
    max-height: 400px;
    overflow-y: auto;
    background: #fff;
  }
  
  .original-text {
    font-size: 12px;
    color: #9ca3af;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px dashed #e5e7eb;
  }
  
  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    padding: 20px 0;
    gap: 10px;
    font-size: 13px;
  }
  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #e5e7eb;
    border-top: 2px solid #849fcc;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  @keyframes popIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }
  </style>