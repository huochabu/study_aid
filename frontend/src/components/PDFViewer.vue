<template>
  <div class="pdf-viewer-container relative w-full h-full bg-zinc-50 overflow-auto border rounded-xl" ref="container">
    <div v-if="loading" class="flex items-center justify-center h-full">
      <Loader2 class="animate-spin text-zinc-400" />
    </div>

    <!-- PDF Viewer wrap -->
    <div v-if="source" class="relative mx-auto" :style="{ maxWidth: '100%' }" ref="pagesWrapper">
       <vue-pdf-embed
          ref="pdfEmbed"
          :source="source"
          class="shadow-sm"
          @loaded="handleLoaded"
        />
        
        <!-- Highlights Layer -->
        <template v-for="(pageData, pageIndex) in highlightsByPage" :key="pageIndex">
            <div 
                v-for="(box, i) in pageData.matches" 
                :key="i"
                class="absolute bg-yellow-300/40 rounded-sm pointer-events-none z-10"
                :style="getHighlightStyle(box, pageIndex)"
            ></div>
        </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import { Loader2 } from 'lucide-vue-next'

const props = defineProps({
  source: String,
  layoutData: { type: Array, default: () => [] },
  highlightText: String
})

const container = ref(null)
const pagesWrapper = ref(null)
const loading = ref(true)
const pageElements = ref({}) // { 1: HTMLElement, ... }

const handleLoaded = () => {
    loading.value = false
    nextTick(() => {
        updatePageElements()
        scrollToFirstHighlight()
    })
}

// Keep track of page DOM elements
const updatePageElements = () => {
    const pages = container.value?.querySelectorAll('.vue-pdf-embed__page')
    if(pages) {
        pages.forEach((el, index) => {
            pageElements.value[index + 1] = el
        })
    }
}

