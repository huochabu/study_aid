<template>
  <div class="eval-score-card">
    <div class="score-row">
      <span class="label">Faithfulness (忠实度)</span>
      <div class="bar-container">
        <div 
          class="bar-fill" 
          :style="{ width: faithfulness * 100 + '%', background: getColor(faithfulness) }"
        ></div>
      </div>
      <span class="value">{{ faithfulness.toFixed(2) }}</span>
    </div>
    
    <div class="score-row">
      <span class="label">Relevancy (相关性)</span>
      <div class="bar-container">
        <div 
          class="bar-fill" 
          :style="{ width: relevancy * 100 + '%', background: getColor(relevancy) }"
        ></div>
      </div>
      <span class="value">{{ relevancy.toFixed(2) }}</span>
    </div>
    
    <div class="reason" v-if="reason">
      <span class="reason-label">评估理由:</span> {{ reason }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  faithfulness: { type: Number, default: 0 },
  relevancy: { type: Number, default: 0 },
  reason: { type: String, default: '' }
})

const getColor = (score) => {
  if (score >= 0.8) return '#10b981' // Green
  if (score >= 0.5) return '#f59e0b' // Amber
  return '#ef4444' // Red
}
</script>

<style scoped>
.eval-score-card {
  margin-top: 10px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
}
.score-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.label {
  width: 120px;
  font-weight: 600;
  color: #64748b;
}
.bar-container {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  transition: width 0.5s ease;
}
.value {
  width: 30px;
  text-align: right;
  font-weight: 700;
}
.reason {
  margin-top: 8px;
  color: #64748b;
  font-style: italic;
  line-height: 1.4;
}
.reason-label {
  font-weight: 600;
  font-style: normal;
}
</style>
