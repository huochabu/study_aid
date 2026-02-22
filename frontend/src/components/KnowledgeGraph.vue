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

const emit = defineEmits(['import-success', 'export-data', 'node-update'])

const networkContainer = ref(null)
let network = null
let nodes = null
let edges = null
let networkOptions = null // 保存网络配置选项

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

    nodes = new DataSet(transformedNodes)
    edges = new DataSet(transformedEdges)

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
    networkOptions = {
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

    network = new Network(networkContainer.value, { nodes, edges }, networkOptions)
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

    // 添加节点双击事件处理，用于编辑节点
    network.on('doubleClick', function(params) {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        editNode(nodeId)
      }
    })

  } catch (error) {
    console.error("知识图谱错误：", error)
    networkContainer.value.innerHTML = `
      <div style="display:flex;justify-content:center;align-items:center;height:100%;color:#ef4444;">
        加载失败：${error.message}
      </div>
    `
  }
}

// 编辑节点
const editNode = (nodeId) => {
  try {
    if (!nodes || !network) return
    
    const node = nodes.get(nodeId)
    if (!node) return
    
    // 保存原始label值
    const originalLabel = node.label || ''
    
    // 创建自定义输入对话框，替代prompt()
    const dialogContainer = document.createElement('div')
    dialogContainer.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
      font-family: 'Microsoft YaHei', sans-serif;
    `
    
    const dialogBox = document.createElement('div')
    dialogBox.style.cssText = `
      background: white;
      padding: 24px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      width: 400px;
      max-width: 90%;
    `
    
    const dialogTitle = document.createElement('h3')
    dialogTitle.textContent = '编辑节点标签'
    dialogTitle.style.cssText = `
      margin: 0 0 16px 0;
      font-size: 18px;
      font-weight: 600;
      color: #1f2937;
    `
    
    const input = document.createElement('input')
    input.type = 'text'
    input.value = originalLabel
    input.placeholder = '请输入新的节点标签'
    input.style.cssText = `
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 14px;
      margin-bottom: 16px;
      box-sizing: border-box;
      outline: none;
    `
    
    input.addEventListener('focus', () => {
      input.select()
    })
    
    const buttonContainer = document.createElement('div')
    buttonContainer.style.cssText = `
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    `
    
    const cancelButton = document.createElement('button')
    cancelButton.textContent = '取消'
    cancelButton.style.cssText = `
      padding: 8px 16px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      background: white;
      color: #374151;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.2s;
    `
    
    const confirmButton = document.createElement('button')
    confirmButton.textContent = '确认'
    confirmButton.style.cssText = `
      padding: 8px 16px;
      border: 1px solid #2563eb;
      border-radius: 6px;
      background: #2563eb;
      color: white;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.2s;
    `
    
    // 添加悬停效果
    cancelButton.addEventListener('mouseenter', () => {
      cancelButton.style.background = '#f3f4f6'
    })
    
    cancelButton.addEventListener('mouseleave', () => {
      cancelButton.style.background = 'white'
    })
    
    confirmButton.addEventListener('mouseenter', () => {
      confirmButton.style.background = '#1d4ed8'
    })
    
    confirmButton.addEventListener('mouseleave', () => {
      confirmButton.style.background = '#2563eb'
    })
    
    // 处理确认事件
    const handleConfirm = () => {
      const newLabel = input.value.trim()
      
      // 如果用户输入了新内容，更新节点
      if (newLabel && newLabel !== originalLabel) {
        // 更新节点数据
        nodes.update({
          id: nodeId,
          label: newLabel
        })
        
        // 通知父组件数据已更新
        emitNodeUpdate()
      }
      
      // 移除对话框
      document.body.removeChild(dialogContainer)
    }
    
    // 处理取消事件
    const handleCancel = () => {
      document.body.removeChild(dialogContainer)
    }
    
    // 添加事件监听器
    confirmButton.addEventListener('click', handleConfirm)
    cancelButton.addEventListener('click', handleCancel)
    
    // 按Enter键确认，按Esc键取消
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        handleConfirm()
      } else if (e.key === 'Escape') {
        handleCancel()
      }
    })
    
    // 构建对话框
    dialogBox.appendChild(dialogTitle)
    dialogBox.appendChild(input)
    buttonContainer.appendChild(cancelButton)
    buttonContainer.appendChild(confirmButton)
    dialogBox.appendChild(buttonContainer)
    dialogContainer.appendChild(dialogBox)
    
    // 添加到文档
    document.body.appendChild(dialogContainer)
    
    // 聚焦输入框
    input.focus()
    input.select()
    
  } catch (error) {
    console.error('Edit node error:', error)
  }
}

// 通知父组件节点更新
const emitNodeUpdate = () => {
  if (!nodes || !edges) return
  
  // 获取当前知识图谱的所有节点和边
  const allNodes = nodes.get()
  const allEdges = edges.get()
  
  // 转换回原始数据格式
  const updatedData = {
    nodes: allNodes.map(node => ({
      id: node.id,
      label: node.label,
      type: node.group ? node.group.charAt(0).toUpperCase() + node.group.slice(1) : 'Default'
    })),
    edges: allEdges.map(edge => ({
      source: edge.from,
      target: edge.to,
      label: edge.label
    }))
  }
  
  // 触发节点更新事件
  emit('node-update', updatedData)
  emit('export-data', updatedData)
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

// 导出知识图谱数据
const exportKnowledgeGraph = (format = 'json') => {
  if (format === 'json') {
    if (!nodes || !edges) return
    
    // 获取当前知识图谱的所有节点和边
    const allNodes = nodes.get()
    const allEdges = edges.get()
    
    // 转换回原始数据格式
    const exportedData = {
      nodes: allNodes.map(node => ({
        id: node.id,
        label: node.label,
        type: node.group ? node.group.charAt(0).toUpperCase() + node.group.slice(1) : 'Default'
      })),
      edges: allEdges.map(edge => ({
        source: edge.from,
        target: edge.to,
        label: edge.label
      }))
    }
    
    // 创建下载链接
    const dataStr = JSON.stringify(exportedData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `knowledge-graph-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    // 触发导出数据事件
    emit('export-data', exportedData)
  } else if (format === 'png' || format === 'jpeg') {
    // 显示导出设置对话框
    showExportSettingsDialog(format)
  }
}

