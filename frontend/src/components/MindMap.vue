<template>
  <div class="mindmap-shell">
    <div class="mindmap-container" ref="container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

// 内部选中的节点ID，用于避免通过props传递导致组件重新渲染
const internalSelectedNodeId = ref(null)

// 暴露一个方法，用于更新选中的节点，而不是通过props传递
const updateSelectedNodeId = (nodeId) => {
  if (internalSelectedNodeId.value === nodeId || !svg) return
  
  internalSelectedNodeId.value = nodeId
  
  // 只更新节点的选中状态，不重渲染整个思维导图
  const nodesGroup = g.select('.nodes')
  if (!nodesGroup.empty()) {
    const nodes = nodesGroup.selectAll('g.node')
    nodes.classed('selected', d => d.data.id === nodeId)
    nodes.classed('hovered', d => d.data.id === hoveredNodeId.value && d.data.id !== nodeId)
  }
}

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
      nodeMaxWidth: 220,
      levelSpacing: 260,
      siblingSpacing: 110,
      textSize: 13
    })
  }
})

const emit = defineEmits(['import-success', 'export-data', 'node-update', 'node-move', 'node-select'])

const container = ref(null)
const containerSize = ref({ width: 0, height: 0 })

const hoveredNodeId = ref(null)
const editingNodeId = ref(null)

const svgReady = ref(false)

let svg = null
let g = null
let zoom = null
let lastLayout = null
let dragging = false

const getThemeByDepth = (depth) => {
  const palette = [
    { bar: '#2563eb', border: '#c7d2fe' }, // root
    { bar: '#ef4444', border: '#fecaca' },
    { bar: '#10b981', border: '#bbf7d0' },
    { bar: '#f59e0b', border: '#fde68a' },
    { bar: '#8b5cf6', border: '#e9d5ff' }
  ]
  return palette[Math.min(depth, palette.length - 1)]
}

// 文本测量缓存
const textWidthCache = new Map()

const smartWrapText = (text, maxWidth, fontSize = 13) => {
  if (text === undefined || text === null) text = ''
  const textStr = String(text)

  const cacheKey = `${textStr}-${maxWidth}-${fontSize}`
  if (textWidthCache.has(cacheKey)) return textWidthCache.get(cacheKey)

  if (textStr.trim() === '') {
    const v = ['']
    textWidthCache.set(cacheKey, v)
    return v
  }

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  ctx.font = `${fontSize}px Microsoft YaHei`

  const words = textStr.split(/\s+|([:：,，.。;；!！?？])/).filter(w => w)
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
          if (ctx.measureText(charTest).width <= maxWidth) charLine = charTest
          else {
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
  if (lines.length === 0) lines.push('')

  textWidthCache.set(cacheKey, lines)
  return lines
}

const calculateNodeSize = (node) => {
  const { nodeMaxWidth, textSize } = props.config
  const textLines = smartWrapText(node.topic, nodeMaxWidth, textSize)
  const lineHeight = textSize + 7
  const paddingX = 18
  const paddingY = 12

  const width = nodeMaxWidth
  const height = textLines.length * lineHeight + paddingY * 2

  return { ...node, textLines, width, height, lineHeight }
}

// 更新容器尺寸
const updateContainerSize = () => {
  const el = container.value
  if (!el) return false

  const w = el.clientWidth || 1600
  const h = el.clientHeight || 900
  const changed = w !== containerSize.value.width || h !== containerSize.value.height
  containerSize.value = { width: w, height: h }
  return changed
}

// 初始化缩放
const initZoom = () => {
  if (zoom) return
  zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      if (g) g.attr('transform', event.transform)
    })

  svg.call(zoom)
}

// 适配视图
const resetView = (width, height, root) => {
  if (!svg || !root || !zoom) return

  let maxX = -Infinity, maxY = -Infinity
  let minX = Infinity, minY = Infinity

  root.each(d => {
    const x = d.x || 0
    const y = d.y || 0
    maxX = Math.max(maxX, x + d.data.width / 2)
    maxY = Math.max(maxY, y + d.data.height / 2)
    minX = Math.min(minX, x - d.data.width / 2)
    minY = Math.min(minY, y - d.data.height / 2)
  })

  const contentW = maxX - minX
  const contentH = maxY - minY
  const scale = Math.min(width / (contentW || width), height / (contentH || height), 0.9)

  const tx = (width - (minX + maxX) * scale) / 2
  const ty = (height - (minY + maxY) * scale) / 2

  svg.transition().duration(250)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale))
}

