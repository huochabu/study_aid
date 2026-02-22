<template>
  <div class="command-center min-h-[calc(100vh-4rem)] bg-black text-cyan-400 font-mono overflow-hidden relative">
    <!-- Background Grid Effect -->
    <div class="absolute inset-0 grid-bg opacity-20 pointer-events-none"></div>
    
    <!-- Top HUD Bar -->
    <div class="relative z-10 flex justify-between items-center p-4 border-b border-cyan-900/50 bg-black/80 backdrop-blur-sm">
      <div class="flex items-center gap-4">
         <div class="w-3 h-3 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_#ef4444]"></div>
         <h1 class="text-2xl font-bold tracking-[0.2em] text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 uppercase">
            AI Neural Command
         </h1>
      </div>
      <div class="flex gap-8 text-xs tracking-widest text-cyan-600">
         <div>SYS.STATUS: <span class="text-green-400">ONLINE</span></div>
         <div>CPU.LOAD: <span class="text-yellow-400">{{ cpuLoad }}%</span></div>
         <div>NET.LATENCY: <span class="text-cyan-400">{{ latency }}ms</span></div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="relative z-10 grid grid-cols-12 gap-4 p-4 h-[calc(100vh-9rem)]">
        
        <!-- Left: Agent Status Nodes (Holographic View) -->
        <div class="col-span-8 flex flex-col gap-4">
            <!-- Active Agents Visualization -->
            <div class="flex-1 border border-cyan-900/30 rounded-lg bg-zinc-900/20 backdrop-blur relative overflow-hidden group">
                <div class="absolute top-2 left-2 text-xs text-cyan-700 font-bold tracking-widest">[ VISUALIZER.V2 ]</div>
                
                <!-- Central Hub Animation -->
                <div class="absolute inset-0 flex items-center justify-center">
                    <div class="relative w-[500px] h-[500px]">
                        <!-- Connecting Lines (SVG) -->
                        <svg class="absolute inset-0 w-full h-full pointer-events-none">
                            <line v-for="(agent, idx) in activeAgents" :key="'line-'+idx"
                                x1="50%" y1="50%"
                                :x2="getAgentPos(idx, activeAgents.length).x"
                                :y2="getAgentPos(idx, activeAgents.length).y"
                                :stroke="agent.active ? '#22d3ee' : '#164e63'"
                                stroke-width="2"
                                :class="agent.active ? 'animate-pulse-fast' : ''"
                            />
                        </svg>

                        <!-- Central Core -->
                        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 rounded-full border-4 border-cyan-500/50 flex items-center justify-center shadow-[0_0_50px_#06b6d4] animate-spin-slow bg-black/50 z-20">
                            <div class="w-16 h-16 rounded-full bg-cyan-500/20 animate-pulse"></div>
                        </div>

                        <!-- Orbiting Agents -->
                        <div v-for="(agent, idx) in activeAgents" :key="agent.name"
                            class="absolute transition-all duration-1000 ease-in-out z-30"
                            :style="{
                                left: getAgentPos(idx, activeAgents.length).x, 
                                top: getAgentPos(idx, activeAgents.length).y,
                                transform: 'translate(-50%, -50%)'
                            }"
                        >
                            <div class="flex flex-col items-center gap-2 group">
                                <div class="w-16 h-16 rounded-lg border-2 flex items-center justify-center bg-black/80 transition-all duration-300 relative"
                                    :class="agent.active ? 'border-cyan-400 shadow-[0_0_30px_#22d3ee] scale-110' : 'border-cyan-900/50 opacity-60'">
                                    
                                    <!-- Scanning Effect -->
                                    <div v-if="agent.active" class="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-400/20 to-transparent animate-scan"></div>
                                    
                                    <component :is="agent.icon" :size="24" :class="agent.active ? 'text-cyan-400' : 'text-cyan-900'" />
                                </div>
                                <div class="px-3 py-1 bg-black/90 border border-cyan-900 text-[10px] tracking-wider uppercase rounded text-cyan-300">
                                    {{ agent.name }}
                                </div>
                                <div v-if="agent.active" class="text-[9px] text-yellow-400 animate-bounce">PROCESSING...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- System Metrics Graphs (Mockup) -->
            <div class="h-32 grid grid-cols-3 gap-4">
                <div v-for="i in 3" :key="i" class="border border-cyan-900/30 bg-zinc-900/30 rounded p-2 flex flex-col justify-end relative overflow-hidden">
                    <div class="absolute inset-x-0 bottom-0 h-full opacity-20 flex items-end gap-1">
                        <div v-for="j in 20" :key="j" 
                             class="flex-1 bg-cyan-500 transition-all duration-300"
                             :style="{ height: Math.random() * 100 + '%' }">
                        </div>
                    </div>
                    <div class="text-xs text-cyan-600 font-bold z-10">CORE_{{ i }} ACTIVITY</div>
                </div>
            </div>
        </div>

        <!-- Right: "The Matrix" Log Stream -->
        <div class="col-span-4 border border-cyan-900/30 bg-black/90 rounded-lg p-0 flex flex-col font-mono text-xs overflow-hidden shadow-[0_0_20px_rgba(8,145,178,0.1)]">
            <div class="p-2 border-b border-cyan-900/50 bg-cyan-900/10 flex justify-between items-center">
                <span class="font-bold text-cyan-400">> SYSTEM_LOGS</span>
                <div class="w-2 h-2 rounded-full bg-green-500 animate-ping"></div>
            </div>
            <div class="flex-1 overflow-auto p-4 space-y-2 scrollbar-hide" ref="logContainer">
                <div v-for="(log, i) in displayedLogs" :key="i" 
                     class="border-l-2 pl-2 transition-all duration-500 animate-slide-in"
                     :class="getLogColor(log.type)">
                    <div class="opacity-50 text-[10px] mb-0.5">{{ log.time }} [{{ log.source }}]</div>
                    <div class="typing-effect">{{ log.msg }}</div>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Cpu, Database, Search, Shield, Zap, Terminal } from 'lucide-vue-next'