// 显示导出设置对话框
const showExportSettingsDialog = (format) => {
  if (!network) {
    console.error('网络实例未准备好，无法导出图片')
    return
  }
  
  // 创建对话框容器
  const dialogContainer = document.createElement('div')
  dialogContainer.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    font-family: 'Microsoft YaHei', sans-serif;
  `
  
  const dialogBox = document.createElement('div')
  dialogBox.style.cssText = `
    background: white;
    padding: 24px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    width: 400px;
    max-width: 90%;
  `
  
  const dialogTitle = document.createElement('h3')
  dialogTitle.textContent = '导出设置'
  dialogTitle.style.cssText = `
    margin: 0 0 20px 0;
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
  `
  
  // 分辨率设置
  const resolutionLabel = document.createElement('label')
  resolutionLabel.textContent = '分辨率倍数:'
  resolutionLabel.style.cssText = `
    display: block;
    margin: 12px 0 8px 0;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
  `
  
  const resolutionSelect = document.createElement('select')
  resolutionSelect.style.cssText = `
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 14px;
    outline: none;
  `
  
  // 添加分辨率选项
  const resolutionOptions = [
    { value: 1, text: '1x (低清晰度)' },
    { value: 2, text: '2x (中等清晰度)' },
    { value: 3, text: '3x (高清晰度)' },
    { value: 4, text: '4x (超高清晰度)' },
    { value: 5, text: '5x (极致清晰度)' },
    { value: 6, text: '6x (超级清晰度)' },
    { value: 8, text: '8x (极限清晰度)' },
    { value: 10, text: '10x (终极清晰度)' },
    { value: 12, text: '12x (超清清晰度)' },
    { value: 15, text: '15x (超高清晰度)' },
    { value: 20, text: '20x (最高清晰度)' }
  ]
  
  resolutionOptions.forEach(option => {
    const opt = document.createElement('option')
    opt.value = option.value
    opt.textContent = option.text
    if (option.value === 3) opt.selected = true // 默认3倍
    resolutionSelect.appendChild(opt)
  })
  
  // JPEG质量设置（仅当格式为JPEG时显示）
  const qualityContainer = document.createElement('div')
  if (format === 'jpeg') {
    const qualityLabel = document.createElement('label')
    qualityLabel.textContent = 'JPEG质量:'
    qualityLabel.style.cssText = `
      display: block;
      margin: 12px 0 8px 0;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
    `
    
    const qualitySlider = document.createElement('input')
    qualitySlider.type = 'range'
    qualitySlider.min = '50'
    qualitySlider.max = '100'
    qualitySlider.value = '98' // 默认98%
    qualitySlider.style.cssText = `
      width: 100%;
      margin: 8px 0;
    `
    
    const qualityValue = document.createElement('div')
    qualityValue.textContent = `质量: 98%`
    qualityValue.style.cssText = `
      font-size: 12px;
      color: #6b7280;
      text-align: center;
    `
    
    // 实时更新质量值
    qualitySlider.addEventListener('input', (e) => {
      qualityValue.textContent = `质量: ${e.target.value}%`
    })
    
    qualityContainer.appendChild(qualityLabel)
    qualityContainer.appendChild(qualitySlider)
    qualityContainer.appendChild(qualityValue)
  }
  
  // 按钮容器
  const buttonContainer = document.createElement('div')
  buttonContainer.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  `
  
  const cancelButton = document.createElement('button')
  cancelButton.textContent = '取消'
  cancelButton.style.cssText = `
    padding: 8px 16px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: white;
    color: #374151;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  `
  
  const exportButton = document.createElement('button')
  exportButton.textContent = '导出'
  exportButton.style.cssText = `
    padding: 8px 16px;
    border: 1px solid #2563eb;
    border-radius: 6px;
    background: #2563eb;
    color: white;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  `
  
  // 添加悬停效果
  cancelButton.addEventListener('mouseenter', () => {
    cancelButton.style.background = '#f3f4f6'
  })
  
  cancelButton.addEventListener('mouseleave', () => {
    cancelButton.style.background = 'white'
  })
  
  exportButton.addEventListener('mouseenter', () => {
    exportButton.style.background = '#1d4ed8'
  })
  
  exportButton.addEventListener('mouseleave', () => {
    exportButton.style.background = '#2563eb'
  })
  
  // 处理导出
  const handleExport = () => {
    const resolution = parseInt(resolutionSelect.value)
    const quality = format === 'jpeg' ? parseInt(qualityContainer.querySelector('input[type="range"]')?.value || '98') / 100 : 1.0
    
    // 调用实际导出函数
    exportKnowledgeGraphAsImage(format, resolution, quality)
    
    // 关闭对话框
    document.body.removeChild(dialogContainer)
  }
  
  // 处理取消
  const handleCancel = () => {
    document.body.removeChild(dialogContainer)
  }
  
  // 添加事件监听器
  exportButton.addEventListener('click', handleExport)
  cancelButton.addEventListener('click', handleCancel)
  
  // 构建对话框
  dialogBox.appendChild(dialogTitle)
  dialogBox.appendChild(resolutionLabel)
  dialogBox.appendChild(resolutionSelect)
  dialogBox.appendChild(qualityContainer)
  dialogBox.appendChild(buttonContainer)
  buttonContainer.appendChild(cancelButton)
  buttonContainer.appendChild(exportButton)
  dialogContainer.appendChild(dialogBox)
  
  // 添加到文档
  document.body.appendChild(dialogContainer)
}

