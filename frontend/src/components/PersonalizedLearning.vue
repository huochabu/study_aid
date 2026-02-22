<template>
  <div class="personalized-learning">
    <h2 class="text-2xl font-bold mb-6">个性化学习</h2>
    
    <!-- 学习偏好设置 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习偏好设置</h3>
      <form @submit.prevent="updatePreferences">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">学习风格</label>
            <select 
              v-model="preferences.learning_style" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="visual">视觉型（通过图片、图表学习）</option>
              <option value="auditory">听觉型（通过听讲、讨论学习）</option>
              <option value="kinesthetic">动觉型（通过实践、操作学习）</option>
              <option value="read_write">读写型（通过阅读、写作学习）</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">偏好难度</label>
            <select 
              v-model="preferences.preferred_difficulty" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="easy">简单</option>
              <option value="medium">中等</option>
              <option value="hard">困难</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">学习时间偏好</label>
            <select 
              v-model="preferences.study_time_preference" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="morning">早晨</option>
              <option value="afternoon">下午</option>
              <option value="evening">晚上</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">学习目标</label>
            <input 
              v-model="learningGoal" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="输入学习目标"
            >
          </div>
        </div>
        <button 
          type="submit" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          保存偏好设置
        </button>
      </form>
    </div>
    
    <!-- 学习风格检测 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">学习风格检测</h3>
      <div v-if="!showStyleTest" class="text-center py-8">
        <p class="text-gray-600 mb-4">通过回答几个问题，检测您的学习风格</p>
        <button 
          @click="showStyleTest = true" 
          class="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          开始检测
        </button>
      </div>
      <div v-else class="space-y-4">
        <div v-for="(question, index) in styleTestQuestions" :key="index" class="border border-gray-200 rounded-lg p-4">
          <h4 class="font-medium mb-2">{{ question.question }}</h4>
          <div class="space-y-2">
            <div 
              v-for="(option, optIndex) in question.options" 
              :key="optIndex"
              class="flex items-center"
            >
              <input 
                type="radio" 
                :name="`question-${index}`" 
                :value="option.value"
                v-model="styleTestAnswers[index]"
                class="mr-2"
              >
              <label>{{ option.text }}</label>
            </div>
          </div>
        </div>
        <div class="flex justify-end">
          <button 
            @click="showStyleTest = false" 
            class="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors mr-2"
          >
            取消
          </button>
          <button 
            @click="submitStyleTest" 
            class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            提交检测
          </button>
        </div>
      </div>
    </div>
    
    <!-- 自适应学习路径 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">自适应学习路径</h3>
      <div v-if="adaptivePath.length === 0" class="text-center py-8 text-gray-500">
        基于您的学习偏好和进度，系统将为您生成个性化的学习路径
      </div>
      <div v-else class="space-y-3">
        <div 
          v-for="(item, index) in adaptivePath" 
          :key="index"
          class="border border-gray-200 rounded-lg p-3"
        >
          <div class="flex justify-between items-center">
            <h4 class="font-medium">{{ item.title }}</h4>
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                item.priority === 'high' ? 'bg-red-100 text-red-800' :
                item.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-green-100 text-green-800'
              ]"
            >
              {{ item.priority === 'high' ? '高优先级' : item.priority === 'medium' ? '中优先级' : '低优先级' }}
            </span>
          </div>
          <p class="text-sm text-gray-600 mt-1">{{ item.description }}</p>
          <div class="text-xs text-gray-500 mt-1">
            预计学习时间: {{ item.estimated_time }}分钟
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PersonalizedLearning',
  data() {
    return {
      preferences: {
        learning_style: 'visual',
        preferred_difficulty: 'medium',
        study_time_preference: 'afternoon',
        goals: {}
      },
      learningGoal: '',
      showStyleTest: false,
      styleTestQuestions: [
        {
          question: '当学习新内容时，您更喜欢：',
          options: [
            { text: '看图片、图表或视频', value: 'visual' },
            { text: '听讲解或讨论', value: 'auditory' },
            { text: '动手实践或操作', value: 'kinesthetic' },
            { text: '阅读文字材料', value: 'read_write' }
          ]
        },
        {
          question: '当有人给您指路时，您会：',
          options: [
            { text: '需要地图或画图', value: 'visual' },
            { text: '需要对方解释清楚', value: 'auditory' },
            { text: '需要亲自走一遍', value: 'kinesthetic' },
            { text: '需要写下来或看文字说明', value: 'read_write' }
          ]
        },
        {
          question: '当学习时，您会：',
          options: [
            { text: '做笔记、画图表', value: 'visual' },
            { text: '大声朗读或讨论', value: 'auditory' },
            { text: '走来走去或做手势', value: 'kinesthetic' },
            { text: '反复阅读和写笔记', value: 'read_write' }
          ]
        }
      ],
      styleTestAnswers: [],
      adaptivePath: []
    }
  },
  mounted() {
    this.fetchPreferences()
    this.generateAdaptivePath()
  },
  methods: {
    async fetchPreferences() {
      try {
        const response = await fetch('/api/learning/preferences/default')
        if (response.ok) {
          const data = await response.json()
          if (data.status === 'success' && data.preferences) {
            this.preferences = data.preferences
            if (this.preferences.goals && this.preferences.goals.main) {
              this.learningGoal = this.preferences.goals.main
            }
          }
        }
      } catch (error) {
        console.error('获取学习偏好失败:', error)
      }
    },
    
    async updatePreferences() {
      try {
        // 更新学习目标
        if (this.learningGoal) {
          this.preferences.goals = {
            main: this.learningGoal
          }
        }
        
        const response = await fetch('/api/learning/preferences', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            learning_style: this.preferences.learning_style,
            preferred_difficulty: this.preferences.preferred_difficulty,
            study_time_preference: this.preferences.study_time_preference,
            goals: this.preferences.goals
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          if (data.status === 'success') {
            alert('学习偏好已更新')
            this.generateAdaptivePath()
          }
        }
      } catch (error) {
        console.error('更新学习偏好失败:', error)
        alert('更新学习偏好失败')
      }
    },
    
    submitStyleTest() {
      // 分析学习风格测试结果
      const styleCounts = {
        visual: 0,
        auditory: 0,
        kinesthetic: 0,
        read_write: 0
      }
      
      this.styleTestAnswers.forEach(answer => {
        if (answer) {
          styleCounts[answer]++
        }
      })
      
      // 找出最常见的学习风格
      let dominantStyle = 'visual'
      let maxCount = 0
      
      for (const [style, count] of Object.entries(styleCounts)) {
        if (count > maxCount) {
          maxCount = count
          dominantStyle = style
        }
      }
      
      // 更新学习风格
      this.preferences.learning_style = dominantStyle
      this.showStyleTest = false
      
      // 显示结果
      const styleNames = {
        visual: '视觉型',
        auditory: '听觉型',
        kinesthetic: '动觉型',
        read_write: '读写型'
      }
      
      alert(`您的学习风格是：${styleNames[dominantStyle]}\n\n建议：${this.getStyleSuggestion(dominantStyle)}`)
    },
    
    getStyleSuggestion(style) {
      const suggestions = {
        visual: '使用图表、图片、思维导图等视觉工具学习，多做笔记和标记',
        auditory: '参加讨论、听讲义、使用录音设备，大声朗读学习材料',
        kinesthetic: '通过实践操作学习，使用手势辅助记忆，多做实验和练习',
        read_write: '多阅读、做详细笔记、写总结，使用列表和提纲组织信息'
      }
      return suggestions[style] || ''
    },
    
    generateAdaptivePath() {
      // 基于学习偏好生成自适应学习路径
      this.adaptivePath = [
        {
          title: '核心概念学习',
          description: '学习本课程的核心概念和基础理论',
          estimated_time: 60,
          priority: 'high'
        },
        {
          title: '实践练习',
          description: '通过实际操作巩固所学知识',
          estimated_time: 90,
          priority: 'medium'
        },
        {
          title: '知识拓展',
          description: '学习相关的扩展知识和前沿内容',
          estimated_time: 45,
          priority: 'low'
        }
      ]
      
      // 根据学习风格调整路径
      if (this.preferences.learning_style === 'visual') {
        this.adaptivePath.unshift({
          title: '可视化学习',
          description: '通过图表、思维导图等视觉工具学习核心概念',
          estimated_time: 45,
          priority: 'high'
        })
      } else if (this.preferences.learning_style === 'auditory') {
        this.adaptivePath.unshift({
          title: '听觉学习',
          description: '通过听讲、讨论等方式学习核心概念',
          estimated_time: 45,
          priority: 'high'
        })
      } else if (this.preferences.learning_style === 'kinesthetic') {
        this.adaptivePath.unshift({
          title: '动手实践',
          description: '通过实际操作学习核心概念',
          estimated_time: 60,
          priority: 'high'
        })
      }
    }
  }
}
</script>

<style scoped>
.personalized-learning {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
</style>