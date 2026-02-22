<template>
  <div class="feedback-widget">
    <div v-if="!submitted">
      <div class="actions">
        <span class="prompt">此回答是否有帮助？</span>
        <button 
          class="btn-icon" 
          :class="{ active: rating === 1 }" 
          @click="setRating(1)"
        >
          👍
        </button>
        <button 
          class="btn-icon" 
          :class="{ active: rating === -1 }" 
          @click="setRating(-1)"
        >
          👎
        </button>
      </div>
      
      <div v-if="rating !== 0" class="comment-area">
        <input 
          v-model="comment" 
          placeholder="如有改进建议，请告诉我们..." 
          class="comment-input"
          @keyup.enter="submit"
        />
        <button class="btn-submit" @click="submit">提交</button>
      </div>
    </div>
    
    <div v-else class="success-msg">
      <div v-if="teacherModeActive" class="teacher-badge">
        ✨ 已学习新知识 (Teacher Mode)
      </div>
      <div v-else>
        感谢您的反馈！我们会持续改进。
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Add new style for teacher badge */
.teacher-badge {
    color: #0ea5e9;
    font-weight: bold;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { opacity: 0.8; }
    50% { opacity: 1; }
    100% { opacity: 0.8; }
}
</style>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const props = defineProps({
  fileId: String,
  qaId: String, // [NEW] Need QA ID for backend update
  question: String,
  answer: String
})

const rating = ref(0)
const comment = ref('')
const submitted = ref(false)
const teacherModeActive = ref(false) // [NEW]
const isSubmitting = ref(false)

const setRating = (val) => {
  rating.value = val
}

const submit = async () => {
  if (isSubmitting.value) return
  isSubmitting.value = true
  
  try {
    const res = await axios.post('http://localhost:8000/feedback', {
      file_id: props.fileId,
      qa_id: props.qaId, // Send QA ID
      question: props.question, // Send question for embedded learning
      rating: rating.value,
      comment: comment.value
    })
    
    submitted.value = true
    if (res.data.message && res.data.message.includes('Teacher Mode')) {
        teacherModeActive.value = true
    }
  } catch (e) {
    console.error('Feedback failed', e)
    alert('提交反馈失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.feedback-widget {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.prompt {
  font-size: 12px;
  color: #94a3b8;
}
.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.6;
  transition: all 0.2s;
}
.btn-icon:hover { opacity: 1; transform: scale(1.1); }
.btn-icon.active { opacity: 1; transform: scale(1.2); }

.comment-area {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.comment-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
}
.btn-submit {
  padding: 6px 12px;
  background: #0f172a;
  color: white;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.success-msg {
  font-size: 12px;
  color: #10b981;
  font-weight: 500;
}
</style>