// ===== 工具条功能 =====
const zoomIn = () => {
  if (!svg || !zoom) return
  svg.transition().duration(150).call(zoom.scaleBy, 1.15)
}
const zoomOut = () => {
  if (!svg || !zoom) return
  svg.transition().duration(150).call(zoom.scaleBy, 0.87)
}
const fitView = () => {
  if (!lastLayout) return
  resetView(containerSize.value.width, containerSize.value.height, lastLayout)
}
const centerRoot = () => {
  if (!svg || !zoom || !lastLayout) return
  const root = lastLayout
  const w = containerSize.value.width
  const h = containerSize.value.height

  const tx = w / 2 - (root.x || 0)
  const ty = h / 2 - (root.y || 0)
  svg.transition().duration(250)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(1))
}

const ensureDefs = () => {
  if (!svg || svg.select('defs').size()) return

  const defs = svg.append('defs')

  const f = defs.append('filter')
    .attr('id', 'mmShadow')
    .attr('x', '-30%')
    .attr('y', '-30%')
    .attr('width', '160%')
    .attr('height', '160%')

  f.append('feDropShadow')
    .attr('dx', 0)
    .attr('dy', 3)
    .attr('stdDeviation', 5)
    .attr('flood-color', '#0f172a')
    .attr('flood-opacity', 0.10)
}

