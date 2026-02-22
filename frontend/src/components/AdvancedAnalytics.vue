<template>
  <div class="advanced-analytics">
    <h2 class="text-2xl font-bold mb-6">高级数据分析</h2>
    
    <!-- 学习行为分析 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习行为分析</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="font-medium mb-2">学习时间分布</h4>
          <div class="h-64">
            <canvas ref="timeDistributionChart"></canvas>
          </div>
        </div>
        <div>
          <h4 class="font-medium mb-2">学习行为类型</h4>
          <div class="h-64">
            <canvas ref="behaviorTypeChart"></canvas>
          </div>
        </div>
      </div>
      <div class="mt-6">
        <h4 class="font-medium mb-2">学习行为详情</h4>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">行为类型</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">持续时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模块</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="behavior in recentBehaviors" :key="behavior.id">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ getBehaviorTypeName(behavior.behavior_type) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDuration(behavior.duration) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDate(behavior.timestamp) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ behavior.module_id || 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- 学习预测分析 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习预测分析</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="font-medium mb-2">完成时间预测</h4>
          <div class="h-64">
            <canvas ref="completionTimeChart"></canvas>
          </div>
        </div>
        <div>
          <h4 class="font-medium mb-2">成功概率分析</h4>
          <div class="h-64">
            <canvas ref="successProbabilityChart"></canvas>
          </div>
        </div>
      </div>
      <div class="mt-4">
        <button 
          @click="generatePredictions(true)" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          生成预测
        </button>
      </div>
    </div>
    
    <!-- 学习对比分析 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">学习对比分析</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-gray-50 rounded-lg p-4">
          <div class="text-sm text-gray-500">我的平均进度</div>
          <div class="text-2xl font-bold text-blue-600">{{ comparisonData.user_avg_progress.toFixed(1) }}%</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-4">
          <div class="text-sm text-gray-500">平均进度</div>
          <div class="text-2xl font-bold text-green-600">{{ comparisonData.average_progress.toFixed(1) }}%</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-4">
          <div class="text-sm text-gray-500">百分位数</div>
          <div class="text-2xl font-bold text-purple-600">{{ comparisonData.percentile }}%</div>
        </div>
      </div>
      <div class="h-64">
        <canvas ref="comparisonChart"></canvas>
      </div>
      <div class="mt-4">
        <h4 class="font-medium mb-2">改进建议</h4>
        <ul class="list-disc pl-5 space-y-1 text-gray-600">
          <li v-for="(recommendation, index) in comparisonData.recommendations" :key="index">
            {{ recommendation }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

// 注册Chart.js组件
Chart.register(...registerables)

// 响应式数据
const recentBehaviors = ref([])
const behaviorStats = ref({})
const predictions = ref([])
const comparisonData = ref({
  user_avg_progress: 0,
  average_progress: 50,
  percentile: 75,
  recommendations: [
    '继续保持当前的学习节奏',
    '可以尝试增加学习时间',
    '建议重点关注未完成的模块'
  ]
})
const charts = ref({})
const refreshTimer = ref(null)
const allModules = ref([])
const isGeneratingPredictions = ref(false)
const isMounted = ref(true)

// 模板引用
const timeDistributionChart = ref(null)
const behaviorTypeChart = ref(null)
const completionTimeChart = ref(null)
const successProbabilityChart = ref(null)
const comparisonChart = ref(null)

// 初始化数据
const initializeData = async () => {
  try {
    console.log('开始初始化数据...')
    // 先获取所有模块
    await fetchAllModules()
    console.log('获取模块完成，数量:', allModules.value.length)
    // 为所有模块生成预测
    await generatePredictions()
    // 获取其他数据
    await fetchBehaviorData()
    await fetchComparisonData()
    console.log('数据初始化完成...')
  } catch (error) {
    console.error('初始化数据失败:', error)
  }
}

// 获取学习行为数据
const fetchBehaviorData = async () => {
  try {
    const response = await fetch('/api/learning/analytics/behavior/default')
    if (response.ok) {
      const data = await response.json()
      if (data.status === 'success') {
        recentBehaviors.value = data.behaviors.slice(0, 10)
        behaviorStats.value = data.behavior_stats
        nextTick(() => {
          renderBehaviorCharts()
        })
      }
    }
  } catch (error) {
    console.error('获取学习行为数据失败:', error)
  }
}

// 获取学习对比数据
const fetchComparisonData = async () => {
  try {
    const response = await fetch('/api/learning/analytics/comparison/default')
    if (response.ok) {
      const data = await response.json()
      if (data.status === 'success') {
        comparisonData.value = data.comparison
        nextTick(() => {
          renderComparisonChart()
        })
      }
    }
  } catch (error) {
    console.error('获取学习对比数据失败:', error)
  }
}

// 获取预测数据
const fetchPredictions = async () => {
  try {
    console.log('开始获取预测数据...')
    const response = await fetch('/api/learning/analytics/prediction/default')
    console.log('获取预测数据响应状态:', response.status)
    if (response.ok) {
      const data = await response.json()
      console.log('获取到的预测数据:', data)
      if (data.status === 'success') {
        predictions.value = data.predictions
        console.log('处理后的预测数据:', predictions.value)
        console.log('预测数据数量:', predictions.value.length)
        nextTick(() => {
          renderPredictionCharts()
        })
      }
    }
  } catch (error) {
    console.error('获取学习预测数据失败:', error)
  }
}

// 获取所有模块
const fetchAllModules = async () => {
  try {
    console.log('开始获取模块数据...')
    // 先获取所有学习计划
    const plansResponse = await fetch('/api/learning/plans')
    console.log('获取学习计划响应状态:', plansResponse.status)
    if (plansResponse.ok) {
      const plans = await plansResponse.json()
      console.log('获取到的学习计划数量:', plans.length)
      // 收集所有模块
      const modulesPromises = plans.map(plan => 
        fetch(`/api/learning/modules/${plan.id}`)
          .then(res => {
            console.log(`获取模块 ${plan.id} 响应状态:`, res.status)
            return res.json()
          })
          .catch(err => {
            console.error(`获取模块 ${plan.id} 失败:`, err)
            return []
          })
      )
      const modulesArrays = await Promise.all(modulesPromises)
      allModules.value = modulesArrays.flat()
      console.log('获取到的模块总数:', allModules.value.length)
      console.log('获取到的模块:', allModules.value)
    }
  } catch (error) {
    console.error('获取模块失败:', error)
  }
}

// 生成预测
const generatePredictions = async (showAlert = false) => {
  try {
    console.log('开始生成预测...')
    console.log('当前模块数量:', allModules.value.length)
    console.log('当前模块:', allModules.value)
    isGeneratingPredictions.value = true
    
    // 为每个模块生成预测
    const promises = allModules.value.filter(module => module.id).map(async (module) => {
      try {
        console.log(`为模块 ${module.id} 生成预测...`)
        // 创建FormData对象
        const formData = new FormData()
        formData.append('user_id', 'default')
        formData.append('module_id', module.id)
        
        const response = await fetch('/api/learning/analytics/generate-prediction', {
          method: 'POST',
          body: formData
        })
        console.log(`为模块 ${module.id} 生成预测响应状态:`, response.status)
        if (response.ok) {
          const data = await response.json()
          console.log(`为模块 ${module.id} 生成预测响应数据:`, data)
        }
        return response.ok
      } catch (error) {
        console.error(`为模块 ${module.id} 生成预测失败:`, error)
        return false
      }
    })
    
    // 如果没有模块，生成默认预测
    if (allModules.value.length === 0) {
      console.log('没有模块，生成默认预测...')
      try {
        const response = await fetch('/api/learning/analytics/generate-prediction', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        })
        console.log('生成默认预测响应状态:', response.status)
        if (response.ok) {
          const data = await response.json()
          console.log('生成默认预测响应数据:', data)
        }
      } catch (error) {
        console.error('生成默认预测失败:', error)
      }
    }
    
    console.log('等待所有预测生成完成...')
    const results = await Promise.all(promises)
    console.log('预测生成结果:', results)
    
    console.log('预测生成成功，开始获取预测数据...')
    await fetchPredictions()
    console.log('获取预测数据完成，当前预测数量:', predictions.value.length)
    console.log('当前预测数据:', predictions.value)
    
    // 只有在手动点击按钮时才显示提示
    if (showAlert) {
      alert('预测生成成功')
    }
  } catch (error) {
    console.error('生成学习预测失败:', error)
    if (showAlert) {
      alert('生成预测失败')
    }
  } finally {
    isGeneratingPredictions.value = false
  }
}