import { v4 as uuidv4 } from 'uuid'

// --- Mock Data & Websocket Simulation ---
const cpuLoad = ref(12)
const latency = ref(45)

const activeAgents = ref([
    { name: 'Log Expert', icon: Terminal, active: false, role: 'log' },
    { name: 'Knowledge', icon: Database, active: false, role: 'rag' },
    { name: 'Search', icon: Search, active: false, role: 'web' },
    { name: 'Critic', icon: Shield, active: false, role: 'review' },
    { name: 'Explainer', icon: Cpu, active: false, role: 'summary' },
])

const logs = ref([])
const displayedLogs = ref([])
const logContainer = ref(null)

const getAgentPos = (index, total) => {
    const radius = 200 // px
    const angle = (index / total) * 2 * Math.PI - (Math.PI / 2)
    // Return CSS percentage strings is hard for SVG lines logic mix.
    // Let's use simple center offset calculations assuming 500x500 box
    const centerX = "50%"
    const centerY = "50%"
    // Calculate percentage offset
    const x = 50 + (Math.cos(angle) * 35) + '%' 
    const y = 50 + (Math.sin(angle) * 35) + '%'
    return { x, y }
}

const getLogColor = (type) => {
    switch(type) {
        case 'error': return 'border-red-500 text-red-400'
        case 'success': return 'border-green-500 text-green-400'
        case 'warning': return 'border-yellow-500 text-yellow-400'
        default: return 'border-cyan-500 text-cyan-300'
    }
}

// --- WebSocket Connection ---
let socket = null

const connectWebSocket = () => {
    const clientId = uuidv4()
    socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`)

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data)
            handleSystemEvent(data)
        } catch (e) {
            console.error("WS Parse Error", e)
        }
    }
}

const handleSystemEvent = (data) => {
    // 1. Add Log
    const logItem = {
        time: new Date().toLocaleTimeString(),
        source: data.name || 'SYSTEM',
        type: data.type === 'error' ? 'error' : 'info',
        msg: typeof data.content === 'string' ? data.content : JSON.stringify(data)
    }
    addLog(logItem)

    // 2. Activate Agent visuals
    if (data.name) {
        // Find matching agent (fuzzy match)
        const target = activeAgents.value.find(a => 
            data.name.includes(a.name) || 
            (a.name === 'Log Expert' && data.name.includes('日志')) ||
            (a.name === 'Critic' && data.name.includes('质检')) ||
            (a.name === 'Explainer' && data.name.includes('解释')) ||
            (a.name === 'Knowledge' && data.name.includes('知识')) 
        )
        
        if (target) {
            triggerAgentActivity(target)
        }
    }
}

const triggerAgentActivity = (agent) => {
    agent.active = true
    setTimeout(() => { agent.active = false }, 1500)
}

const addLog = (log) => {
    displayedLogs.value.unshift(log)
    if (displayedLogs.value.length > 50) displayedLogs.value.pop()
}

// --- Demo Mode (Auto-run if no real data) ---
let demoInterval = null
const runDemo = () => {
    const demoMsgs = [
        "Analyzing packet headers...",
        "Anomaly detected in sector 7...",
        "Knowledge graph updated: +5 nodes...",
        "Retrieving archival records...",
        "Optimizing neural weights...",
        "Cross-referencing entities..."
    ]
    
    demoInterval = setInterval(() => {
        // Random CPU flux
        cpuLoad.value = Math.floor(Math.random() * 30) + 10
        
        // Random Log
        if (Math.random() > 0.5) {
            const agent = activeAgents.value[Math.floor(Math.random() * activeAgents.value.length)]
            triggerAgentActivity(agent)
            addLog({
                time: new Date().toLocaleTimeString(),
                source: agent.name.toUpperCase(),
                type: 'info',
                msg: demoMsgs[Math.floor(Math.random() * demoMsgs.length)]
            })
        }
    }, 2000)
}

onMounted(() => {
    connectWebSocket()
    // Always run demo for visual effect, real data will interleave
    runDemo()
})

onUnmounted(() => {
    if (socket) socket.close()
    if (demoInterval) clearInterval(demoInterval)
})
</script>

<style scoped>
.grid-bg {
    background-image: 
        linear-gradient(rgba(6,182,212,0.1) 1px, transparent 1px),
        linear-gradient(90deg, rgba(6,182,212,0.1) 1px, transparent 1px);
    background-size: 40px 40px;
}

.animate-spin-slow {
    animation: spin 10s linear infinite;
}

.animate-pulse-fast {
    animation: pulse 0.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes scan {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}

.animate-scan {
    animation: scan 2s linear infinite;
}

.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
</style>