const renderMindMap = () => {
  try {
    const el = container.value
    if (!el) return

    const sizeChanged = updateContainerSize()

    let svgElement = el.querySelector('svg')
    if (!svgElement) {
      svg = d3.select(el)
        .append('svg')
        .attr('width', containerSize.value.width)
        .attr('height', containerSize.value.height)
        .style('cursor', 'grab')

      g = svg.append('g')
      initZoom()
      ensureDefs()
      svgReady.value = true
    } else {
      svg = d3.select(svgElement)
      if (sizeChanged) {
        svg.attr('width', containerSize.value.width)
          .attr('height', containerSize.value.height)
      }
      g = svg.select('g')
      if (g.empty()) g = svg.append('g')
      ensureDefs()
      svgReady.value = true
    }

    const sourceData = props.dataObj?.root ? props.dataObj : props.rawData
    // 深拷贝原始数据，避免直接修改props.dataObj
    const rawRoot = sourceData?.root ? JSON.parse(JSON.stringify(sourceData.root)) : { id: 'root', topic: '技术内容分析', children: [] }

    // 保留原始 topic；只补齐 id
    const normalize = (node, depth = 0, path = '') => {
      if (!node || typeof node !== 'object') {
        return { id: `node-${path}-${depth}`, topic: '', children: [], depth }
      }
      return {
        id: node.id || `node-${path}-${depth}`,
        topic: node.topic,
        children: Array.isArray(node.children)
          ? node.children.map((c, i) => normalize(c, depth + 1, `${path ? path + '-' : ''}${depth}-${i}`))
          : [],
        depth
      }
    }

    const validRoot = normalize(rawRoot)
    const d3Root = d3.hierarchy(validRoot).each(d => {
      // 不直接修改props.dataObj，只修改本地数据
      Object.assign(d.data, calculateNodeSize(d.data))
    })

    const { levelSpacing, siblingSpacing } = props.config
    const treeLayout = d3.tree()
      .nodeSize([siblingSpacing, levelSpacing])
      .separation((a, b) => (a.depth !== b.depth ? 2 : 1.4))

    const rootLayout = treeLayout(d3Root)

    rootLayout.each(d => {
      if (d.data.x !== undefined && d.data.y !== undefined) {
        d.x = d.data.x
        d.y = d.data.y
      } else {
        const tmp = d.x
        d.x = d.y
        d.y = tmp
        d.data.x = d.x
        d.data.y = d.y
      }
      d.data.depth = d.depth
    })

    lastLayout = rootLayout

    // groups
    let linksGroup = g.select('.links')
    if (linksGroup.empty()) linksGroup = g.append('g').attr('class', 'links')

    let nodesGroup = g.select('.nodes')
    if (nodesGroup.empty()) nodesGroup = g.append('g').attr('class', 'nodes')

    // link generator：更像 XMind 的柔和曲线
    const linkGenerator = d3.linkHorizontal()
      .x(d => d.x)
      .y(d => d.y)

    const links = linksGroup.selectAll('path')
      .data(rootLayout.links(), d => `${d.source.data.id}-${d.target.data.id}`)

    links.exit().remove()

    links.enter()
      .append('path')
      .attr('fill', 'none')
      .attr('stroke-linecap', 'round')
      .attr('stroke-linejoin', 'round')
      .attr('pointer-events', 'none')
      .merge(links)
      .attr('data-link', d => `${d.source.data.id}-${d.target.data.id}`)
      .attr('stroke-width', 1.15)
      .attr('stroke', d => {
        const t = getThemeByDepth(d.target.depth)
        return d3.color(t.bar).copy({ opacity: 0.35 })
      })
      .attr('d', linkGenerator)

    // drag
    const drag = d3.drag()
      .on('start', (event, d) => {
        event.sourceEvent.stopPropagation()
        dragging = true
        emit('node-select', d.data.id)
        svg.style('cursor', 'grabbing')
      })
      .on('drag', (event, d) => {
        if (!dragging) return
        const dx = event.dx
        const dy = event.dy

        d.x += dx
        d.y += dy
        d3.select(event.currentTarget).attr('transform', `translate(${d.x}, ${d.y})`)

        const moveChildren = (node) => {
          if (!node.children) return
          for (const c of node.children) {
            c.x += dx
            c.y += dy
            moveChildren(c)
          }
        }
        moveChildren(d)

        const updateLayoutNode = (layoutNode) => {
          if (layoutNode.data.id === d.data.id) {
            layoutNode.x = d.x
            layoutNode.y = d.y
            if (layoutNode.children) {
              for (const c of layoutNode.children) {
                c.x += dx
                c.y += dy
              }
            }
            return true
          }
          if (layoutNode.children) {
            for (const c of layoutNode.children) {
              if (updateLayoutNode(c)) return true
            }
          }
          return false
        }
        if (lastLayout) updateLayoutNode(lastLayout)

        updateAllLinks()

        emit('node-move', { nodeId: d.data.id, x: d.x, y: d.y })
      })
      .on('end', (event, d) => {
        dragging = false
        svg.style('cursor', 'grab')

        // 不再直接修改props.dataObj，只通过事件通知父组件更新位置
        // 位置更新已经通过node-move事件通知父组件
        // 这里移除了直接修改props的代码，遵循Vue单向数据流原则

        emit('node-update', { nodeId: d.data.id, position: { x: d.x, y: d.y } })
      })

    // nodes data join
    const nodes = nodesGroup.selectAll('g.node')
      .data(rootLayout.descendants().filter(d => d.data && d.data.id), d => d.data.id)

    nodes.exit().remove()

    const newNodes = nodes.enter()
      .append('g')
      .attr('class', d => `node level-${d.depth}`)
      .attr('data-node-id', d => d.data.id)

    newNodes.append('rect')
      .attr('class', 'node-card')
      .attr('rx', 12)
      .attr('ry', 12)
      .attr('filter', 'url(#mmShadow)')
      .attr('pointer-events', 'all')

    newNodes.append('rect')
      .attr('class', 'node-bar')
      .attr('rx', 12)
      .attr('ry', 12)
      .attr('pointer-events', 'none')

    newNodes.append('text')
      .attr('class', 'node-text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', props.config.textSize)
      .attr('pointer-events', 'none')

    const nodesToUpdate = newNodes.merge(nodes)

    // events
    nodesToUpdate
      .on('mouseenter', (event, d) => { hoveredNodeId.value = d.data.id })
      .on('mouseleave', () => { hoveredNodeId.value = null })

    nodesToUpdate.on('click', (event, d) => {
      event.stopPropagation()
      event.preventDefault()
      emit('node-select', d.data.id)

      // 直接更新节点选中状态，避免等待父组件更新props后再更新
      const currentNodes = nodesGroup.selectAll('g.node')
      currentNodes.classed('selected', n => n.data.id === d.data.id)
      currentNodes.classed('hovered', n => n.data.id === hoveredNodeId.value && n.data.id !== d.data.id)
    })

    nodesToUpdate.on('dblclick', (event, d) => {
      event.stopPropagation()
      event.preventDefault()
      editNode(event, d)
    })

    nodesToUpdate.call(drag)

    // position + states
    nodesToUpdate
      .classed('selected', d => d.data.id === internalSelectedNodeId.value)
      .classed('hovered', d => d.data.id === hoveredNodeId.value && d.data.id !== internalSelectedNodeId.value)
      .attr('transform', d => `translate(${d.x || 0}, ${d.y || 0})`)

    // update card rect
    nodesToUpdate.select('rect.node-card')
  .attr('x', d => -d.data.width / 2)
  .attr('y', d => -d.data.height / 2)
  .attr('width', d => d.data.width)
  .attr('height', d => d.data.height)
  .attr('fill', '#ffffff')
  .attr('stroke', 'rgba(226,232,240,0.95)') // 永远浅灰边
  .attr('stroke-width', 1.1)

    // update left color bar
    nodesToUpdate.select('rect.node-bar')
      .attr('x', d => -d.data.width / 2)
      .attr('y', d => -d.data.height / 2)
      .attr('width', 10)
      .attr('height', d => d.data.height)
      .attr('fill', d => getThemeByDepth(d.depth).bar)
      .attr('opacity', 0.95)

    // update text
    nodesToUpdate.select('text.node-text')
      .each(function(d) {
        const t = d3.select(this)
        t.selectAll('tspan').remove()

        const lines = Array.isArray(d.data.textLines) ? d.data.textLines : ['']
        lines.forEach((line, idx) => {
          const y = (idx - (lines.length - 1) / 2) * d.data.lineHeight
          t.append('tspan').attr('x', 0).attr('y', y).text(line)
        })
      })

    // 默认适配（首次）
    if (sizeChanged) {
      resetView(containerSize.value.width, containerSize.value.height, rootLayout)
    }
  } catch (error) {
    console.error('思维导图渲染失败:', error)
    const el = container.value
    if (el) {
      el.innerHTML = `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#ef4444;font-size:14px;">
        渲染失败：${error.message}
      </div>`
    }
  }
}