// Compute highlights grouped by page
const highlightsByPage = computed(() => {
    if (!props.highlightText || !props.layoutData.length) return {}
    
    // ROBUST CHARACTER-STREAM MATCHING
    if (!props.highlightText) return {}
    
    // Clean target: remove all whitespace and punctuation, lowercase
    const targetClean = props.highlightText.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')
    if (targetClean.length < 2) return {} // Allow short matches if precise (e.g. ID)
    
    console.log("[PDFViewer] Target Sig:", targetClean.slice(0, 50) + "...")

    const result = {} 
    
    props.layoutData.forEach(page => {
        const pIndex = page.page
        const pWidth = page.width || 595.28 
        const pHeight = page.height || 841.89
        
        if (!page.words || page.words.length === 0) return

        // TOKEN SEQUENCE STRATEGY
        // Break both into word tokens. Find meaningful sequences of matches.
        
        // 1. Tokenize Target
        // FILTERING STRATEGY: 
        // We MUST apply the exact same filter to both Target and Page tokens.
        
        // Stop words list to reduce noise (common academic/english words)
        const STOP_WORDS = new Set([
            'the', 'and', 'for', 'with', 'that', 'this', 'but', 'not', 'can', 'are', 'was', 'all', 'one', 'has', 'its', 'use', 'two', 
            'from', 'which', 'their', 'what', 'top', 'bottom', 'left', 'right', 'table', 'figure', 'fig', 'section',
            'definition', 'notation', 'value', 'mean', 'std', 'min', 'max', 'summary', 'total', 'average'
        ])
        
        // Stricter filter: Ignore 1-2 char words AND stop words
        const filterToken = (t) => t.length > 2 && !STOP_WORDS.has(t)
        
        // Custom splitter that handles punctuation inside words
        const splitRegex = /[\s,.\-_:;()\[\]"'/]+/
        
        const targetTokens = props.highlightText.toLowerCase()
            .split(splitRegex) 
            .map(t => t.replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')) 
            .filter(t => t.length > 0 && filterToken(t))
            
        if (targetTokens.length === 0) return

        // 2. Tokenize Page Words with Map
        const pageTokens = [] // { token, box }
        
        for (let i = 0; i < page.words.length; i++) {
            const w = page.words[i]
            const text = w.text
            
            // HYPHENATION HANDLING:
            // Check if this word ends in hyphen and next word exists
            if (text.endsWith('-') && i + 1 < page.words.length) {
                const nextW = page.words[i+1]
                // Try merging: "detec-" + "tion" -> "detection"
                const mergedText = text.slice(0, -1) + nextW.text
                const mergedClean = mergedText.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')
                
                // If merged word is in target (or distinct enough), add it as a virtual token
                // We add it to the stream.
                // Note: We might also want to process the individual parts? 
                // Usually "detection" is what we want.
                // But let's check if 'mergedClean' passes filter
                if (mergedClean.length > 0 && filterToken(mergedClean)) {
                     // Add virtual token representing BOTH boxes
                     // We use a composite box? Or just add two entries?
                     // Algorithm expects one box.
                     // Let's create a "Virtual Box" that spans both? 
                     // No, highlighting needs individual rects.
                     // The "matches" array stores BOXES.
                     // If we match this token, we should highlight BOTH w and nextW.
                     // So we push a special object?
                     // Or, we push the token twice? Once for each box?
                     // No, sequence matching checks `token`.
                     
                     // Solution: Push the merged token, but attach *multiple* boxes to it.
                     // The matcher needs to handle multi-box items?
                     // Current matcher: `rawMatches.push(pageTokens[pi].box)`
                     // So we can attach `boxes: [w, nextW]` to the token object.
                     // And update matcher to push ALL boxes.
                     
                     pageTokens.push({ 
                        token: mergedClean, 
                        boxes: [w, nextW], // Special property
                        isHyphenated: true 
                     })
                     
                     // Skip next word since we consumed it?
                     // Yes, usually.
                     i++ 
                     continue
                }
            }
            
            // Standard processing
            const subTokens = text.toLowerCase().split(splitRegex)
            subTokens.forEach(sub => {
                const clean = sub.replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')
                 if (clean.length > 0 && filterToken(clean)) {
                     pageTokens.push({ token: clean, box: w })
                 }
            })
        }
        
        if (pageTokens.length === 0) return

        // 3. Find Matches (Longest Common Substring on Tokens)
        // Optimization: Pre-index target tokens for O(1) lookup
        const targetIndexMap = new Map()
        targetTokens.forEach((t, i) => {
            if (!targetIndexMap.has(t)) targetIndexMap.set(t, [])
            targetIndexMap.get(t).push(i)
        })
        
        // DYNAMIC THRESHOLD:
        // Use stricter threshold for long queries to avoid accidental matches
        let minSeqLen = 2
        // If target is long paragraph (>20 major tokens), require 4 matches
        if (targetTokens.length > 20) minSeqLen = 4
        // If medium (10-20), require 3
        else if (targetTokens.length > 8) minSeqLen = 3
        
        console.log(`[PDFViewer] Target Tokens: ${targetTokens.length}, Threshold: ${minSeqLen}`)
        
        const usedPageIndices = new Set()
        const rawMatches = [] // boxes
        
        for (let i = 0; i < pageTokens.length; i++) {
            if (usedPageIndices.has(i)) continue
            
            const pToken = pageTokens[i].token
            // Fast lookup
            const startIndices = targetIndexMap.get(pToken)
            
            if (!startIndices) continue
            
            let bestRun = 0
            
            // In dense text, a word might appear many times in target (e.g. "the").
            startIndices.forEach(tIdx => {
                let ran = 0
                // Look ahead
                while (
                    (i + ran) < pageTokens.length && 
                    (tIdx + ran) < targetTokens.length && 
                    pageTokens[i + ran].token === targetTokens[tIdx + ran]
                ) {
                    ran++
                }
                if (ran > bestRun) bestRun = ran
            })
            
            if (bestRun >= minSeqLen) {
                // Record match
                for (let k = 0; k < bestRun; k++) {
                    const pi = i + k
                    if (!usedPageIndices.has(pi)) {
                        usedPageIndices.add(pi)
                        
                        // Handle potential multi-box token (hyphenated)
                        const item = pageTokens[pi]
                        if (item.boxes) {
                            item.boxes.forEach(b => rawMatches.push(b))
                        } else {
                            rawMatches.push(item.box)
                        }
                    }
                }
            }
        }
        
        // 4. Merge Rectangles to clean up "Messy" highlights
        // Merge boxes that are on the same line and close to each other
        const mergedMatches = mergeHighlightBoxes(rawMatches)
            
        if (mergedMatches.length > 0) {
            console.log(`[PDFViewer] Page ${pIndex}: Found matches, merged into ${mergedMatches.length} ranges`)
            result[pIndex] = {
                matches: mergedMatches,
                originalWidth: pWidth,
                originalHeight: pHeight
            }
        }
    })
    
    return result
})

function mergeHighlightBoxes(boxes) {
    if (!boxes.length) return []
    // 1. Sort by Y (top), then X (left)
    // Approximate Y sort (cache locality)
    boxes.sort((a, b) => {
        if (Math.abs(a.top - b.top) > 5) return a.top - b.top
        return a.x0 - b.x0
    })
    
    const merged = []
    let current = { ...boxes[0] }
    
    for (let i = 1; i < boxes.length; i++) {
        const next = boxes[i]
        
        // Check if on same line (vertical overlap / similar top)
        const isSameLine = Math.abs(current.top - next.top) < 5 && Math.abs(current.bottom - next.bottom) < 5
        
        // Check if horizontally close (within 15px, e.g. space width)
        // Also allow slight negative gap (overlap)
        const isClose = (next.x0 - current.x1) < 15 
        
        if (isSameLine && isClose) {
            // Merge
            current.x1 = Math.max(current.x1, next.x1)
            current.bottom = Math.max(current.bottom, next.bottom) // take max height?
            current.top = Math.min(current.top, next.top)
        } else {
            // Push current, start new
            merged.push(current)
            current = { ...next }
        }
    }
    merged.push(current)
    return merged
}


const getHighlightStyle = (box, pageIndexKey) => {
    const el = pageElements.value[pageIndexKey]
    if (!el) return { display: 'none' }
    
    const wrapperEl = pagesWrapper.value
    if (!wrapperEl) return { display: 'none' }

    const pageData = highlightsByPage.value[pageIndexKey]
    if (!pageData) return { display: 'none' }
    
    // Calculate relative position using getBoundingClientRect for robustness
    const wrapperRect = wrapperEl.getBoundingClientRect()
    const pageRect = el.getBoundingClientRect()
    
    // Relative offset of the page within the wrapper (positioning context)
    const pageLeft = pageRect.left - wrapperRect.left
    const pageTop = pageRect.top - wrapperRect.top
    
    // Calculate Scale
    const clientWidth = el.clientWidth
    const clientHeight = el.clientHeight
    
    const scaleX = clientWidth / pageData.originalWidth
    // const scaleY = clientHeight / pageData.originalHeight 
    // FIX: Use Uniform Scaling based on Width to avoid Aspect Ratio distortion or height misreporting
    const scaleY = scaleX 
    
    // Debug scale discrepancy
    // console.log(`[PDFViewer] Page ${pageIndexKey} Scale: X=${scaleX.toFixed(4)}, Y_raw=${(clientHeight/pageData.originalHeight).toFixed(4)}`)

    // Visual adjustment: Add vertical padding to make it look like a marker pen
    const padY = 2
    
    return {
        left: `${pageLeft + box.x0 * scaleX}px`,
        top: `${pageTop + (box.top * scaleY) - padY}px`,
        width: `${(box.x1 - box.x0) * scaleX}px`,
        height: `${(box.bottom - box.top) * scaleY + (padY*2)}px`
    }
}

const scrollToFirstHighlight = () => {
     const pages = Object.keys(highlightsByPage.value).sort((a,b) => a-b)
     if (pages.length > 0) {
         const firstPage = pages[0]
         const el = pageElements.value[firstPage]
         if (el) {
             console.log("[PDFViewer] Scrolling to page", firstPage)
             el.scrollIntoView({ behavior: 'smooth', block: 'center' })
         }
     } else {
         console.log("[PDFViewer] No highlights found to scroll to.")
     }
}
</script>
