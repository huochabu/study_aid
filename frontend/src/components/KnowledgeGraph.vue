<template>
  <div class="kg-container" ref="networkContainer"></div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const props = defineProps({
  data: {
    type: Object,
    default: () => ({ nodes: [], edges: [] })
  }
})

const networkContainer = ref(null)
let network = null

// 转换数据（节点+关系）
const transformData = (rawData) => {
  // 1. 处理节点（保留原有逻辑）
  const nodes = Array.isArray(rawData.nodes) 
    ? rawData.nodes.map(node => ({
        id: node.id,
        label: node.label || '未知节点',
        group: node.type?.toLowerCase() || 'default',
        font: { size: 14, face: 'Microsoft YaHei' }
      }))
    : []

  // 2. 处理后端关系（edges）
  const edges = Array.isArray(rawData.edges)
    ? rawData.edges.map(edge => ({
        from: edge.source, // 后端关系的source对应节点id
        to: edge.target,   // 后端关系的target对应节点id
        label: edge.label || '关联', // 后端关系的标签
        font: { size: 12, face: 'Microsoft YaHei' }, // 移除无效的padding
        arrows: 'to' // 箭头指向target节点
      }))
    : []

  return { nodes, edges }
}

const initNetwork = () => {
  if (!networkContainer.value) return
  if (network) network.destroy()

  try {
    const { nodes: transformedNodes, edges: transformedEdges } = transformData(props.data)
    
    if (transformedNodes.length === 0) {
      networkContainer.value.innerHTML = `
        <div style="display:flex;justify-content:center;align-items:center;height:100%;color:#64748b;">
          暂无节点数据
        </div>
      `
      return
    }

    const nodes = new DataSet(transformedNodes)
    const edges = new DataSet(transformedEdges)

    // 节点颜色（保留原有配置）
    const colorMap = {
      category: { background: '#eff6ff', border: '#2563eb' },
      error: { background: '#fef2f2', border: '#ef4444' },
      solution: { background: '#ecfdf5', border: '#10b981' },
      rootcause: { background: '#fffbeb', border: '#f59e0b' },
      info: { background: '#f5f3ff', border: '#8b5cf6' },
      default: { background: '#fff', border: '#2563eb' }
    }
    nodes.forEach(node => {
      const color = colorMap[node.group] || colorMap.default
      nodes.update({ id: node.id, color })
    })

    // 图谱配置（移除edges.font中的padding参数）
    const options = {
      nodes: {
        shape: 'box',
        size: 30,
        font: { size: 14 },
        borderWidth: 2,
        shadow: true,
        margin: 15
      },
      edges: {
        color: '#94a3b8', // 连线颜色
        width: 2,         // 连线宽度
        smooth: { type: 'cubicBezier' }, // 平滑曲线
        font: { 
          size: 12, 
          face: 'Microsoft YaHei',
          color: '#333'
          // 移除padding，改用全局样式处理
        },
        arrows: { 
          to: { enabled: true, scaleFactor: 1.2 } // 箭头放大
        }
      },
      interaction: {
        dragNodes: true,
        dragView: true,
        zoomView: true,
        hover: true,
        tooltipDelay: 100
      },
      layout: {
        hierarchical: { enabled: false }
      },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -8000,
          centralGravity: 0.3,
          springLength: 200,
          springConstant: 0.04,
          damping: 0.09
        }
      },
      manipulation: { enabled: false }
    }

    network = new Network(networkContainer.value, { nodes, edges }, options)
    network.setSize('100%', '100%')
    network.fit()

    // 全局样式处理关系标签背景（替代padding）
    if (!document.querySelector('#kg-edge-label-style')) {
      const style = document.createElement('style')
      style.id = 'kg-edge-label-style'
      style.textContent = `
        .vis-network .vis-edge-label {
          background: rgba(255,255,255,0.8) !important;
          padding: 2px 6px !important;
          border-radius: 4px !important;
          border: 1px solid #e5e7eb !important;
        }
      `
      document.head.appendChild(style)
    }

  } catch (error) {
    console.error("知识图谱错误：", error)
    networkContainer.value.innerHTML = `
      <div style="display:flex;justify-content:center;align-items:center;height:100%;color:#ef4444;">
        加载失败：${error.message}
      </div>
    `
  }
}

// 尺寸监听
const resizeObserver = ref(null)
const observeResize = () => {
  if (!networkContainer.value) return
  resizeObserver.value = new ResizeObserver(() => {
    if (network) {
      network.setSize('100%', '100%')
      network.fit()
    }
  })
  resizeObserver.value.observe(networkContainer.value)
}

onMounted(() => {
  initNetwork()
  observeResize()
})

onUnmounted(() => {
  if (network) network.destroy()
  if (resizeObserver.value) resizeObserver.value.disconnect()
})

watch(() => props.data, initNetwork, { deep: true, immediate: true })
</script>

<style scoped>
.kg-container {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  background: #f9fafb;
  border-radius: 8px;
  overflow: hidden;
}
</style>