const updateAllLinks = () => {
  if (!g || !lastLayout) return

  const linkGenerator = d3.linkHorizontal().x(d => d.x).y(d => d.y)

  const findNode = (layoutNode, targetId) => {
    if (layoutNode.data.id === targetId) return layoutNode
    if (layoutNode.children) {
      for (const c of layoutNode.children) {
        const found = findNode(c, targetId)
        if (found) return found
      }
    }
    return null
  }

  g.select('.links').selectAll('path')
    .attr('d', d => {
      const s = findNode(lastLayout, d.source.data.id)
      const t = findNode(lastLayout, d.target.data.id)
      if (s && t) return linkGenerator({ source: s, target: t })
      return linkGenerator(d)
    })
}

const editNode = (event, d) => {
  if (editingNodeId.value) return
  editingNodeId.value = d.data.id

  const nodeGroup = d3.select(event.currentTarget)
  const textElement = nodeGroup.select('text.node-text')
  const rectCard = nodeGroup.select('rect.node-card')

  const originalStroke = rectCard.attr('stroke')
  const originalStrokeWidth = rectCard.attr('stroke-width')

  rectCard.attr('stroke', '#2563eb').attr('stroke-width', 2.2)
  textElement.style('visibility', 'hidden')

  const width = d.data.width
  const height = d.data.height

  const inputGroup = nodeGroup.append('g').attr('class', 'edit-input-group')

  const input = inputGroup.append('foreignObject')
    .attr('x', -width / 2 + 14)
    .attr('y', -height / 2 + 10)
    .attr('width', width - 28)
    .attr('height', height - 20)
    .append('xhtml:input')
    .attr('type', 'text')
    .attr('value', d.data.topic ?? '')
    .style('width', '100%')
    .style('height', '100%')
    .style('border', 'none')
    .style('outline', 'none')
    .style('background', 'transparent')
    .style('font-size', `${props.config.textSize}px`)
    .style('color', '#111827')

  const inputEl = input.node()
  if (inputEl) {
    try {
      inputEl.focus()
      inputEl.select()
    } catch (e) {
      console.error('Focus error:', e)
    }
  }

  const finish = () => {
    if (!inputEl) {
      cleanup()
      return
    }
    
    const v = String(inputEl.value ?? '').trim()
    if (v && v !== d.data.topic) {
      // 更新节点数据
      const updatedTopic = v
      
      // 直接更新当前节点的文本，避免重新渲染整个思维导图
      textElement.selectAll('tspan').remove()
      const textLines = smartWrapText(updatedTopic, props.config.nodeMaxWidth, props.config.textSize)
      textLines.forEach((line, idx) => {
        const y = (idx - (textLines.length - 1) / 2) * (props.config.textSize + 7)
        textElement.append('tspan').attr('x', 0).attr('y', y).text(line)
      })
      
      // 更新节点在数据中的topic
      d.data.topic = updatedTopic
      Object.assign(d.data, calculateNodeSize(d.data))
      
      // 通知父组件更新数据
      emit('node-update', { nodeId: d.data.id, topic: updatedTopic })
      
      // 不重新渲染整个思维导图，只更新当前节点
    }
    cleanup()
  }

  const cancel = () => cleanup(true)

  const cleanup = (isCancel = false) => {
    inputGroup.remove()
    textElement.style('visibility', 'visible')
    rectCard.attr('stroke', originalStroke).attr('stroke-width', originalStrokeWidth)
    editingNodeId.value = null
    // 取消编辑时也不重新渲染整个思维导图
  }

  input.on('blur', finish)
  input.on('keydown', (e) => {
    if (e.key === 'Enter') finish()
    if (e.key === 'Escape') cancel()
  })
}