// 导出知识图谱为图片（PNG/JPEG）
const exportKnowledgeGraphAsImage = async (format = 'png', resolution = 3, quality = 0.98) => {
  try {
    if (!network) return
    
    // 获取整个知识图谱的边界
    const allNodes = nodes.get()
    if (allNodes.length === 0) return
    
    // 保存当前视图状态
    const currentScale = network.getScale()
    const currentPosition = network.getViewPosition()
    
    // 获取容器原始尺寸
    const containerRect = networkContainer.value.getBoundingClientRect()
    
    // 使用用户选择的分辨率倍数
    const exportWidth = containerRect.width * resolution
    const exportHeight = containerRect.height * resolution
    
    // 调整视图以显示整个图谱，增加边距确保内容不被裁剪
    network.fit({
      padding: {
        top: 100,
        right: 100,
        bottom: 100,
        left: 100
      },
      animation: false
    })
    
    // 等待视图调整完成
    await new Promise(resolve => setTimeout(resolve, 1000)) // 增加等待时间确保完全渲染
    
    // 获取当前canvas和上下文
    const originalCanvas = network.canvas.frame.canvas
    if (!originalCanvas) return
    
    // 创建一个临时的高分辨率canvas
    const tempContainer = document.createElement('div')
    tempContainer.style.width = `${exportWidth}px`
    tempContainer.style.height = `${exportHeight}px`
    tempContainer.style.position = 'absolute'
    tempContainer.style.left = '-9999px' // 将临时容器移出可视区域
    tempContainer.style.top = '-9999px'
    document.body.appendChild(tempContainer)
    
    // 创建临时网络实例
    const tempNodes = new DataSet(nodes.get())
    const tempEdges = new DataSet(edges.get())
    
    // 使用原始网络的选项
    const tempNetwork = new Network(tempContainer, { nodes: tempNodes, edges: tempEdges }, networkOptions)
    tempNetwork.setSize(exportWidth, exportHeight)
    tempNetwork.fit({
      padding: {
        top: 100,
        right: 100,
        bottom: 100,
        left: 100
      },
      animation: false
    })
    
    // 等待临时网络渲染完成
    await new Promise(resolve => setTimeout(resolve, 700)) // 增加等待时间确保高质量渲染
    
    // 获取临时网络的canvas
    const tempCanvas = tempNetwork.canvas.frame.canvas
    if (!tempCanvas) {
      document.body.removeChild(tempContainer)
      return
    }
    
    // 使用临时canvas直接导出，使用用户选择的质量
    const imageType = format === 'jpeg' ? 'image/jpeg' : 'image/png'
    const imageDataURL = tempCanvas.toDataURL(imageType, quality)
    
    // 清理临时资源
    tempNetwork.destroy()
    document.body.removeChild(tempContainer)
    
    // 恢复原始视图状态
    network.moveTo({
      position: currentPosition,
      scale: currentScale,
      animation: false
    })
    network.redraw()
    
    // 创建下载链接
    const a = document.createElement('a')
    a.href = imageDataURL
    a.download = `knowledge-graph-${new Date().toISOString().slice(0, 10)}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch (error) {
    console.error('导出图片失败:', error)
    alert('导出图片失败，请重试')
  }
}

// 导入知识图谱数据
const importKnowledgeGraph = (importedData) => {
  try {
    // 验证导入数据的格式
    if (!importedData || typeof importedData !== 'object') {
      throw new Error('导入数据格式不正确')
    }
    
    if (!Array.isArray(importedData.nodes) || !Array.isArray(importedData.edges)) {
      throw new Error('导入数据必须包含nodes和edges数组')
    }
    
    // 转换数据格式
    const { nodes: transformedNodes, edges: transformedEdges } = transformData(importedData)
    
    if (transformedNodes.length === 0) {
      throw new Error('导入数据中没有有效的节点')
    }
    
    // 清空当前数据集
    nodes.clear()
    edges.clear()
    
    // 添加新数据
    nodes.add(transformedNodes)
    edges.add(transformedEdges)
    
    // 更新节点颜色
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
    
    // 如果网络已经初始化，重新拟合视图
    if (network) {
      network.fit()
    }
    
    // 触发导入成功事件
    emit('import-success', importedData)
    return true
  } catch (error) {
    console.error('导入知识图谱失败:', error)
    throw error
  }
}

// 暴露方法给父组件
defineExpose({
  exportKnowledgeGraph,
  importKnowledgeGraph
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