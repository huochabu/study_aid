<template>
  <div class="image-viewer-container relative w-full h-full bg-zinc-900 overflow-auto flex items-center justify-center p-4">
      <div class="relative inline-block">
        <img 
            ref="imgEl" 
            :src="source" 
            class="max-w-full max-h-[80vh] object-contain shadow-2xl rounded-sm"
            @load="handleLoad" 
        />
        
        <!-- Overlays -->
        <div v-for="(box, i) in highlights" :key="i"
             class="absolute border-2 border-yellow-400 bg-yellow-400/20"
             :style="getBoxStyle(box)"
        ></div>
      </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  source: String,
  layoutData: { type: Array, default: () => [] }, // [{text, box: [[x,y],...]}]
  highlightText: String
})

const imgEl = ref(null)
const naturalSize = ref({ width: 1, height: 1 })
const displaySize = ref({ width: 1, height: 1 })

const handleLoad = (e) => {
    const el = e.target
    naturalSize.value = { width: el.naturalWidth, height: el.naturalHeight }
    displaySize.value = { width: el.clientWidth, height: el.clientHeight }
}

const highlights = computed(() => {
    if (!props.highlightText || !props.layoutData.length) return []
    
    // 1. Normalize target
    // Allow . - _ for filenames, code paths
    const clean = (str) => {
        return str.toLowerCase()
          .replace(/([^\x00-\xff])/g, ' $1 ') 
          .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\.\-\_]/g, ' ') // Allow . - _
          .trim()
          .split(/\s+/)
          .filter(t => t.length > 0)
    }
    
    const targetTokens = clean(props.highlightText)
    if (targetTokens.length === 0) return []
    
    const targetSet = new Set(targetTokens)
    
    return props.layoutData.filter(item => {
        // 2. Normalize OCR text line
        const lineTokens = clean(item.text)
        if (lineTokens.length === 0) return false
        
        // 3. Calculate overlap
        let matchCount = 0
        let hasLongTokenMatch = false
        
        lineTokens.forEach(t => {
            // Strict token match
            if (targetSet.has(t)) {
                matchCount++
                if (t.length > 3) hasLongTokenMatch = true
            }
            // Optional: Partial match for very long tokens?
            // else if (t.length > 8 && targetTokens.some(tt => tt.includes(t) || t.includes(tt))) {
            //    matchCount++
            //    hasLongTokenMatch = true
            // }
        })
        
        // 4. Threshold
        if (targetTokens.length === 1) {
            return matchCount >= 1
        }
        
        // Revised Threshold:
        // - At least 2 token matches
        // - OR 1 match if it's a "Significant" token (len > 3) and ratio is decent
        // - OR > 40% overlap
        
        const lineRatio = matchCount / lineTokens.length
        
        return (matchCount >= 2) || 
               (hasLongTokenMatch && matchCount >= 1) ||
               (lineRatio > 0.4 && matchCount >= 1)
        
    }).map(item => item.box)
})

const getBoxStyle = (box) => {
    // box is 4 points: [[x,y], [x,y], [x,y], [x,y]]
    // Get bounds
    const xs = box.map(p => p[0])
    const ys = box.map(p => p[1])
    const xMin = Math.min(...xs)
    const xMax = Math.max(...xs)
    const yMin = Math.min(...ys)
    const yMax = Math.max(...ys)
    
    // Scale
    const scaleX = displaySize.value.width / naturalSize.value.width
    const scaleY = displaySize.value.height / naturalSize.value.height
    
    return {
        left: `${xMin * scaleX}px`,
        top: `${yMin * scaleY}px`,
        width: `${(xMax - xMin) * scaleX}px`,
        height: `${(yMax - yMin) * scaleY}px`
    }
}
</script>