// ===== Resize (throttle) =====
let resizeTimeout
const handleResize = () => {
  clearTimeout(resizeTimeout)
  resizeTimeout = setTimeout(() => {
    if (!container.value) return
    const changed = updateContainerSize()
    if (changed && svg) {
      svg.attr('width', containerSize.value.width)
        .attr('height', containerSize.value.height)
      renderMindMap()
    }
  }, 120)
}

const handleKeydown = (e) => {
  // 编辑中不抢按键
  if (editingNodeId.value) {
    if (e.key === 'Escape') {
      // 让 input 自己处理
    }
    return
  }

  if (e.key === 'f' || e.key === 'F') fitView()
  if (e.key === '0') centerRoot()
  if (e.key === '+' || e.key === '=') zoomIn()
  if (e.key === '-' || e.key === '_') zoomOut()
}

onMounted(() => {
  nextTick(() => {
    renderMindMap()
    window.addEventListener('resize', handleResize)
    window.addEventListener('keydown', handleKeydown)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeydown)
})

// 数据变化时重渲染
watch(
  () => JSON.stringify(props.dataObj),
  (n, o) => {
    if (n !== o) nextTick(renderMindMap)
  }
)

// 移除了对props.selectedNodeId的watch监听器，改为通过内部方法updateSelectedNodeId更新选中状态

// 导出思维导图
const exportMindMap = (format = 'json') => {
  if (format === 'json') {
    const sourceData = props.dataObj.root ? props.dataObj : props.rawData
    const exportData = { version: '1.0', exportDate: new Date().toISOString(), mindmap: sourceData }
    emit('export-data', exportData)
    const jsonString = JSON.stringify(exportData, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mindmap-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } else if (format === 'png' || format === 'jpeg') {
    // 显示导出设置对话框
    showExportSettingsDialog(format)
  }
}

// 显示导出设置对话框
const showExportSettingsDialog = (format) => {
  if (!svg || !svgReady.value) {
    console.error('SVG未准备好，无法导出图片')
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
    qualitySlider.value = '92' // 默认92%
    qualitySlider.style.cssText = `
      width: 100%;
      margin: 8px 0;
    `
    
    const qualityValue = document.createElement('div')
    qualityValue.textContent = `质量: 92%`
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
    const quality = format === 'jpeg' ? parseInt(qualityContainer.querySelector('input[type="range"]')?.value || '92') / 100 : 1.0
    
    // 调用实际导出函数
    exportMindMapAsImage(format, resolution, quality)
    
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

// 实际导出思维导图为图片
const exportMindMapAsImage = (format, resolution, quality) => {
  if (!svg || !svgReady.value) {
    console.error('SVG未准备好，无法导出图片')
    return
  }
  
  // 获取SVG元素
  const svgElement = svg.node()
  if (!svgElement) {
    console.error('无法获取SVG元素')
    return
  }
  
  // 创建一个临时的canvas元素
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('无法获取Canvas上下文')
    return
  }
  
  // 设置canvas尺寸为SVG的实际尺寸乘以分辨率倍数
  const svgRect = svgElement.getBoundingClientRect()
  canvas.width = svgRect.width * resolution
  canvas.height = svgRect.height * resolution
  
  // 将SVG转换为DataURL
  const svgData = new XMLSerializer().serializeToString(svgElement)
  const img = new Image()
  img.onload = () => {
    // 绘制图片到canvas，使用更高的分辨率
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    
    // 将canvas转换为图片数据URL
    const mimeType = format === 'png' ? 'image/png' : 'image/jpeg'
    const dataUrl = canvas.toDataURL(mimeType, quality)
    
    // 触发下载
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = `mindmap-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
  
  img.onerror = (error) => {
    console.error('图片加载失败:', error)
  }
  
  // 设置SVG数据URL
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
  img.src = URL.createObjectURL(svgBlob)
}

const importMindMap = (jsonData) => {
  try {
    if (!jsonData || !jsonData.mindmap) throw new Error('无效的数据格式')
    emit('import-success', jsonData.mindmap)
    renderMindMap()
    return true
  } catch (e) {
    console.error(e)
    return false
  }
}

const addNode = (nodeId) => {
  // 使用传入的节点ID作为父节点，如果没有则使用内部选中的节点，否则使用根节点
  const targetId = nodeId || internalSelectedNodeId.value || 'root'
  
  // 生成新节点ID
  const newNodeId = `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`
  
  // 创建新节点
  const newNode = {
    id: newNodeId,
    topic: '新节点',
    children: []
  }
  
  // 通知父组件添加节点，由父组件更新数据
  emit('node-update', { 
    action: 'add', 
    parentId: targetId, 
    newNode: newNode 
  })
}

const deleteNode = (nodeId) => {
  // 使用传入的节点ID作为要删除的节点，如果没有则使用内部选中的节点，不允许删除根节点
  const targetId = nodeId || internalSelectedNodeId.value
  if (!targetId || targetId === 'root') return
  
  // 通知父组件删除节点，由父组件更新数据
  emit('node-update', { 
    action: 'delete', 
    nodeId: targetId 
  })
}

const importFromFile = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const jsonData = JSON.parse(e.target.result)
      const ok = importMindMap(jsonData)
      ok ? resolve(jsonData) : reject(new Error('导入失败'))
    } catch (err) {
      reject(new Error('JSON 解析错误'))
    }
  }
  reader.onerror = () => reject(new Error('文件读取错误'))
  reader.readAsText(file)
})


defineExpose({
  exportMindMap,
  importMindMap,
  importFromFile,
  editNode,
  addNode,
  deleteNode,
  updateSelectedNodeId
})
</script>

<style scoped>
/* 外壳：用于放工具条 */
.mindmap-shell{
  width:100%;
  height:100%;
  position:relative;
}

/* 工具条 */
.mm-toolbar{
  position:absolute;
  top:14px;
  right:14px;
  z-index:10;
  display:flex;
  gap:0;
  padding:6px;
  border-radius:999px;
  background:rgba(255,255,255,0.88);
  border:1px solid rgba(226,232,240,0.9);
  box-shadow:0 10px 30px rgba(15,23,42,0.10);
  backdrop-filter: blur(10px);
}

.mm-tool{
  height:34px;
  padding:0 14px;
  border-radius:999px;
  border:none;
  background:transparent;
  color:#0f172a;
  font-size:12px;
  font-weight:700;
  cursor:pointer;
  transition: background .12s ease, transform .12s ease, opacity .12s ease;
}

.mm-tool:hover{ background: rgba(15,23,42,0.06); }
.mm-tool:active{ transform: translateY(1px); }
.mm-tool:disabled{ opacity:.45; cursor:not-allowed; }

/* 分隔线 */
.mm-tool + .mm-tool{
  position:relative;
}
.mm-tool + .mm-tool::before{
  content:"";
  position:absolute;
  left:-3px;
  top:7px;
  bottom:7px;
  width:1px;
  background: rgba(226,232,240,0.9);
}

.mm-tool:hover{
  background:#f8fafc;
  border-color:#cbd5e1;
}
.mm-tool:active{ transform: translateY(1px); }
.mm-tool:disabled{ opacity:.55; cursor:not-allowed; }

/* 画布 */
.mindmap-container{
  width:100%;
  height:100%;
  min-height:900px;
  border-radius:16px;
  overflow:hidden;
  position:relative;
  border:1px solid rgba(226,232,240,0.9);

  background:
    linear-gradient(180deg, #fbfcfe 0%, #f7f9fc 100%);
}

.mindmap-container::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background-image:
    linear-gradient(to right, rgba(15,23,42,0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15,23,42,0.05) 1px, transparent 1px);
  background-size: 36px 36px;   /* 更细 */
  opacity:.22;                  /* 更淡 */
}

:deep(.links path){
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 节点：hover/selected 动效 */
:deep(.node .node-card){
  filter: drop-shadow(0 8px 18px rgba(15,23,42,0.10));
  transition: filter .14s ease, transform .14s ease;
}

:deep(.node.hovered .node-card){
  filter: drop-shadow(0 14px 28px rgba(15,23,42,0.14));
  transform: translateY(-1px);
}

:deep(.node.selected .node-card){
  filter:
    drop-shadow(0 16px 34px rgba(37,99,235,0.18))
    drop-shadow(0 0 0 rgba(0,0,0,0));
}


/* 文本 */
:deep(text.node-text){
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue",
    Arial, "Noto Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
  font-weight: 650;
  letter-spacing: .1px;
  fill: rgba(15,23,42,0.92) !important;
  text-rendering: geometricPrecision;
}

/* 编辑输入 */
:deep(.edit-input-group input){
  box-sizing: border-box !important;
  border-radius: 10px !important;
  border: 1px solid rgba(59,130,246,0.45) !important;
  background: rgba(255,255,255,0.92) !important;
  padding: 6px 10px !important;
  font-weight: 650 !important;
  box-shadow: 0 12px 30px rgba(37,99,235,0.20) !important;
}
:deep(.edit-input-group input:focus){
  border-color: rgba(37,99,235,0.85) !important;
  box-shadow: 0 14px 34px rgba(37,99,235,0.26) !important;
}

/* 边框保持原色 */
:deep(.node rect){
  rx: 12;
  ry: 12;
  shape-rendering: geometricPrecision;
  transition: filter .14s ease, transform .14s ease;
}

/* hover：轻微抬起 */
:deep(.node:hover rect){
  filter: drop-shadow(0 10px 22px rgba(15,23,42,0.14));
  transform: translateY(-1px);
}

/* 选中：只让卡片发光 */
:deep(.node.selected .node-card){
  filter:
    drop-shadow(0 18px 38px rgba(37,99,235,0.26))
    drop-shadow(0 0 0 rgba(0,0,0,0));
  transform: translateY(-1px);
}

/* hover：抬起卡片 */
:deep(.node.hovered .node-card),
:deep(.node:hover .node-card){
  filter: drop-shadow(0 14px 28px rgba(15,23,42,0.14));
  transform: translateY(-1px);
}

/* 左色条不受选中影响 */
:deep(.node .node-bar){
  filter: none !important;
  transform: none !important;
}
</style>
