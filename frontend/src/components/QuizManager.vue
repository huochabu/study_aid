<template>
  <div class="quiz-manager">
    <h2 class="text-2xl font-bold mb-6">测验与练习</h2>
    
    <!-- 创建测验 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">创建新测验</h3>
      <div class="flex gap-4 mb-4">
        <button 
          @click="activeTab = 'manual'" 
          :class="[activeTab === 'manual' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700', 'px-4 py-2 rounded-md font-medium transition-colors']"
        >
          手动创建
        </button>
        <button 
          @click="activeTab = 'ai'" 
          :class="[activeTab === 'ai' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700', 'px-4 py-2 rounded-md font-medium transition-colors']"
        >
          AI生成
        </button>
      </div>
      
      <!-- 手动创建表单 -->
      <form v-if="activeTab === 'manual'" @submit.prevent="createQuiz">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">测验标题</label>
          <input 
            v-model="newQuiz.title" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">测验描述</label>
          <textarea 
            v-model="newQuiz.description" 
            rows="2" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">关联模块</label>
            <select 
              v-model="newQuiz.module_id" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">请选择模块</option>
              <option 
                v-for="module in allModules" 
                :key="module.id" 
                :value="module.id"
              >
                {{ module.title }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">时间限制（分钟）</label>
            <input 
              v-model.number="newQuiz.time_limit" 
              type="number" 
              min="1" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
        </div>
        <button 
          type="submit" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          创建测验
        </button>
      </form>
      
      <!-- AI生成表单 -->
      <form v-else @submit.prevent="generateQuizWithAI">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">测验标题</label>
          <input 
            v-model="aiQuiz.title" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">测验描述</label>
          <textarea 
            v-model="aiQuiz.description" 
            rows="2" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">关联模块</label>
            <select 
              v-model="aiQuiz.module_id" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">请选择模块</option>
              <option 
                v-for="module in allModules" 
                :key="module.id" 
                :value="module.id"
              >
                {{ module.title }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">题目数量</label>
            <input 
              v-model.number="aiQuiz.question_count" 
              type="number" 
              min="1" 
              max="20" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">时间限制（分钟）</label>
          <input 
            v-model.number="aiQuiz.time_limit" 
            type="number" 
            min="1" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <button 
          type="submit" 
          class="bg-purple-500 hover:bg-purple-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          :disabled="isGenerating"
        >
          <span v-if="!isGenerating">AI生成测验</span>
          <span v-else>生成中...</span>
        </button>
      </form>
    </div>
    
    <!-- 测验列表 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <h3 class="text-lg font-semibold mb-4">测验列表</h3>
      <div v-if="quizzes.length === 0" class="text-center py-8 text-gray-500">
        暂无测验，点击上方按钮创建
      </div>
      <div v-else class="space-y-4">
        <div 
          v-for="quiz in quizzes" 
          :key="quiz.id" 
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <h4 class="text-lg font-medium">{{ quiz.title }}</h4>
            <span class="text-sm text-gray-500">{{ quiz.time_limit }}分钟</span>
          </div>
          <p class="text-gray-600 text-sm mb-3">{{ quiz.description }}</p>
          <div class="flex flex-wrap gap-2 text-xs text-gray-500 mb-3">
            <span>模块: {{ getModuleTitle(quiz.module_id) }}</span>
          </div>
          
          <!-- 操作按钮 -->
          <div class="flex gap-2">
            <button 
              @click="viewQuizDetail(quiz)" 
              class="bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              查看详情
            </button>
            <button 
              @click="addQuestion(quiz)" 
              class="bg-green-500 hover:bg-green-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              添加问题
            </button>
            <button 
              @click="takeQuiz(quiz)" 
              class="bg-purple-500 hover:bg-purple-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              开始测验
            </button>
            <button 
              @click="deleteQuiz(quiz.id)" 
              class="bg-red-500 hover:bg-red-600 text-white text-sm font-medium py-1 px-3 rounded-md transition-colors"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 测验详情弹窗 -->
    <div v-if="showQuizDetail" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">{{ selectedQuiz.title }} - 详情</h3>
          <button @click="showQuizDetail = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div class="mb-6">
          <p class="text-gray-600 mb-3">{{ selectedQuiz.description }}</p>
          <div class="flex flex-wrap gap-4 text-sm text-gray-500">
            <span>时间限制: {{ selectedQuiz.time_limit }}分钟</span>
            <span>模块: {{ getModuleTitle(selectedQuiz.module_id) }}</span>
            <span>问题数量: {{ quizQuestions.length }}</span>
          </div>
        </div>
        
        <!-- 问题列表 -->
        <div class="mb-6">
          <h4 class="text-lg font-medium mb-3">问题列表</h4>
          <div v-if="quizQuestions.length === 0" class="text-center py-4 text-gray-500">
            暂无问题
          </div>
          <div v-else class="space-y-4">
            <div 
              v-for="(question, index) in quizQuestions" 
              :key="question.id" 
              class="border border-gray-200 rounded-lg p-3"
            >
              <div class="flex justify-between items-center mb-2">
                <h5 class="font-medium">{{ index + 1 }}. {{ question.content }}</h5>
                <span class="text-sm text-gray-500">{{ question.points }}分</span>
              </div>
              <div class="text-sm text-gray-600 mb-2">
                类型: {{ question.question_type === 'multiple_choice' ? '选择题' : question.question_type === 'true_false' ? '判断题' : '简答题' }}
              </div>
              <div v-if="question.options && question.options.length > 0" class="ml-4 space-y-1 mb-2">
                <div 
                  v-for="(option, optIndex) in question.options" 
                  :key="optIndex" 
                  class="flex items-center"
                >
                  <input 
                    type="radio" 
                    :name="`q${question.id}`" 
                    :value="option" 
                    disabled 
                    class="mr-2"
                  >
                  <label>{{ option }}</label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 添加问题弹窗 -->
    <div v-if="showAddQuestion" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">添加问题</h3>
          <button @click="showAddQuestion = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <form @submit.prevent="saveQuestion">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">问题内容</label>
            <textarea 
              v-model="newQuestion.content" 
              rows="2" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            ></textarea>
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">问题类型</label>
            <select 
              v-model="newQuestion.question_type" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="multiple_choice">选择题</option>
              <option value="true_false">判断题</option>
              <option value="short_answer">简答题</option>
            </select>
          </div>
          <div v-if="newQuestion.question_type === 'multiple_choice'" class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">选项（每行一个）</label>
            <textarea 
              v-model="newQuestion.optionsInput" 
              rows="4" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="选项A\n选项B\n选项C\n选项D"
              required
            ></textarea>
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">正确答案</label>
            <input 
              v-model="newQuestion.correct_answer" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">分值</label>
            <input 
              v-model.number="newQuestion.points" 
              type="number" 
              min="1" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
          <div class="flex gap-2">
            <button 
              type="submit" 
              class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              保存问题
            </button>
            <button 
              type="button" 
              @click="showAddQuestion = false" 
              class="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- 参加测验弹窗 -->
    <div v-if="showTakeQuiz" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">{{ takingQuiz.title }} - 测验</h3>
          <button @click="confirmExitQuiz" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div class="mb-6">
          <p class="text-gray-600 mb-3">{{ takingQuiz.description }}</p>
          <div class="flex flex-wrap gap-4 text-sm text-gray-500 mb-3">
            <span>时间限制: {{ takingQuiz.time_limit }}分钟</span>
            <span>问题数量: {{ quizQuestions.length }}</span>
            <span>总分: {{ totalPoints }}分</span>
          </div>
        </div>
        
        <form @submit.prevent="submitQuiz">
          <div class="space-y-4 mb-6">
            <div 
              v-for="(question, index) in quizQuestions" 
              :key="question.id" 
              class="border border-gray-200 rounded-lg p-3"
            >
              <h5 class="font-medium mb-2">{{ index + 1 }}. {{ question.content }}</h5>
              <div v-if="question.question_type === 'multiple_choice'" class="ml-4 space-y-2">
                <div 
                  v-for="(option, optIndex) in question.options" 
                  :key="optIndex" 
                  class="flex items-center"
                >
                  <input 
                    type="radio" 
                    :name="`q${question.id}`" 
                    :value="option" 
                    v-model="userAnswers[question.id]" 
                    class="mr-2"
                  >
                  <label>{{ option }}</label>
                </div>
              </div>
              <div v-else-if="question.question_type === 'true_false'" class="ml-4 space-y-2">
                <div class="flex items-center">
                  <input 
                    type="radio" 
                    :name="`q${question.id}`" 
                    value="True" 
                    v-model="userAnswers[question.id]" 
                    class="mr-2"
                  >
                  <label>正确</label>
                </div>
                <div class="flex items-center">
                  <input 
                    type="radio" 
                    :name="`q${question.id}`" 
                    value="False" 
                    v-model="userAnswers[question.id]" 
                    class="mr-2"
                  >
                  <label>错误</label>
                </div>
              </div>
              <div v-else class="ml-4">
                <textarea 
                  :name="`q${question.id}`" 
                  v-model="userAnswers[question.id]" 
                  rows="2" 
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="请输入答案"
                ></textarea>
              </div>
            </div>
          </div>
          <button 
            type="submit" 
            class="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            提交测验
          </button>
        </form>
      </div>
    </div>
    
    <!-- 测验结果弹窗 -->
    <div v-if="showQuizResult" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">测验结果</h3>
          <button @click="showQuizResult = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div class="text-center mb-6">
          <div class="text-4xl font-bold mb-2">{{ quizResult.score }}/{{ quizResult.total_points }}</div>
          <div class="text-2xl font-medium text-blue-500 mb-2">{{ quizResult.percentage }}%</div>
          <div :class="[
            'text-lg font-medium',
            quizResult.percentage >= 60 ? 'text-green-500' : 'text-red-500'
          ]">
            {{ quizResult.percentage >= 60 ? '恭喜通过！' : '未通过，继续努力！' }}
          </div>
        </div>
        
        <div class="mb-6">
          <h4 class="text-lg font-medium mb-3">答题情况</h4>
          <div class="space-y-2">
            <div 
              v-for="(question, index) in quizQuestions" 
              :key="question.id" 
              class="border border-gray-200 rounded-lg p-3"
            >
              <div class="flex justify-between items-center mb-1">
                <h5 class="font-medium">{{ index + 1 }}. {{ question.content }}</h5>
                <span :class="[
                  'px-2 py-0.5 text-xs rounded-full font-medium',
                  userAnswers[question.id] === question.correct_answer ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                ]">
                  {{ userAnswers[question.id] === question.correct_answer ? '正确' : '错误' }}
                </span>
              </div>
              <div class="text-sm">
                <div class="text-gray-600">你的答案: {{ userAnswers[question.id] || '未回答' }}</div>
                <div class="text-green-600">正确答案: {{ question.correct_answer }}</div>
              </div>
            </div>
          </div>
        </div>
        
        <button 
          @click="showQuizResult = false" 
          class="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'QuizManager',
  data() {
    return {
      quizzes: [],
      allModules: [],
      activeTab: 'manual',
      newQuiz: {
        title: '',
        description: '',
        module_id: '',
        time_limit: 30
      },
      aiQuiz: {
        title: '',
        description: '',
        module_id: '',
        question_count: 5,
        time_limit: 30
      },
      isGenerating: false,
      newQuestion: {
        content: '',
        question_type: 'multiple_choice',
        optionsInput: '',
        correct_answer: '',
        points: 10
      },
      selectedQuiz: null,
      takingQuiz: null,
      quizQuestions: [],
      userAnswers: {},
      quizResult: null,
      showQuizDetail: false,
      showAddQuestion: false,
      showTakeQuiz: false,
      showQuizResult: false
    }
  },
  computed: {
    totalPoints() {
      return this.quizQuestions.reduce((sum, q) => sum + q.points, 0)
    }
  },
  mounted() {
    this.fetchQuizzes()
    this.fetchAllModules()
  },
  methods: {
    async fetchQuizzes() {
      try {
        const response = await fetch('/api/learning/quizzes')
        if (response.ok) {
          this.quizzes = await response.json()
        }
      } catch (error) {
        console.error('获取测验失败:', error)
      }
    },
    
    async fetchAllModules() {
      try {
        // 先获取所有学习计划
        const plansResponse = await fetch('/api/learning/plans')
        if (plansResponse.ok) {
          const plans = await plansResponse.json()
          // 收集所有模块
          const modulesPromises = plans.map(plan => 
            fetch(`/api/learning/modules/${plan.id}`)
              .then(res => res.json())
              .catch(() => [])
          )
          const modulesArrays = await Promise.all(modulesPromises)
          this.allModules = modulesArrays.flat()
        }
      } catch (error) {
        console.error('获取模块失败:', error)
      }
    },
    
    async createQuiz() {
      try {
        console.log('创建测验请求数据:', {
          module_id: this.newQuiz.module_id,
          title: this.newQuiz.title,
          description: this.newQuiz.description,
          time_limit: this.newQuiz.time_limit
        });
        
        const response = await fetch('/api/learning/quizzes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            module_id: this.newQuiz.module_id,
            title: this.newQuiz.title,
            description: this.newQuiz.description,
            time_limit: this.newQuiz.time_limit
          })
        });
        
        console.log('创建测验响应状态:', response.status);
        
        if (response.ok) {
          const result = await response.json();
          console.log('创建测验成功:', result);
          await this.fetchQuizzes();
          this.newQuiz = {
            title: '',
            description: '',
            module_id: '',
            time_limit: 30
          };
        } else {
          const errorData = await response.json();
          console.error('创建测验失败:', errorData);
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
          alert('创建测验失败: ' + errorMessage);
        }
      } catch (error) {
        console.error('创建测验失败:', error);
        alert('创建测验失败: ' + error.message);
      }
    },
    
    async viewQuizDetail(quiz) {
      this.selectedQuiz = quiz
      this.showQuizDetail = true
      await this.fetchQuizQuestions(quiz.id)
    },
    
    async fetchQuizQuestions(quizId) {
      try {
        const response = await fetch(`/api/learning/quizzes/${quizId}`)
        if (response.ok) {
          const quizData = await response.json()
          this.quizQuestions = quizData.questions || []
          console.log('获取的问题数据:', this.quizQuestions)
        }
      } catch (error) {
        console.error('获取问题失败:', error)
      }
    },
    
    addQuestion(quiz) {
      this.selectedQuiz = quiz
      this.showAddQuestion = true
      this.newQuestion = {
        content: '',
        question_type: 'multiple_choice',
        optionsInput: '',
        correct_answer: '',
        points: 10
      }
    },
    
    async saveQuestion() {
      try {
        // 处理选项
        const options = this.newQuestion.question_type === 'multiple_choice' && this.newQuestion.optionsInput
          ? this.newQuestion.optionsInput.split('\n').map(option => option.trim()).filter(option => option)
          : []
        
        const response = await fetch(`/api/learning/quizzes/${this.selectedQuiz.id}/questions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            content: this.newQuestion.content,
            question_type: this.newQuestion.question_type,
            options: JSON.stringify(options),
            correct_answer: this.newQuestion.correct_answer,
            points: this.newQuestion.points
          })
        })
        
        if (response.ok) {
          await this.fetchQuizQuestions(this.selectedQuiz.id)
          this.showAddQuestion = false
        }
      } catch (error) {
        console.error('添加问题失败:', error)
      }
    },
    
    async takeQuiz(quiz) {
      this.takingQuiz = quiz
      this.showTakeQuiz = true
      this.userAnswers = {}
      await this.fetchQuizQuestions(quiz.id)
    },
    
    async submitQuiz() {
      try {
        const response = await fetch(`/api/learning/quizzes/${this.takingQuiz.id}/attempt`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            answers: JSON.stringify(this.userAnswers)
          })
        })
        
        if (response.ok) {
          this.quizResult = await response.json()
          this.showTakeQuiz = false
          this.showQuizResult = true
        }
      } catch (error) {
        console.error('提交测验失败:', error)
      }
    },
    
    confirmExitQuiz() {
      if (confirm('确定要退出测验吗？你的答案将不会被保存。')) {
        this.showTakeQuiz = false
      }
    },
    
    async deleteQuiz(quizId) {
      if (confirm('确定要删除这个测验吗？相关的问题也会被删除。')) {
        try {
          const response = await fetch(`/api/learning/quizzes/${quizId}`, {
            method: 'DELETE'
          })
          if (response.ok) {
            await this.fetchQuizzes()
          }
        } catch (error) {
          console.error('删除测验失败:', error)
        }
      }
    },
    
    async generateQuizWithAI() {
      try {
        this.isGenerating = true
        
        const response = await fetch('/api/learning/quizzes/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            module_id: this.aiQuiz.module_id,
            title: this.aiQuiz.title,
            description: this.aiQuiz.description,
            question_count: this.aiQuiz.question_count,
            time_limit: this.aiQuiz.time_limit
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          console.log('AI生成测验成功:', result)
          await this.fetchQuizzes()
          // 重置表单
          this.aiQuiz = {
            title: '',
            description: '',
            module_id: '',
            question_count: 5,
            time_limit: 30
          }
          alert('AI生成测验成功！')
        } else {
          const errorData = await response.json()
          console.error('AI生成测验失败:', errorData)
          let errorMessage = '未知错误'
          if (errorData.detail) {
            errorMessage = errorData.detail
          }
          alert('AI生成测验失败: ' + errorMessage)
        }
      } catch (error) {
        console.error('AI生成测验失败:', error)
        alert('AI生成测验失败: ' + error.message)
      } finally {
        this.isGenerating = false
      }
    },
    
    getModuleTitle(moduleId) {
      const module = this.allModules.find(m => m.id === moduleId)
      return module ? module.title : '未知模块'
    }
  }
}
</script>

<style scoped>
.quiz-manager {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
</style>