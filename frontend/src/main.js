// src/main.js
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import axios from 'axios'
import App from './App.vue'
import IntroView from './views/IntroView.vue'
import HomeView from './views/HomeView.vue'
import VideoAnalysisView from './views/VideoAnalysisView.vue'
import PdfHelperView from './views/PdfHelperView.vue'
import QaView from './views/QaView.vue'
import BrainView from './views/BrainView.vue' // [NEW]
import DashboardView from './views/DashboardView.vue' // [NEW] - Dashboard
import ComparisonView from './views/ComparisonView.vue' // [NEW] - Comparison
import LearningView from './views/LearningView.vue' // [NEW] - 学习系统
import BilingualReaderView from './views/BilingualReaderView.vue' // [NEW] - 双语对照阅读
import EncyclopediaView from './views/EncyclopediaView.vue' // [NEW] - 知识智库
import './styles/tailwind.css'

const routes = [
  { path: '/', component: IntroView, name: 'intro' },
  { path: '/dashboard', component: DashboardView, name: 'dashboard' }, // [NEW]
  { path: '/comparison', component: ComparisonView, name: 'comparison' }, // [NEW]
  { path: '/learning', component: LearningView, name: 'learning' }, // [NEW] - 学习系统
  { path: '/document-analysis', component: HomeView, name: 'document-analysis' },
  { path: '/video-analysis', component: VideoAnalysisView, name: 'video-analysis' },
  { path: '/pdf-helper', component: PdfHelperView, name: 'pdf-helper' },
  { path: '/bilingual-reader', component: BilingualReaderView, name: 'bilingual-reader' }, // [NEW] - 双语对照阅读
  { path: '/encyclopedia', component: EncyclopediaView, name: 'encyclopedia' }, // [NEW] - 知识智库
  { path: '/qa', component: QaView, name: 'qa' },
  { path: '/brain', component: BrainView, name: 'brain' } // [NEW]
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 配置axios
axios.defaults.baseURL = 'http://localhost:8000'

const app = createApp(App)
app.use(router)
app.config.globalProperties.$axios = axios
app.mount('#app')