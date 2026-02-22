<template>
  <div class="learning-plan-manager">
    <h2 class="text-2xl font-bold mb-6">学习计划管理</h2>
    
    <!-- 创建学习计划 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">创建新学习计划</h3>
      <form @submit.prevent="createPlan">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">计划标题</label>
            <input 
              v-model="newPlan.title" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <input 
              v-model="newPlan.description" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
            <input 
              v-model="newPlan.startDate" 
              type="date" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
            <input 
              v-model="newPlan.endDate" 
              type="date" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
        </div>
        <button 
          type="submit" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          创建计划
        </button>
      </form>
    </div>
    
    <!-- 学习计划列表 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">我的学习计划</h3>
      <div v-if="plans.length === 0" class="text-center py-8 text-gray-500">
        暂无学习计划，点击上方按钮创建
      </div>
      <div v-else class="space-y-4">
        <div 
          v-for="plan in plans" 
          :key="plan.id" 
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <h4 class="text-lg font-medium">{{ plan.title }}</h4>
            <span 
              :class="[
                'px-2 py-1 text-xs rounded-full font-medium',
                plan.status === 'active' ? 'bg-green-100 text-green-800' :
                plan.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              ]"
            >
              {{ plan.status === 'active' ? '进行中' : plan.status === 'completed' ? '已完成' : '暂停' }}
            </span>
          </div>
          <p class="text-gray-600 text-sm mb-3">{{ plan.description }}</p>
          <div class="flex flex-wrap gap-4 mb-3 text-sm text-gray-500">
            <span>开始: {{ formatDate(plan.start_date) }}</span>
            <span>结束: {{ formatDate(plan.end_date) }}</span>
            <span>计划ID: {{ plan.id }}</span>
          </div>
          
          <!-- 学习进度 -->
          <div v-if="progressData[plan.id]" class="mb-3">
            <div class="flex justify-between text-sm mb-1">
              <span>学习进度</span>
              <span>{{ progressData[plan.id].overall_progress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div 
                class="bg-blue-500 h-2 rounded-full transition-all duration-500"
                :style="{ width: progressData[plan.id].overall_progress + '%' }"
              ></div>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="flex gap-2 mt-3">
            <button 
              @click="viewPlanDetail(plan)" 
              class="bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              查看详情
            </button>
            <button 
              @click="editPlan(plan)" 
              class="bg-gray-500 hover:bg-gray-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              编辑
            </button>
            <button 
              @click="deletePlan(plan.id)" 
              class="bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 计划详情弹窗 -->
    <div v-if="showPlanDetail" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">{{ selectedPlan.title }} - 详情</h3>
          <button @click="showPlanDetail = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <!-- 学习模块 -->
        <div class="mb-6">
          <h4 class="text-lg font-medium mb-3">学习模块</h4>
          <div v-if="selectedPlanModules.length === 0" class="text-center py-4 text-gray-500">
            暂无学习模块
          </div>
          <div v-else class="space-y-3">
            <div 
              v-for="module in selectedPlanModules" 
              :key="module.id" 
              class="border border-gray-200 rounded-lg p-3"
            >
              <div class="flex justify-between items-center mb-2">
                <h5 class="font-medium">{{ module.title }}</h5>
                <span class="text-sm text-gray-500">{{ module.estimated_time }}分钟</span>
              </div>
              <p class="text-sm text-gray-600 mb-2">{{ module.description }}</p>
              
              <!-- 模块进度 -->
              <div v-if="progressData[selectedPlan.id]" class="mb-2">
                <div class="flex justify-between text-xs mb-1">
                  <span>进度</span>
                  <span>{{ getModuleProgress(module.id) }}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                  <div 
                    class="bg-green-500 h-1.5 rounded-full"
                    :style="{ width: getModuleProgress(module.id) + '%' }"
                  ></div>
                </div>
                <div class="flex items-center gap-2 mb-2">
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    step="10" 
                    :value="getModuleProgress(module.id)"
                    @change="updateModuleProgress(module.id, selectedPlan.id, parseInt($event.target.value))"
                    class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  >
                  <input 
                    type="number" 
                    min="0" 
                    max="100" 
                    :value="getModuleProgress(module.id)"
                    @change="updateModuleProgress(module.id, selectedPlan.id, parseInt($event.target.value))"
                    class="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm"
                  >
                  <span class="text-sm">%</span>
                </div>
              </div>
              
              <div class="flex gap-2 mt-2">
                <button 
                  @click="updateModuleProgress(module.id, selectedPlan.id, 100)"
                  class="bg-green-500 hover:bg-green-600 text-white text-xs font-medium py-1 px-2 rounded transition-colors"
                >
                  标记完成
                </button>
                <button 
                  @click="updateModuleProgress(module.id, selectedPlan.id, 0)"
                  class="bg-gray-500 hover:bg-gray-600 text-white text-xs font-medium py-1 px-2 rounded transition-colors"
                >
                  重置
                </button>
                <button 
                  @click="addNote(module.id)"
                  class="bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium py-1 px-2 rounded transition-colors"
                >
                  添加笔记
                </button>
                <button 
                  @click="deleteModule(module.id, selectedPlan.id)"
                  class="bg-red-500 hover:bg-red-600 text-white text-xs font-medium py-1 px-2 rounded transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 添加模块 -->
        <div class="mt-6">
          <h4 class="text-lg font-medium mb-3">添加学习模块</h4>
          <form @submit.prevent="addModule">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">模块标题</label>
                <input 
                  v-model="newModule.title" 
                  type="text" 
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  required
                >
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">预计时间（分钟）</label>
                <input 
                  v-model.number="newModule.estimated_time" 
                  type="number" 
                  min="1" 
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  required
                >
              </div>
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-gray-700 mb-1">模块描述</label>
              <input 
                v-model="newModule.description" 
                type="text" 
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">排序索引</label>
              <input 
                v-model.number="newModule.order_index" 
                type="number" 
                min="0" 
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                required
              >
            </div>
            <button 
              type="submit" 
              class="mt-3 bg-green-500 hover:bg-green-600 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
            >
              添加模块
            </button>
          </form>
        </div>
      </div>
    </div>
    
    <!-- 编辑计划弹窗 -->
    <div v-if="showEditDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">编辑学习计划</h3>
          <button @click="cancelEdit" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">计划标题</label>
          <input 
            v-model="editTitle" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <div class="flex justify-end gap-2">
          <button 
            @click="cancelEdit" 
            class="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            取消
          </button>
          <button 
            @click="saveEdit" 
            class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            保存
          </button>
        </div>
      </div>
    </div>
    
    <!-- 添加笔记弹窗 -->
    <div v-if="showAddNoteDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">添加笔记</h3>
          <button @click="cancelAddNote" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">笔记标题</label>
          <input 
            v-model="newNote.title" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">笔记内容</label>
          <textarea 
            v-model="newNote.content" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
            required
          ></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button 
            @click="cancelAddNote" 
            class="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            取消
          </button>
          <button 
            @click="saveAddNote" 
            class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            保存笔记
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LearningPlanManager',
  data() {
    return {
      plans: [],
      progressData: {},
      newPlan: {
        title: '',
        description: '',
        startDate: '',
        endDate: ''
      },
      newModule: {
        title: '',
        description: '',
        order_index: 0,
        estimated_time: 30
      },
      showPlanDetail: false,
      selectedPlan: null,
      selectedPlanModules: [],
      showEditDialog: false,
      editingPlan: null,
      editTitle: '',
      showAddNoteDialog: false,
      currentModuleId: null,
      newNote: {
        title: '',
        content: ''
      }
    }
  },
  mounted() {
    this.fetchPlans()
  },
  methods: {
    async fetchPlans() {
      try {
        const response = await fetch('/api/learning/plans')
        if (response.ok) {
          this.plans = await response.json()
          for (const plan of this.plans) {
            await this.fetchPlanProgress(plan.id)
          }
        }
      } catch (error) {
        console.error('获取学习计划失败:', error)
      }
    },
    
    async fetchPlanProgress(planId) {
      try {
        const response = await fetch(`/api/learning/progress/${planId}`)
        if (response.ok) {
          const progress = await response.json()
          this.progressData[planId] = progress
        }
      } catch (error) {
        console.error('获取学习进度失败:', error)
      }
    },
    
    async createPlan() {
      try {
        if (!this.newPlan.title || !this.newPlan.startDate || !this.newPlan.endDate) {
          console.error('表单数据不完整');
          return;
        }
        
        const startDate = new Date(this.newPlan.startDate).getTime() / 1000;
        const endDate = new Date(this.newPlan.endDate).getTime() / 1000;
        
        if (isNaN(startDate) || isNaN(endDate)) {
          console.error('日期转换失败');
          return;
        }
        
        console.log('发送请求:', {
          title: this.newPlan.title,
          description: this.newPlan.description,
          start_date: startDate,
          end_date: endDate
        });
        
        const response = await fetch('/api/learning/plans', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            title: this.newPlan.title,
            description: this.newPlan.description,
            start_date: startDate,
            end_date: endDate
          })
        });
        
        console.log('响应状态:', response.status);
        if (response.ok) {
          const result = await response.json();
          console.log('创建成功:', result);
          await this.fetchPlans();
          this.newPlan = {
            title: '',
            description: '',
            startDate: '',
            endDate: ''
          };
        } else {
          const errorData = await response.json();
          console.error('创建失败:', errorData);
          let errorMessage = '未知错误';
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map(e => e.msg || e.loc || JSON.stringify(e)).join(', ');
            } else if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail;
            } else {
              errorMessage = JSON.stringify(errorData.detail);
            }
          }
          alert('创建失败: ' + errorMessage);
        }
      } catch (error) {
        console.error('创建学习计划失败:', error);
        alert('创建学习计划失败: ' + error.message);
      }
    },
    
    async viewPlanDetail(plan) {
      this.selectedPlan = plan
      this.showPlanDetail = true
      await this.fetchPlanModules(plan.id)
      await this.fetchPlanProgress(plan.id)
    },
    
    async fetchPlanModules(planId) {
      try {
        const response = await fetch(`/api/learning/modules/${planId}`)
        if (response.ok) {
          this.selectedPlanModules = await response.json()
        }
      } catch (error) {
        console.error('获取学习模块失败:', error)
      }
    },
    
    async addModule() {
      try {
        if (!this.selectedPlan || !this.selectedPlan.id) {
          console.error('未选择有效的学习计划');
          return;
        }
        
        console.log('添加模块请求数据:', {
          plan_id: this.selectedPlan.id,
          title: this.newModule.title,
          description: this.newModule.description,
          order_index: this.newModule.order_index,
          estimated_time: this.newModule.estimated_time
        });
        
        const response = await fetch('/api/learning/modules', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            plan_id: this.selectedPlan.id,
            title: this.newModule.title,
            description: this.newModule.description,
            order_index: this.newModule.order_index,
            estimated_time: this.newModule.estimated_time
          })
        });
        
        console.log('添加模块响应状态:', response.status);
        
        if (response.ok) {
          const result = await response.json();
          console.log('添加模块成功:', result);
          await this.fetchPlanModules(this.selectedPlan.id);
          this.newModule = {
            title: '',
            description: '',
            order_index: 0,
            estimated_time: 30
          };
        } else {
          const errorData = await response.json();
          console.error('添加模块失败:', errorData);
          let errorMessage = '未知错误';
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map(e => e.msg || e.loc || JSON.stringify(e)).join(', ');
            } else if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail;
            } else {
              errorMessage = JSON.stringify(errorData.detail);
            }
          }
          alert('添加模块失败: ' + errorMessage);
        }
      } catch (error) {
        console.error('添加学习模块失败:', error);
        alert('添加学习模块失败: ' + error.message);
      }
    },
    
    async updateModuleProgress(moduleId, planId, progress) {
      try {
        console.log('更新进度请求数据:', {
          module_id: moduleId,
          plan_id: planId,
          progress: progress
        })
        
        const response = await fetch('/api/learning/progress', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            module_id: moduleId,
            plan_id: planId,
            progress: progress
          })
        })
        
        console.log('更新进度响应状态:', response.status)
        
        if (response.ok) {
          const result = await response.json()
          console.log('更新进度成功:', result)
          await this.fetchPlanProgress(planId)
          
          // 记录学习活动
          await this.logLearningActivity(moduleId, 'study', 60) // 假设学习了1分钟
        } else {
          const errorData = await response.json()
          console.error('更新进度失败:', errorData)
          let errorMessage = '未知错误'
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map(e => e.msg || e.loc || JSON.stringify(e)).join(', ')
            } else if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail
            } else {
              errorMessage = JSON.stringify(errorData.detail)
            }
          }
          alert('更新进度失败: ' + errorMessage)
        }
      } catch (error) {
        console.error('更新学习进度失败:', error)
        alert('更新学习进度失败: ' + error.message)
      }
    },
    
    async logLearningActivity(moduleId, activityType, duration) {
      try {
        const response = await fetch('/api/learning/analytics', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            user_id: 'default',
            module_id: moduleId,
            activity_type: activityType,
            duration: duration,
            metadata: ''
          })
        })
        
        console.log('学习活动记录响应状态:', response.status)
        
        if (response.ok) {
          console.log('学习活动记录成功')
        } else {
          const errorData = await response.json()
          console.error('学习活动记录失败:', errorData)
        }
      } catch (error) {
        console.error('记录学习活动失败:', error)
      }
    },
    
    async deletePlan(planId) {
      if (confirm('确定要删除这个学习计划吗？')) {
        try {
          const response = await fetch(`/api/learning/plans/${planId}`, {
            method: 'DELETE'
          })
          if (response.ok) {
            await this.fetchPlans()
          }
        } catch (error) {
          console.error('删除学习计划失败:', error)
        }
      }
    },
    
    editPlan(plan) {
      this.editingPlan = plan
      this.editTitle = plan.title
      this.showEditDialog = true
    },
    
    cancelEdit() {
      this.showEditDialog = false
      this.editingPlan = null
      this.editTitle = ''
    },
    
    saveEdit() {
      if (this.editTitle && this.editingPlan) {
        this.updatePlan(this.editingPlan.id, { title: this.editTitle })
        this.cancelEdit()
      }
    },
    
    async updatePlan(planId, updates) {
      try {
        const response = await fetch(`/api/learning/plans/${planId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams(updates)
        })
        if (response.ok) {
          await this.fetchPlans()
        }
      } catch (error) {
        console.error('更新学习计划失败:', error)
      }
    },
    
    addNote(moduleId) {
      this.currentModuleId = moduleId
      this.showAddNoteDialog = true
    },
    
    cancelAddNote() {
      this.showAddNoteDialog = false
      this.currentModuleId = null
      this.newNote = {
        title: '',
        content: ''
      }
    },
    
    async saveAddNote() {
      if (!this.currentModuleId) return
      
      try {
        console.log('添加笔记请求数据:', {
          title: this.newNote.title,
          content: this.newNote.content,
          module_id: this.currentModuleId
        })
        
        const response = await fetch('/api/learning/notes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            title: this.newNote.title,
            content: this.newNote.content,
            module_id: this.currentModuleId
          })
        })
        
        console.log('添加笔记响应状态:', response.status)
        
        if (response.ok) {
          const result = await response.json()
          console.log('添加笔记成功:', result)
          this.cancelAddNote()
          alert('笔记添加成功')
        } else {
          const errorData = await response.json()
          console.error('添加笔记失败:', errorData)
          let errorMessage = '未知错误'
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map(e => e.msg || e.loc || JSON.stringify(e)).join(', ')
            } else if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail
            } else {
              errorMessage = JSON.stringify(errorData.detail)
            }
          }
          alert('添加笔记失败: ' + errorMessage)
        }
      } catch (error) {
        console.error('添加笔记失败:', error)
        alert('添加笔记失败: ' + error.message)
      }
    },
    
    async deleteModule(moduleId, planId) {
      if (confirm('确定要删除这个学习模块吗？')) {
        try {
          const response = await fetch(`/api/learning/modules/${moduleId}`, {
            method: 'DELETE'
          })
          if (response.ok) {
            await this.fetchPlanModules(planId)
            await this.fetchPlanProgress(planId)
          }
        } catch (error) {
          console.error('删除学习模块失败:', error)
        }
      }
    },
    
    getModuleProgress(moduleId) {
      if (!this.selectedPlan || !this.progressData[this.selectedPlan.id]) {
        return 0
      }
      const moduleProgress = this.progressData[this.selectedPlan.id].module_progress.find(
        mp => mp.module_id === moduleId
      )
      return moduleProgress ? moduleProgress.progress : 0
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
.learning-plan-manager {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
</style>