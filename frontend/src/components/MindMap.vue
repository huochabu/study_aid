<template>
  <div class="mindmap-container" ref="container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  dataObj: {
    type: Object,
    required: false,
    default: () => ({ root: { id: 'root', topic: '技术内容分析', children: [] } })
  },
  rawData: {
    type: Object,
    required: false,
    default: () => ({ root: { id: 'root', topic: '技术内容分析', children: [] } })
  },
  config: {
    type: Object,
    default: () => ({
      nodeMaxWidth: 200,
      levelSpacing: 300,
      siblingSpacing: 120,
      textSize: 13
    })
  }
})

const container = ref(null)
let svg = null
let g = null
let zoom = null

// ===== 按层级分配颜色（参照 KnowledgeView 配色）=====
const getColorByDepth = (depth) => {
  const palette = [
    { fill: '#eff6ff', border: '#2563eb' }, // level 0 - 蓝（根）
    { fill: '#fef2f2', border: '#ef4444' }, // level 1 - 红
    { fill: '#ecfdf5', border: '#10b981' }, // level 2 - 绿
    { fill: '#fffbeb', border: '#f59e0b' }, // level 3 - 橙
    { fill: '#f5f3ff', border: '#8b5cf6' }  // level 4+ - 紫
  ]
  return palette[Math.min(depth, palette.length - 1)]
}

// 智能文本换行（保持不变）
const smartWrapText = (text, maxWidth, fontSize = 13) => {
  if (!text) return ['']
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  ctx.font = `${fontSize}px Microsoft YaHei`
  const words = text.split(/\s+|([:：,，.。;；!！?？])/).filter(w => w)
  const lines = []
  let currentLine = ''
  for (const word of words) {
    const testLine = currentLine ? `${currentLine}${word}` : word
    const testWidth = ctx.measureText(testLine).width
    if (testWidth <= maxWidth) {
      currentLine = testLine
    } else {
      if (currentLine) lines.push(currentLine)
      if (ctx.measureText(word).width > maxWidth) {
        const chars = word.split('')
        let charLine = ''
        for (const char of chars) {
          const charTest = charLine + char
          if (ctx.measureText(charTest).width <= maxWidth) {
            charLine = charTest
          } else {
            lines.push(charLine)
            charLine = char
          }
        }
        currentLine = charLine
      } else {
        currentLine = word
      }
    }
  }
  if (currentLine) lines.push(currentLine)
  return lines
}

// 递归校验节点（保持不变）
const validateNodeRecursive = (node, depth = 0) => {
  if (typeof node !== 'object' || node === null) {
    return {
      id: `default-node-${depth}-${Math.random().toString(36).slice(2, 8)}`,
      topic: `未识别节点(${depth})`,
      children: [],
      depth
    }
  }
  const validNode = {
    id: node.id || `auto-id-${depth}-${Math.random().toString(36).slice(2, 8)}`,
    topic: node.topic || `未命名节点(${depth})`,
    children: Array.isArray(node.children) ? node.children : [],
    depth
  }
  validNode.children = validNode.children.map(child =>
    validateNodeRecursive(child, depth + 1)
  )
  return validNode
}

// 计算节点尺寸（保持不变）
const calculateNodeSize = (node) => {
  const { nodeMaxWidth, textSize } = props.config
  const textLines = smartWrapText(node.topic, nodeMaxWidth)
  const lineHeight = textSize + 7
  const padding = 12
  return {
    ...node,
    textLines,
    width: nodeMaxWidth,
    height: textLines.length * lineHeight + padding * 2,
    lineHeight
  }
}

// 初始化缩放（保持不变）
const initZoom = (containerEl) => {
  if (!containerEl) return
  zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      if (g) g.attr('transform', event.transform)
    })
  if (svg) svg.call(zoom)
}

// 重置视图居中（保持不变）
const resetView = (width, height, root) => {
  if (!svg || !root) return
  let maxX = -Infinity, maxY = -Infinity
  let minWidth = Infinity, minHeight = Infinity
  root.each(d => {
    const x = d.x || 0
    const y = d.y || 0
    maxX = Math.max(maxX, x + d.data.width / 2)
    maxY = Math.max(maxY, y + d.data.height / 2)
    minWidth = Math.min(minWidth, x - d.data.width / 2)
    minHeight = Math.min(minHeight, y - d.data.height / 2)
  })
  const contentWidth = maxX - minWidth
  const contentHeight = maxY - minHeight
  const scale = Math.min(
    width / (contentWidth || width),
    height / (contentHeight || height),
    0.7
  )
  const translateX = (width - (minWidth + maxX) * scale) / 2
  const translateY = (height - (minHeight + maxY) * scale) / 2
  svg.transition().duration(300)
    .call(zoom.transform, d3.zoomIdentity.translate(translateX, translateY).scale(scale))
}

