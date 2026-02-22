<template>
  <div class="learning-analytics">
    <h2 class="text-2xl font-bold mb-6">学习数据可视化</h2>
    
    <!-- 数据筛选 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <div class="flex flex-wrap gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
          <input 
            v-model="filterStartDate" 
            type="date" 
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
          <input 
            v-model="filterEndDate" 
            type="date" 
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
        <div class="flex items-end">
          <button 
            @click="fetchAnalyticsData" 
            class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            应用筛选
          </button>
        </div>
      </div>
    </div>
    
    <!-- 学习概览卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-500 mb-1">总学习时间</div>
        <div class="text-2xl font-bold">{{ formatTime(analyticsData.total_study_time) }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-500 mb-1">测验时间</div>
        <div class="text-2xl font-bold">{{ formatTime(analyticsData.total_quiz_time) }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-500 mb-1">活动次数</div>
        <div class="text-2xl font-bold">{{ analyticsData.activity_count }}</div>
      </div>
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-500 mb-1">完成模块数</div>
        <div class="text-2xl font-bold">{{ completedModulesCount }}</div>
      </div>
    </div>
    
    <!-- 学习时间趋势图 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习时间趋势</h3>
      <div class="h-80">
        <canvas ref="timeChart"></canvas>
      </div>
    </div>
    
    <!-- 学习活动类型分布 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习活动类型分布</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="h-64">
          <canvas ref="activityChart"></canvas>
        </div>
        <div>
          <h4 class="text-md font-medium mb-2">活动类型详情</h4>
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="flex items-center">
                <span class="w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
                学习
              </span>
              <span class="font-medium">{{ formatTime(studyTimeByType) }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="flex items-center">
                <span class="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                测验
              </span>
              <span class="font-medium">{{ formatTime(quizTimeByType) }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="flex items-center">
                <span class="w-3 h-3 bg-purple-500 rounded-full mr-2"></span>
                笔记
              </span>
              <span class="font-medium">{{ formatTime(noteTimeByType) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 学习进度分析 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">学习进度分析</h3>
      <div v-if="plansWithProgress.length === 0" class="text-center py-8 text-gray-500">
        暂无学习计划数据
      </div>
      <div v-else class="space-y-4">
        <div 
          v-for="plan in plansWithProgress" 
          :key="plan.id" 
          class="border border-gray-200 rounded-lg p-4"
        >
          <div class="flex justify-between items-start mb-2">
            <h4 class="text-md font-medium">{{ plan.title }}</h4>
            <span class="text-sm font-medium">{{ plan.progress }}%</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2 mb-3">
            <div 
              class="bg-blue-500 h-2 rounded-full transition-all duration-500"
              :style="{ width: plan.progress + '%' }"
            ></div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-500">
            <span>模块数: {{ plan.moduleCount }}</span>
            <span>完成: {{ plan.completedModules }}</span>
            <span>开始: {{ formatDate(plan.start_date) }}</span>
            <span>结束: {{ formatDate(plan.end_date) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export default {
  name: 'LearningAnalytics',
  data() {
    return {
      filterStartDate: '',
      filterEndDate: '',
      analyticsData: {
        total_study_time: 0,
        total_quiz_time: 0,
        activity_count: 0,
        activities: []
      },
      plansWithProgress: [],
      timeChart: null,
      activityChart: null,
      refreshTimer: null
    }
  },
  computed: {
    completedModulesCount() {
      return this.plansWithProgress.reduce((sum, plan) => sum + plan.completedModules, 0)
    },
    studyTimeByType() {
      return this.analyticsData.activities.filter(a => a.activity_type === 'study').reduce((sum, a) => sum + a.duration, 0)
    },
    quizTimeByType() {
      return this.analyticsData.activities.filter(a => a.activity_type === 'quiz').reduce((sum, a) => sum + a.duration, 0)
    },
    noteTimeByType() {
      return this.analyticsData.activities.filter(a => a.activity_type === 'note').reduce((sum, a) => sum + a.duration, 0)
    }
  },
  mounted() {
    // 初始获取数据
    this.fetchAnalyticsData()
    this.fetchPlansWithProgress()
    
    // 设置定时刷新，每30秒更新一次数据
    this.refreshTimer = setInterval(() => {
      this.fetchAnalyticsData()
      this.fetchPlansWithProgress()
    }, 30000)
  },
  beforeUnmount() {
    // 清除定时器
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer)
      this.refreshTimer = null
    }
    
    // 销毁图表实例
    if (this.timeChart) {
      this.timeChart.destroy()
      this.timeChart = null
    }
    if (this.activityChart) {
      this.activityChart.destroy()
      this.activityChart = null
    }
  },
  methods: {
    async fetchAnalyticsData() {
      try {
        const startDate = this.filterStartDate ? new Date(this.filterStartDate).getTime() / 1000 : null
        const endDate = this.filterEndDate ? new Date(this.filterEndDate).getTime() / 1000 : null
        
        const params = new URLSearchParams()
        if (startDate) params.append('start_date', startDate)
        if (endDate) params.append('end_date', endDate)
        
        const response = await fetch(`/api/learning/analytics/default?${params.toString()}`)
        if (response.ok) {
          this.analyticsData = await response.json()
          this.$nextTick(() => {
            this.initCharts()
          })
        }
      } catch (error) {
        console.error('获取分析数据失败:', error)
      }
    },
    
    async fetchPlansWithProgress() {
      try {
        // 获取所有学习计划
        const plansResponse = await fetch('/api/learning/plans')
        if (plansResponse.ok) {
          const plans = await plansResponse.json()
          
          // 获取每个计划的进度
          const plansWithProgress = await Promise.all(
            plans.map(async (plan) => {
              try {
                const progressResponse = await fetch(`/api/learning/progress/${plan.id}`)
                if (progressResponse.ok) {
                  const progressData = await progressResponse.json()
                  const moduleCount = progressData.module_progress.length
                  const completedModules = progressData.module_progress.filter(mp => mp.progress === 100).length
                  
                  return {
                    ...plan,
                    progress: progressData.overall_progress,
                    moduleCount,
                    completedModules
                  }
                }
                return {
                  ...plan,
                  progress: 0,
                  moduleCount: 0,
                  completedModules: 0
                }
              } catch (error) {
                console.error('获取计划进度失败:', error)
                return {
                  ...plan,
                  progress: 0,
                  moduleCount: 0,
                  completedModules: 0
                }
              }
            })
          )
          
          this.plansWithProgress = plansWithProgress
        }
      } catch (error) {
        console.error('获取学习计划失败:', error)
      }
    },
    
    initCharts() {
      this.initTimeChart()
      this.initActivityChart()
    },
    
    initTimeChart() {
      if (this.timeChart) {
        this.timeChart.destroy()
        this.timeChart = null
      }
      
      const canvas = this.$refs.timeChart
      if (!canvas || !canvas.getContext) return
      
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      
      // 检查canvas是否已连接到DOM且尺寸有效
      if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
      
      // 按日期分组活动数据
      const activitiesByDate = this.groupActivitiesByDate()
      
      // 准备图表数据
      const labels = Object.keys(activitiesByDate).map(dateStr => {
        const date = new Date(parseInt(dateStr))
        return `${date.getMonth() + 1}/${date.getDate()}`
      })
      
      const datasets = [
        {
          label: '学习时间（分钟）',
          data: Object.values(activitiesByDate).map(dayData => dayData.studyTime / 60),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: '测验时间（分钟）',
          data: Object.values(activitiesByDate).map(dayData => dayData.quizTime / 60),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
      
      // 使用已导入的Chart.js
      this.timeChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'top'
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                title: {
                  display: true,
                  text: '时间（分钟）'
                }
              }
            }
          }
        })
    },
    
    initActivityChart() {
      if (this.activityChart) {
        this.activityChart.destroy()
        this.activityChart = null
      }
      
      const canvas = this.$refs.activityChart
      if (!canvas || !canvas.getContext) return
      
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      
      // 检查canvas是否已连接到DOM且尺寸有效
      if (!canvas.offsetParent || canvas.width === 0 || canvas.height === 0) return
      
      // 准备图表数据
      const data = [
        this.studyTimeByType,
        this.quizTimeByType,
        this.noteTimeByType
      ]
      
      const labels = ['学习', '测验', '笔记']
      const backgroundColor = ['#3b82f6', '#10b981', '#8b5cf6']
      
      // 使用已导入的Chart.js
      this.activityChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels,
            datasets: [{
              data,
              backgroundColor,
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom'
              }
            }
          }
        })
    },
    
    groupActivitiesByDate() {
      const activitiesByDate = {}
      
      this.analyticsData.activities.forEach(activity => {
        if (activity.timestamp) {
          const date = new Date(activity.timestamp * 1000)
          const dateKey = date.toDateString()
          
          if (!activitiesByDate[dateKey]) {
            activitiesByDate[dateKey] = {
              studyTime: 0,
              quizTime: 0,
              noteTime: 0
            }
          }
          
          if (activity.activity_type === 'study') {
            activitiesByDate[dateKey].studyTime += activity.duration
          } else if (activity.activity_type === 'quiz') {
            activitiesByDate[dateKey].quizTime += activity.duration
          } else if (activity.activity_type === 'note') {
            activitiesByDate[dateKey].noteTime += activity.duration
          }
        }
      })
      
      return activitiesByDate
    },
    
    formatTime(seconds) {
      if (!seconds) return '0分钟'
      
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      
      if (hours > 0) {
        return `${hours}小时${minutes}分钟`
      }
      return `${minutes}分钟`
    },
    
    formatDate(timestamp) {
      if (!timestamp) return '未知'
      const date = new Date(timestamp * 1000)
      return date.toLocaleDateString('zh-CN')
    }
  }
}
</script>

<style scoped>
.learning-analytics {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>