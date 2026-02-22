<template>
  <div class="p-6 bg-gray-50 min-h-screen">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">📊 知识驾驶舱 (Knowledge Dashboard)</h1>
      <button @click="fetchData" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">
        刷新数据
      </button>
    </div>

    <!-- 核心指标卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <div 
        v-for="(item, index) in kpiCards" 
        :key="index"
        class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition"
      >
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm">{{ item.title }}</span>
          <component :is="item.icon" class="w-5 h-5 text-blue-500" />
        </div>
        <div class="text-3xl font-bold text-gray-800" :id="item.countId">
          {{ item.value }}
        </div>
        <div class="text-xs text-gray-400 mt-2">{{ item.subtitle }}</div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- 知识热力图 -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 col-span-1 lg:col-span-2">
        <h3 class="text-lg font-semibold mb-4 text-gray-700">📅 学习热力图 (Knowledge Heatmap)</h3>
        <!-- Scrollable Container -->
        <div class="w-full overflow-x-auto pb-4">
            <!-- Explicit pixel dimensions directly on v-chart to prevent collapse -->
            <v-chart class="chart" style="width: 1200px; height: 350px;" :option="heatmapOption" autoresize />
        </div>
      </div>

      <!-- 文件类型分布 -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col h-[400px]">
        <h3 class="text-lg font-semibold mb-4 text-gray-700">📂 资料类型分布</h3>
        <div class="flex-1 min-h-0">
            <v-chart class="chart w-full h-full" :option="pieOption" autoresize />
        </div>
      </div>

      <!-- 领域词云 -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col h-[400px]">
        <h3 class="text-lg font-semibold mb-4 text-gray-700">☁️ 核心知识领域</h3>
        <div class="flex-1 min-h-0">
             <v-chart class="chart w-full h-full" :option="wordCloudOption" autoresize />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { PieChart, HeatmapChart } from 'echarts/charts';
import { 
  TitleComponent, 
  TooltipComponent, 
  VisualMapComponent, 
  CalendarComponent,
  LegendComponent 
} from 'echarts/components';
import VChart from 'vue-echarts';
import 'echarts-wordcloud';
import { CountUp } from 'countup.js';
import axios from 'axios';
import { BookOpen, FileText, Activity, Clock } from 'lucide-vue-next';

// 注册 ECharts 组件
use([
  CanvasRenderer,
  PieChart,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CalendarComponent,
  LegendComponent
]);

// 状态数据
const kpiCards = ref([
  { title: "总阅读字数", value: 0, countId: "count-words", icon: BookOpen, subtitle: "累计字符输入量" },
  { title: "已归档文件", value: 0, countId: "count-files", icon: FileText, subtitle: "PDF / Video / Log" },
  { title: "活跃天数", value: 0, countId: "count-days", icon: Clock, subtitle: "有上传记录的天数" },
  { title: "知识点", value: 0, countId: "count-keywords", icon: Activity, subtitle: "提取的关键词总数" }
]);

const rawData = ref({
  heatmap: [],
  file_types: [],
  word_cloud: [],
  total_chars: 0
});

// 获取数据
const fetchData = async () => {
  try {
    // Check if we are in dev mode and need full URL, otherwise use relative
    // Usually best to use relative and rely on proxy
    const res = await axios.get('/api/dashboard/stats');
    const data = res.data;
    rawData.value = data;
    
    // 更新 KPI
    updateKpi("count-words", data.total_chars);
    updateKpi("count-files", data.file_types.reduce((sum, item) => sum + item.value, 0));
    updateKpi("count-days", data.heatmap.length);
    updateKpi("count-keywords", data.word_cloud.length);

  } catch (error) {
    console.error("Dashboard fetch error:", error);
  }
};

const updateKpi = (id, endVal) => {
  const countUp = new CountUp(id, endVal);
  if (!countUp.error) countUp.start();
};

// 1. 热力图配置
const heatmapOption = computed(() => ({
  tooltip: {
    formatter: params => `${params.value[0]}: 上传 ${params.value[1]} 个文件`
  },
  visualMap: {
    min: 0,
    max: 10,
    type: 'piecewise',
    orient: 'horizontal',
    left: 'center',
    top: 0,
    inRange: { color: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'] }
  },
  calendar: {
    top: 30,
    left: 30,
    right: 'auto',
    bottom: 0,
    orient: 'horizontal',
    cellSize: [30, 30],
    range: new Date().getFullYear(),
    itemStyle: { 
      borderWidth: 2, 
      borderColor: '#fff' 
    },
    yearLabel: { show: false }
  },
  series: {
    type: 'heatmap',
    coordinateSystem: 'calendar',
    data: rawData.value.heatmap
  }
}));

// 2. 饼图配置
const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: '0%' },
  series: [
    {
      name: '文件类型',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: {
        label: { show: true, fontSize: 20, fontWeight: 'bold' }
      },
      data: rawData.value.file_types
    }
  ]
}));

// 3. 词云配置
const wordCloudOption = computed(() => ({
  tooltip: {},
  series: [{
    type: 'wordCloud',
    gridSize: 10,
    sizeRange: [12, 30], // Smaller max font to fit long phrases
    rotationRange: [0, 0], // Force horizontal only to prevent cropping
    shape: 'circle',
    width: '95%',
    height: '95%',
    drawOutOfBound: false,
    textStyle: {
      fontFamily: 'sans-serif',
      fontWeight: 'bold',
      color: () => 'rgb(' + [
        Math.round(Math.random() * 160),
        Math.round(Math.random() * 160),
        Math.round(Math.random() * 160)
      ].join(',') + ')'
    },
    data: rawData.value.word_cloud
  }]
}));

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.chart {
  width: 100%;
}
</style>