// 渲染主函数
const renderMindMap = () => {
  try {
    const containerEl = container.value
    if (!containerEl) return

    containerEl.innerHTML = ''
    const width = containerEl.clientWidth || 1800
    const height = containerEl.clientHeight || 1000

    svg = d3.select(containerEl)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('cursor', 'grab')

    g = svg.append('g')
    initZoom(containerEl)

    const sourceData = props.dataObj.root ? props.dataObj : props.rawData
    const rawRoot = sourceData.root || { id: 'root', topic: '技术内容分析', children: [] }
    const validRoot = validateNodeRecursive(rawRoot)
    const d3Root = d3.hierarchy(validRoot)
      .each(d => {
        Object.assign(d.data, calculateNodeSize(d.data))
      })

    const { levelSpacing, siblingSpacing } = props.config
    const treeLayout = d3.tree()
      .nodeSize([siblingSpacing, levelSpacing])
      .separation((a, b) => a.depth !== b.depth ? 2 : 1.5)

    const rootLayout = treeLayout(d3Root)
    rootLayout.each(d => {
      const temp = d.x
      d.x = d.y
      d.y = temp
    })

    // 连接线
    const linkGenerator = d3.linkHorizontal()
      .x(d => d.x)
      .y(d => d.y)

    g.append('g')
      .attr('class', 'links')
      .selectAll('path')
      .data(rootLayout.links())
      .enter()
      .append('path')
      .attr('d', linkGenerator)
      .attr('fill', 'none')
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', 1.2)
      .attr('stroke-opacity', 0.8)

    // 节点
    const nodes = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(rootLayout.descendants())
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x || 0}, ${d.y || 0})`)
      .attr('class', d => `node level-${d.depth}`)

    // 节点背景：按 depth 分配颜色
    nodes.append('rect')
      .attr('x', d => -d.data.width / 2)
      .attr('y', d => -d.data.height / 2)
      .attr('width', d => d.data.width)
      .attr('height', d => d.data.height)
      .attr('rx', 6)
      .attr('ry', 6)
      .attr('fill', d => getColorByDepth(d.depth).fill)
      .attr('stroke', d => getColorByDepth(d.depth).border)
      .attr('stroke-width', 2)
      .attr('fill-opacity', 1)
      .attr('filter', 'url(#shadow)')

    // 节点文本
    nodes.each(function(d) {
      const nodeData = d.data
      const textGroup = d3.select(this).append('text')
        .attr('class', 'node-text')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-size', props.config.textSize)
        .attr('font-family', 'Microsoft YaHei, sans-serif')
        .attr('fill', '#000')
        .attr('font-weight', 400)

      nodeData.textLines.forEach((line, index) => {
        const y = (index - (nodeData.textLines.length - 1) / 2) * nodeData.lineHeight
        textGroup.append('tspan')
          .attr('x', 0)
          .attr('y', y)
          .text(line)
      })
    })

    // 添加阴影滤镜（仅一次）
    if (!svg.select('defs').size()) {
      svg.append('defs')
        .append('filter')
        .attr('id', 'shadow')
        .attr('x', '-20%')
        .attr('y', '-20%')
        .attr('width', '140%')
        .attr('height', '140%')
        .append('feDropShadow')
        .attr('dx', 0)
        .attr('dy', 2)
        .attr('stdDeviation', 4)
        .attr('flood-color', '#000')
        .attr('flood-opacity', 0.1)
    }

    resetView(width, height, rootLayout)
  } catch (error) {
    console.error('思维导图渲染失败:', error)
    const containerEl = container.value
    if (containerEl) {
      containerEl.innerHTML = `
        <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#ef4444;font-size:14px;">
          渲染失败：${error.message}
        </div>
      `
    }
  }
}

onMounted(() => {
  nextTick(() => {
    renderMindMap()
    window.addEventListener('resize', renderMindMap)
  })
})

watch(
  () => [props.dataObj, props.rawData],
  () => nextTick(renderMindMap),
  { deep: true, immediate: false }
)

onUnmounted(() => {
  window.removeEventListener('resize', renderMindMap)
})
</script>

<style scoped>
.mindmap-container {
  width: 100%;
  height: 100%;
  min-height: 900px;
  background-color: #f9fafb;
  border-radius: 8px;
  overflow: hidden;
}

:deep(svg) {
  transition: cursor 0.2s ease;
}
:deep(svg:active) {
  cursor: grabbing;
}

:deep(.node-text) {
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

:deep(.node) {
  transition: transform 0.2s ease;
}
:deep(.node:hover) {
  transform: scale(1.03);
}
</style>