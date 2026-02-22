<template>
  <div class="collaboration-manager">
    <h2 class="text-2xl font-bold mb-6">协作学习管理</h2>
    
    <!-- 加入协作计划 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">加入协作学习计划</h3>
      <form @submit.prevent="joinCollaboration">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">计划ID</label>
            <input 
              v-model="joinForm.planId" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              placeholder="输入学习计划的ID"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">角色</label>
            <select 
              v-model="joinForm.role" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="contributor">贡献者</option>
              <option value="owner">所有者</option>
            </select>
          </div>
        </div>
        <button 
          type="submit" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          加入协作
        </button>
      </form>
    </div>
    
    <!-- 我的协作计划 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">我的协作计划</h3>
      <div v-if="collaborations.length === 0" class="text-center py-8 text-gray-500">
        暂无协作计划，点击上方按钮加入
      </div>
      <div v-else class="space-y-4">
        <div 
          v-for="collab in collaborations" 
          :key="collab.id" 
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <h4 class="text-lg font-medium">{{ getPlanTitle(collab.plan_id) }}</h4>
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                collab.role === 'owner' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
              ]"
            >
              {{ collab.role === 'owner' ? '所有者' : '贡献者' }}
            </span>
          </div>
          <div class="flex flex-wrap gap-4 mb-3 text-sm text-gray-500">
            <span>计划ID: {{ collab.plan_id }}</span>
            <span>加入时间: {{ formatDate(collab.joined_at) }}</span>
          </div>
          <div class="flex gap-2 mt-3">
            <button 
              @click="viewCollaborators(collab.plan_id)" 
              class="bg-green-500 hover:bg-green-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              查看协作者
            </button>
            <button 
              @click="viewPlanDetails(collab.plan_id)" 
              class="bg-gray-500 hover:bg-gray-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              查看计划详情
            </button>
            <button 
              @click="leaveCollaboration(collab.plan_id)" 
              class="bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              退出协作
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 协作者列表弹窗 -->
    <div v-if="showCollaborators" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-lg font-semibold">协作者列表</h3>
          <button @click="showCollaborators = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div v-if="currentCollaborators.length === 0" class="text-center py-4 text-gray-500">
          暂无协作者
        </div>
        <div v-else class="space-y-3">
          <div 
            v-for="(collaborator, index) in currentCollaborators" 
            :key="index" 
            class="border border-gray-200 rounded-lg p-3"
          >
            <div class="flex justify-between items-center">
              <span class="font-medium">{{ collaborator.user_id }}</span>
              <span 
                :class="[
                  'px-2 py-1 text-xs rounded-full font-medium',
                  collaborator.role === 'owner' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                ]"
              >
                {{ collaborator.role === 'owner' ? '所有者' : '贡献者' }}
              </span>
            </div>
            <div class="text-xs text-gray-500 mt-1">
              加入时间: {{ formatDate(collaborator.joined_at) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CollaborationManager',
  data() {
    return {
      collaborations: [],
      plans: [],
      joinForm: {
        planId: '',
        role: 'contributor'
      },
      showCollaborators: false,
      currentCollaborators: [],
      currentPlanId: ''
    }
  },
  mounted() {
    this.fetchCollaborations()
    this.fetchPlans()
  },
  methods: {
    async fetchCollaborations() {
      try {
        // 获取所有学习计划
        const plansResponse = await fetch('/api/learning/plans')
        if (plansResponse.ok) {
          const plans = await plansResponse.json()
          this.plans = plans
          
          // 为每个计划获取协作记录
          const collaborationsPromises = plans.map(async (plan) => {
            try {
              const collabResponse = await fetch(`/api/learning/collaboration/${plan.id}`)
              if (collabResponse.ok) {
                const collabs = await collabResponse.json()
                // 只获取当前用户的协作记录，并添加计划ID
                return collabs.filter(collab => collab.user_id === 'default').map(collab => ({
                  ...collab,
                  plan_id: plan.id
                }))
              }
            } catch (error) {
              console.error(`获取计划 ${plan.id} 的协作记录失败:`, error)
            }
            return []
          })
          
          const collaborationsArrays = await Promise.all(collaborationsPromises)
          this.collaborations = collaborationsArrays.flat().filter(collab => collab.user_id === 'default')
        }
      } catch (error) {
        console.error('获取协作记录失败:', error)
      }
    },
    
    async fetchPlans() {
      try {
        const response = await fetch('/api/learning/plans')
        if (response.ok) {
          this.plans = await response.json()
        }
      } catch (error) {
        console.error('获取学习计划失败:', error)
      }
    },
    
    async joinCollaboration() {
      try {
        const response = await fetch('/api/learning/collaboration', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            plan_id: this.joinForm.planId,
            role: this.joinForm.role
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          alert('加入协作成功！')
          // 重置表单
          this.joinForm = {
            planId: '',
            role: 'contributor'
          }
          // 刷新协作列表
          await this.fetchCollaborations()
        }
      } catch (error) {
        console.error('加入协作失败:', error)
        alert('加入协作失败，请检查计划ID是否正确')
      }
    },
    
    async viewCollaborators(planId) {
      try {
        const response = await fetch(`/api/learning/collaboration/${planId}`)
        if (response.ok) {
          this.currentCollaborators = await response.json()
          this.currentPlanId = planId
          this.showCollaborators = true
        }
      } catch (error) {
        console.error('获取协作者列表失败:', error)
      }
    },
    
    async viewPlanDetails(planId) {
      try {
        // 获取计划详情
        const response = await fetch(`/api/learning/plans/${planId}`)
        if (response.ok) {
          const planDetails = await response.json()
          // 显示计划详情弹窗或跳转到详情页面
          alert(`计划详情:\n标题: ${planDetails.title}\n描述: ${planDetails.description}\n状态: ${planDetails.status === 'active' ? '进行中' : planDetails.status === 'completed' ? '已完成' : '暂停'}\n开始时间: ${this.formatDate(planDetails.start_date)}\n结束时间: ${this.formatDate(planDetails.end_date)}\n模块数量: ${planDetails.modules.length}`)
        } else {
          alert('获取计划详情失败')
        }
      } catch (error) {
        console.error('获取计划详情失败:', error)
        alert('获取计划详情失败')
      }
    },
    
    async leaveCollaboration(planId) {
      if (confirm('确定要退出这个协作计划吗？')) {
        try {
          const response = await fetch(`/api/learning/collaboration/${planId}`, {
            method: 'DELETE'
          })
          if (response.ok) {
            await this.fetchCollaborations()
            alert('成功退出协作')
          } else {
            const errorData = await response.json()
            alert('退出协作失败: ' + (errorData.detail || '未知错误'))
          }
        } catch (error) {
          console.error('退出协作失败:', error)
          alert('退出协作失败')
        }
      }
    },
    
    getPlanTitle(planId) {
      const plan = this.plans.find(p => p.id === planId)
      return plan ? plan.title : '未知计划'
    },
    
    formatDate(timestamp) {
      if (!timestamp) return '未知'
      const date = new Date(timestamp * 1000)
      return date.toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.collaboration-manager {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
</style>