// 渲染行为图表
const renderBehaviorCharts = () => {
  renderTimeDistributionChart()
  renderBehaviorTypeChart()
}

// 渲染时间分布图表
const renderTimeDistributionChart = () => {
  // 检查组件是否已挂载
  if (!isMounted.value) return
  
  const canvas = timeDistributionChart.value
  if (!canvas || !canvas.getContext) return
  
  // 检查canvas是否已连接到DOM且尺寸有效
  if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // 使用真实的学习行为数据计算每小时的学习时长
  const hours = Array.from({ length: 24 }, (_, i) => i)
  const hourlyData = Array.from({ length: 24 }, () => 0)
  
  // 遍历学习行为数据，计算每小时的学习时长
  recentBehaviors.value.forEach(behavior => {
    if (behavior.timestamp && behavior.duration) {
      const date = new Date(behavior.timestamp * 1000)
      const hour = date.getHours()
      if (hour >= 0 && hour < 24) {
        // 将秒转换为分钟
        hourlyData[hour] += behavior.duration / 60
      }
    }
  })
  
  if (charts.value.timeDistribution) {
    charts.value.timeDistribution.destroy()
    charts.value.timeDistribution = null
  }
  
  charts.value.timeDistribution = new Chart(ctx, {
    type: 'line',
    data: {
      labels: hours.map(h => `${h}:00`),
      datasets: [{
        label: '学习时长（分钟）',
        data: hourlyData.map(Math.round), // 四舍五入到整数
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  })
}

// 渲染行为类型图表
const renderBehaviorTypeChart = () => {
  // 检查组件是否已挂载
  if (!isMounted.value) return
  
  const canvas = behaviorTypeChart.value
  if (!canvas || !canvas.getContext) return
  
  // 检查canvas是否已连接到DOM且尺寸有效
  if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const behaviorTypes = Object.keys(behaviorStats.value || {})
  const data = behaviorTypes.map(type => behaviorStats.value[type]?.count || 0)
  
  if (charts.value.behaviorType) {
    charts.value.behaviorType.destroy()
    charts.value.behaviorType = null
  }
  
  charts.value.behaviorType = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: behaviorTypes.map(getBehaviorTypeName),
      datasets: [{
        label: '行为次数',
        data: data,
        backgroundColor: 'rgba(75, 192, 192, 0.6)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  })
}

// 渲染预测图表
const renderPredictionCharts = () => {
  renderCompletionTimeChart()
  renderSuccessProbabilityChart()
}

// 渲染完成时间预测图表
const renderCompletionTimeChart = () => {
  // 检查组件是否已挂载
  if (!isMounted.value) return
  
  const canvas = completionTimeChart.value
  if (!canvas || !canvas.getContext) return
  
  // 检查canvas是否已连接到DOM且尺寸有效
  if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // 使用真实的预测数据
  let modules = []
  let data = []
  
  if (predictions.value && predictions.value.length > 0) {
    // 从预测数据中提取模块ID和预计完成时间
    modules = predictions.value.map((p, index) => {
      if (p.module_id) {
        return p.module_id
      } else {
        const moduleName = `模块${index + 1}`
        return moduleName
      }
    })
    data = predictions.value.map(p => {
      // 计算预计完成时间（分钟）
      if (p.predicted_completion_time) {
        const now = Date.now() / 1000
        const seconds = Math.max(0, p.predicted_completion_time - now)
        return Math.round(seconds / 60) // 转换为分钟
      }
      return 0
    })
    console.log('处理后的模块名称:', modules)
    console.log('处理后的数据:', data)
  } else if (allModules.value && allModules.value.length > 0) {
    // 如果没有预测数据，但有模块数据，为每个模块显示默认预测
    modules = allModules.value.map((module, index) => {
      if (module.id) {
        return module.id
      } else {
        const moduleName = `模块${index + 1}`
        return moduleName
      }
    })
    data = allModules.value.map(() => 0) // 为每个模块显示默认值
    console.log('使用模块数据生成默认预测:', modules)
  } else {
    // 如果没有预测数据和模块数据，显示默认值
    modules = ['暂无数据']
    data = [0]
  }
  
  if (charts.value.completionTime) {
    charts.value.completionTime.destroy()
    charts.value.completionTime = null
  }
  
  charts.value.completionTime = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: modules,
      datasets: [{
        label: '预计完成时间（分钟）',
        data: data,
        backgroundColor: 'rgba(255, 99, 132, 0.6)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  })
}

// 渲染成功概率分析图表
const renderSuccessProbabilityChart = () => {
  // 检查组件是否已挂载
  if (!isMounted.value) return
  
  const canvas = successProbabilityChart.value
  if (!canvas || !canvas.getContext) return
  
  // 检查canvas是否已连接到DOM且尺寸有效
  if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // 使用真实的预测数据
  let modules = []
  let data = []
  
  if (predictions.value && predictions.value.length > 0) {
    // 从预测数据中提取模块ID和成功概率
    modules = predictions.value.map((p, index) => {
      if (p.module_id) {
        return p.module_id
      } else {
        const moduleName = `模块${index + 1}`
        return moduleName
      }
    })
    data = predictions.value.map(p => p.success_probability || 0)
    console.log('成功概率图表处理后的模块名称:', modules)
    console.log('成功概率图表处理后的数据:', data)
  } else if (allModules.value && allModules.value.length > 0) {
    // 如果没有预测数据，但有模块数据，为每个模块显示默认预测
    modules = allModules.value.map((module, index) => {
      if (module.id) {
        return module.id
      } else {
        const moduleName = `模块${index + 1}`
        return moduleName
      }
    })
    data = allModules.value.map(() => 0.7) // 为每个模块显示默认成功概率
    console.log('使用模块数据生成默认成功概率预测:', modules)
  } else {
    // 如果没有预测数据和模块数据，显示默认值
    modules = ['暂无数据']
    data = [0]
  }
  
  if (charts.value.successProbability) {
    charts.value.successProbability.destroy()
    charts.value.successProbability = null
  }
  
  charts.value.successProbability = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: modules,
      datasets: [{
        label: '成功概率',
        data: data,
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        borderColor: 'rgba(153, 102, 255, 1)',
        pointBackgroundColor: 'rgba(153, 102, 255, 1)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 1
        }
      }
    }
  })
}

// 渲染对比图表
const renderComparisonChart = () => {
  // 检查组件是否已挂载
  if (!isMounted.value) return
  
  const canvas = comparisonChart.value
  if (!canvas || !canvas.getContext) return
  
  // 检查canvas是否已连接到DOM且尺寸有效
  if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // 使用真实的对比数据
  const labels = ['我的进度', '平均进度', '目标进度']
  const data = [
    comparisonData.value.user_avg_progress,
    comparisonData.value.average_progress,
    90 // 目标进度固定为90%
  ]
  
  if (charts.value.comparison) {
    charts.value.comparison.destroy()
    charts.value.comparison = null
  }
  
  charts.value.comparison = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '进度百分比',
        data: data,
        backgroundColor: [
          'rgba(54, 162, 235, 0.6)',
          'rgba(75, 192, 192, 0.6)',
          'rgba(255, 206, 86, 0.6)'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100
        }
      }
    }
  })
}

// 获取行为类型名称
const getBehaviorTypeName = (type) => {
  const types = {
    view: '查看',
    study: '学习',
    quiz: '测验',
    pause: '暂停',
    resume: '继续'
  }
  return types[type] || type
}

// 格式化持续时间
const formatDuration = (seconds) => {
  if (!seconds) return '0秒'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}

// 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

// 组件挂载时
onMounted(() => {
  // 初始获取数据
  initializeData()
  
  // 设置定时刷新，每10秒更新一次数据
  refreshTimer.value = setInterval(() => {
    console.log('定时刷新数据...')
    initializeData()
  }, 10000)
})

// 组件卸载前
onBeforeUnmount(() => {
  // 设置为未挂载状态
  isMounted.value = false
  
  // 清除定时器
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
  
  // 销毁图表实例
  Object.values(charts.value).forEach(chart => {
    if (chart) {
      chart.destroy()
    }
  })
})
</script>

<style scoped>
.advanced-analytics {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
</style>