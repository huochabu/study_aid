<script setup>
import { ref } from 'vue'
import LearningPlanManager from '@/components/LearningPlanManager.vue'
import NoteManager from '@/components/NoteManager.vue'
import QuizManager from '@/components/QuizManager.vue'
import LearningAnalytics from '@/components/LearningAnalytics.vue'
import CollaborationManager from '@/components/CollaborationManager.vue'
import PersonalizedLearning from '@/components/PersonalizedLearning.vue'
import AdvancedAnalytics from '@/components/AdvancedAnalytics.vue'

// 当前激活的标签
const activeTab = ref('plans')
</script>

<template>
  <div class="min-h-screen bg-zinc-50 p-6">
    <div class="max-w-6xl mx-auto space-y-6">
      <!-- 页面标题 -->
      <div>
        <h1 class="text-3xl font-bold text-zinc-900">学习系统</h1>
        <p class="text-zinc-500 mt-1">管理学习计划、跟踪进度、记录笔记、参加测验</p>
      </div>
      
      <!-- 标签页导航 -->
      <div class="bg-white rounded-lg shadow-sm border border-zinc-200">
        <div class="flex flex-wrap border-b border-zinc-200">
          <button 
            @click="activeTab = 'plans'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'plans' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            学习计划
            <div 
              v-if="activeTab === 'plans'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'notes'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'notes' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            笔记管理
            <div 
              v-if="activeTab === 'notes'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'quizzes'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'quizzes' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            测验练习
            <div 
              v-if="activeTab === 'quizzes'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'analytics'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'analytics' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            学习分析
            <div 
              v-if="activeTab === 'analytics'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'collaboration'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'collaboration' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            协作学习
            <div 
              v-if="activeTab === 'collaboration'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'personalized'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'personalized' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            个性化学习
            <div 
              v-if="activeTab === 'personalized'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
          <button 
            @click="activeTab = 'advanced-analytics'" 
            :class="[
              'px-5 py-3 font-medium text-sm transition-all duration-200 whitespace-nowrap relative mx-1 my-1 rounded-t-md',
              activeTab === 'advanced-analytics' 
                ? 'text-blue-600 font-semibold bg-blue-50' 
                : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
            ]"
          >
            高级数据分析
            <div 
              v-if="activeTab === 'advanced-analytics'" 
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full"
            ></div>
          </button>
        </div>
        
        <!-- 标签页内容 -->
        <div class="p-6">
          <transition name="fade" mode="out-in">
            <div :key="activeTab" class="w-full">
              <LearningPlanManager v-if="activeTab === 'plans'" />
              <NoteManager v-else-if="activeTab === 'notes'" />
              <QuizManager v-else-if="activeTab === 'quizzes'" />
              <LearningAnalytics v-else-if="activeTab === 'analytics'" />
              <CollaborationManager v-else-if="activeTab === 'collaboration'" />
              <PersonalizedLearning v-else-if="activeTab === 'personalized'" />
              <AdvancedAnalytics v-else-if="activeTab === 'advanced-analytics'" />
            </div>
          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 组件特定样式 */

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 隐藏滚动条 */
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>