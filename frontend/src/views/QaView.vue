<template>
  <div class="page">
    <header class="topbar">
      <div class="topbar-left">
        <h1 class="h1">备用功能栏</h1>
        <p class="sub">愿景先行：把学习流程做成真正可持续的工作台</p>
      </div>

      <div class="topbar-right">
        <div class="status-pill" :class="statusTone">
          <span class="status-dot"></span>
          {{ statusText }}
        </div>

        <button class="btn btn-ghost" type="button" @click="simulateProgress">
          更新进度
        </button>
      </div>
    </header>

    <section class="hero">
      <div class="hero-bg" aria-hidden="true"></div>

      <div class="hero-inner floaty hero-enter">
        <div class="hero-left">
          <div class="chip">
            <span class="chip-dot"></span>
            Vision · Roadmap
          </div>

          <div class="hero-head">
            <div class="badge-hero" aria-hidden="true">
              <div class="badge-ring"></div>
              <div class="badge-mark">
                <svg viewBox="0 0 24 24">
                  <path
                    d="M20 12a8 8 0 1 1-2.343-5.657"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                  />
                  <path
                    d="M20 4v6h-6"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
            </div>

            <div class="hero-head-text">
              <h2 class="hero-title">打造一个真正陪你学习的工作台</h2>
              <p class="hero-desc">
                把「记录 → 计划 → 执行 → 复盘」连成闭环
              </p>
            </div>
          </div>

          <div class="tool-dock">
            <div class="dock-row">
              <div class="dock-actions">
                <button class="btn btn-primary" type="button" @click="simulateProgress">
                  Forward
                </button>
                <button class="btn btn-secondary" type="button" @click="resetProgress">
                  Restart
                </button>
              </div>

              <div class="dock-hint">
                当前进度会驱动右侧阶段变化
              </div>
            </div>

            <div class="mini-metrics dock-metrics">
              <div class="mini">
                <div class="mini-k">闭环模块</div>
                <div class="mini-v">4</div>
              </div>
              <div class="mini">
                <div class="mini-k">优先功能</div>
                <div class="mini-v">P0–P2</div>
              </div>
              <div class="mini">
                <div class="mini-k">迭代节奏</div>
                <div class="mini-v">Weekly</div>
              </div>
            </div>
          </div>
        </div>

        <div class="hero-right">
          <div class="glass card-stage glow-breathe">
            <div class="card-label">当前阶段</div>
            <div class="card-value">{{ stageLabel }}</div>
            <div class="card-sub">根据进度自动切换</div>

            <div class="stage-steps">
              <div class="step" :class="{ on: progress >= 0 }">
                <span class="step-dot"></span> 规划
              </div>
              <div class="step" :class="{ on: progress >= 15 }">
                <span class="step-dot"></span> 开发
              </div>
              <div class="step" :class="{ on: progress >= 70 }">
                <span class="step-dot"></span> 收尾
              </div>
              <div class="step" :class="{ on: progress >= 100 }">
                <span class="step-dot"></span> 发布
              </div>
            </div>
          </div>

          <div class="glass card-progress">
            <div class="progress-top">
              <div>
                <div class="card-label">完成度</div>
                <div class="card-value mono">{{ progress }}%</div>
              </div>
              <div class="progress-meta mono">{{ progress }} / 100</div>
            </div>

            <div
              class="progress-bar"
              role="progressbar"
              :aria-valuenow="progress"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div class="progress-fill" :style="{ width: progress + '%' }"></div>
            </div>

            <div class="card-sub">
              正在开发...
            </div>

            <div class="sparkline" aria-hidden="true">
              <span v-for="n in 18" :key="n" class="spark"></span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="card section">
      <div class="section-head">
        <div>
          <div class="section-title">即将推出</div>
          <div class="section-sub">这些功能会围绕闭环逐步接入</div>
        </div>
        <div class="section-actions">
          <div class="hint-pill">Roadmap · Beta</div>
        </div>
      </div>

      <div class="features">
        <div
          v-for="(item, idx) in features"
          :key="idx"
          class="feature-row floaty-soft"
          :style="{ animationDelay: (idx * 90) + 'ms' }"
        >
          <div class="left">
            <div class="priority" :class="item.priority">
              <span class="p-dot"></span>
            </div>

            <div class="meta">
              <div class="name">
                {{ item.title }}
                <span class="tag" :class="item.tagTone">{{ item.tag }}</span>
              </div>
              <div class="desc">{{ item.desc }}</div>
            </div>
          </div>

          <div class="right">
            <div class="eta mono">{{ item.eta }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="card note">
      <div class="note-left">
        <div class="note-title">你希望优先上线哪个功能？</div>
        <div class="note-sub">可以把需求写进Issue，我们会据此调整迭代顺序。</div>
      </div>
    </section>

    <div v-if="message" class="toast" :class="messageType">{{ message }}</div>
  </div>
</template>

<script>
export default {
  name: 'QaView',
  data() {
    return {
      progress: 0,
      message: '',
      messageType: 'info',
      features: [
        { title: '学习笔记管理', desc: '结构化笔记、标签、全文检索与关联。', priority: 'p0', tag: 'P0', tagTone: 'tag-strong', eta: 'Soon' },
        { title: '学习计划制定', desc: '目标拆解、提醒、番茄钟与习惯化。', priority: 'p1', tag: 'P1', tagTone: 'tag-mid', eta: 'Next' },
        { title: '学习进度跟踪', desc: '里程碑、统计面板、趋势与复盘。', priority: 'p1', tag: 'P1', tagTone: 'tag-mid', eta: 'Next' },
        { title: '学习小组协作', desc: '共享任务、讨论串、评论与权限。', priority: 'p2', tag: 'P2', tagTone: 'tag-soft', eta: 'Later' },
        { title: '学习资源推荐', desc: '围绕主题自动聚合与推荐高质量资源。', priority: 'p2', tag: 'P2', tagTone: 'tag-soft', eta: 'Later' }
      ]
    }
  },
  computed: {
    stageLabel() {
      const p = this.progress
      if (p < 15) return '规划中'
      if (p < 70) return '开发中'
      if (p < 100) return '收尾中'
      return '已发布'
    },
    statusText() {
      return this.stageLabel
    },
    statusTone() {
      const p = this.progress
      if (p < 15) return 'tone-muted'
      if (p < 70) return 'tone-blue'
      if (p < 100) return 'tone-amber'
      return 'tone-green'
    }
  },
  methods: {
    simulateProgress() {
      const next = this.progress >= 100 ? 0 : Math.min(100, this.progress + 12)
      this.progress = next
      this.toast(`进度更新：${this.progress}%`, 'success')
    },
    resetProgress() {
      this.progress = 0
      this.toast('已重置进度', 'info')
    },
    toast(msg, type = 'info') {
      this.message = msg
      this.messageType = type
      clearTimeout(this._t)
      this._t = setTimeout(() => {
        this.message = ''
        this.messageType = 'info'
      }, 2200)
    }
  }
}
</script>

<style scoped>
.page{
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px 44px;
  color:#0f172a;
}

.topbar{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  padding: 16px 16px;
  border-radius: 16px;
  border: 1px solid rgba(226,232,240,0.9);
  background:
    radial-gradient(1000px 420px at 70% 0%, rgba(37,99,235,0.14), rgba(37,99,235,0) 60%),
    linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,252,0.92));
  box-shadow: 0 12px 34px rgba(15,23,42,0.06);
}

.topbar-left{ min-width:0; }
.h1{ margin:0; font-size:20px; font-weight:950; letter-spacing:.2px; }
.sub{ margin:6px 0 0; font-size:13px; color: rgba(100,116,139,1); line-height:1.55; }

.topbar-right{
  display:flex;
  align-items:center;
  gap:10px;
  flex-wrap: wrap;
}

.status-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.72);
  font-size: 12px;
  font-weight: 900;
  color:#0f172a;
  box-shadow: 0 14px 30px rgba(15,23,42,0.06);
  backdrop-filter: blur(10px);
}

.status-dot{
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148,163,184,0.18);
}

.tone-muted .status-dot{ background:#94a3b8; box-shadow:0 0 0 3px rgba(148,163,184,0.18); }
.tone-blue  .status-dot{ background:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,0.16); }
.tone-amber .status-dot{ background:#f59e0b; box-shadow:0 0 0 3px rgba(245,158,11,0.16); }
.tone-green .status-dot{ background:#10b981; box-shadow:0 0 0 3px rgba(16,185,129,0.16); }

.hero{
  margin-top: 14px;
  position: relative;
}

.hero-bg{
  position:absolute;
  inset:0;
  pointer-events:none;
  border-radius: 18px;
  background:
    radial-gradient(900px 420px at 18% 10%, rgba(37,99,235,0.22), rgba(37,99,235,0) 55%),
    radial-gradient(900px 420px at 80% 0%, rgba(16,185,129,0.14), rgba(16,185,129,0) 55%),
    radial-gradient(700px 360px at 60% 80%, rgba(168,85,247,0.12), rgba(168,85,247,0) 60%);
  filter: blur(1px);
}

.hero-inner{
  border-radius: 18px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.82);
  box-shadow: 0 18px 50px rgba(15,23,42,0.08);
  overflow:hidden;
  position: relative;
  display:grid;
  grid-template-columns: 1.12fr 0.88fr;
  gap: 16px;
  padding: 20px;
}

.hero-inner::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background-image:
    linear-gradient(to right, rgba(15,23,42,0.04) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(15,23,42,0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  opacity: .14;
}

@media (max-width: 980px){
  .hero-inner{ grid-template-columns: 1fr; }
}

.hero-left{
  position: relative;
  z-index: 1;
  padding: 6px 6px 10px;
}

.chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(248,250,252,0.85);
  font-size: 12px;
  font-weight: 950;
  color:#0f172a;
}

.chip-dot{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background:#111827;
  box-shadow: 0 0 0 3px rgba(17,24,39,0.12);
}

.hero-head{
  margin-top: 14px;
  display:flex;
  gap: 16px;
  align-items:flex-start;
  flex-wrap: wrap;
}

.hero-head-text{
  min-width: 260px;
  flex: 1;
}

.hero-title{
  margin: 0;
  font-size: 28px;
  font-weight: 980;
  letter-spacing: -0.4px;
  line-height: 1.12;
}

.hero-desc{
  margin-top: 12px;
  font-size: 14px;
  color: rgba(100,116,139,1);
  line-height: 1.75;
  max-width: 64ch;
}

.hero-right{
  position: relative;
  z-index: 1;
  display:flex;
  flex-direction: column;
  gap: 12px;
}

.glass{
  border-radius: 16px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.74);
  box-shadow: 0 16px 42px rgba(15,23,42,0.08);
  backdrop-filter: blur(12px);
  padding: 14px 14px;
}

.card-label{
  font-size: 12px;
  color: rgba(100,116,139,1);
  font-weight: 900;
}

.card-value{
  margin-top: 8px;
  font-size: 18px;
  font-weight: 980;
  color:#0f172a;
}

.card-sub{
  margin-top: 8px;
  font-size: 12px;
  color: rgba(100,116,139,1);
  line-height: 1.55;
}

.stage-steps{
  margin-top: 12px;
  display:flex;
  flex-wrap: wrap;
  gap: 8px;
}

.step{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  font-size: 12px;
  font-weight: 900;
  color: rgba(100,116,139,1);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(248,250,252,0.85);
}

.step-dot{
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background:#cbd5e1;
  box-shadow: 0 0 0 3px rgba(203,213,225,0.18);
}

.step.on{
  color:#0f172a;
  border-color: rgba(37,99,235,0.20);
  background: rgba(37,99,235,0.06);
}
.step.on .step-dot{
  background:#2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.16);
}

.progress-top{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap: 10px;
}
.progress-meta{
  font-size: 12px;
  color: rgba(100,116,139,1);
  padding-top: 2px;
}

.progress-bar{
  margin-top: 12px;
  height: 10px;
  border-radius: 999px;
  background: rgba(226,232,240,0.72);
  overflow:hidden;
  border: 1px solid rgba(226,232,240,0.9);
}

.progress-fill{
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #111827, #2563eb);
  transition: width 420ms ease;
}

.sparkline{
  margin-top: 12px;
  display:flex;
  gap: 4px;
  align-items:flex-end;
  height: 22px;
}
.spark{
  width: 6px;
  border-radius: 999px;
  background: rgba(15,23,42,0.12);
  animation: spark 1.8s ease-in-out infinite;
}
.spark:nth-child(3n){ animation-delay: .12s; }
.spark:nth-child(4n){ animation-delay: .22s; }
.spark:nth-child(5n){ animation-delay: .32s; }

@keyframes spark{
  0%{ height: 8px; opacity: .55; }
  50%{ height: 22px; opacity: .95; }
  100%{ height: 10px; opacity: .6; }
}

.glow-breathe{
  position: relative;
}
.glow-breathe::after{
  content:"";
  position:absolute;
  inset:-18px;
  background: radial-gradient(circle at 30% 30%, rgba(37,99,235,0.18), rgba(37,99,235,0) 60%);
  border-radius: 22px;
  filter: blur(8px);
  opacity: .75;
  pointer-events:none;
  animation: breathe 2.4s ease-in-out infinite;
}
.glow-breathe::after{
  content: none !important;
  display: none !important;
}
.glass{
  backdrop-filter: none;
  background: rgba(255,255,255,0.86);
}

@keyframes breathe{
  0%{ transform: scale(0.98); opacity: .55; }
  50%{ transform: scale(1.04); opacity: .9; }
  100%{ transform: scale(0.98); opacity: .55; }
}

.tool-dock{
  margin-top: 16px;
  padding: 14px 14px;
  border-radius: 16px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.76);
  box-shadow: 0 12px 30px rgba(15,23,42,0.06);
  backdrop-filter: blur(10px);
}

.dock-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.dock-actions{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}

.dock-hint{
  font-size: 12px;
  font-weight: 800;
  color: rgba(100,116,139,1);
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px dashed rgba(226,232,240,0.95);
  background: rgba(248,250,252,0.65);
}

.mini-metrics{
  margin-top: 12px;
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}

.mini{
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.78);
  min-width: 160px;
}

.mini-k{
  font-size: 12px;
  color: rgba(100,116,139,1);
  font-weight: 800;
}

.mini-v{
  margin-top: 6px;
  font-size: 14px;
  font-weight: 980;
  color:#0f172a;
}

.card{
  background: rgba(255,255,255,0.90);
  border: 1px solid rgba(226,232,240,0.9);
  border-radius: 16px;
  box-shadow: 0 12px 34px rgba(15,23,42,0.06);
  overflow:hidden;
}

.section{
  margin-top: 14px;
}

.section-head{
  padding: 14px 14px;
  display:flex;
  justify-content:space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(226,232,240,0.9);
  background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,252,0.92));
}

.section-title{
  font-size: 13px;
  font-weight: 980;
}
.section-sub{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(100,116,139,1);
}

.hint-pill{
  font-size: 12px;
  font-weight: 900;
  color: rgba(100,116,139,1);
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.7);
}

.features{
  padding: 12px 12px 14px;
  display:flex;
  flex-direction: column;
  gap: 10px;
}
.feature-row{
  display:flex;
  justify-content:space-between;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 14px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.88);
  transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}
.feature-row:hover{
  transform: translateY(-2px);
  border-color: rgba(37,99,235,0.22);
  box-shadow: 0 18px 36px rgba(37,99,235,0.10);
}

.left{ display:flex; gap:12px; min-width:0; }
.meta{ min-width:0; }
.name{
  font-size: 13px;
  font-weight: 980;
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap: wrap;
}
.desc{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(100,116,139,1);
  line-height: 1.55;
}
.right{
  display:flex;
  align-items:center;
  justify-content:flex-end;
  padding-top: 2px;
}
.eta{
  font-size: 12px;
  color: rgba(100,116,139,1);
}

.priority{
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(248,250,252,0.92);
  display:grid;
  place-items:center;
  flex: 0 0 auto;
}
.p-dot{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148,163,184,0.16);
}
.p0 .p-dot{ background:#ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.14); }
.p1 .p-dot{ background:#2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.14); }
.p2 .p-dot{ background:#10b981; box-shadow: 0 0 0 3px rgba(16,185,129,0.14); }

.tag{
  font-size: 11px;
  font-weight: 980;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.9);
}
.tag-strong{ background: rgba(239,68,68,0.08); color:#b91c1c; border-color: rgba(239,68,68,0.18); }
.tag-mid{ background: rgba(37,99,235,0.08); color:#1d4ed8; border-color: rgba(37,99,235,0.18); }
.tag-soft{ background: rgba(16,185,129,0.08); color:#065f46; border-color: rgba(16,185,129,0.18); }

.note{
  margin-top: 14px;
  padding: 14px 14px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap: 12px;
  flex-wrap: wrap;
}
.note-title{ font-size: 13px; font-weight: 980; }
.note-sub{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(100,116,139,1);
  line-height: 1.55;
}

.btn{
  height: 38px;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 950;
  border: 1px solid transparent;
  cursor:pointer;
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease, border-color .12s ease;
  user-select:none;
}
.btn:active{ transform: translateY(1px); }

.btn-primary{
  background:#111827;
  color:#fff;
  box-shadow: 0 12px 28px rgba(17,24,39,0.16);
}
.btn-primary:hover{ background:#0f172a; }

.btn-secondary{
  background: rgba(248,250,252,0.92);
  border-color: rgba(226,232,240,0.95);
  color:#0f172a;
  border: 1px solid rgba(226,232,240,0.95);
}
.btn-secondary:hover{ background: rgba(241,245,249,0.95); }

.btn-ghost{
  background: transparent;
  border-color: rgba(226,232,240,0.95);
  color:#0f172a;
  border: 1px solid rgba(226,232,240,0.95);
}
.btn-ghost:hover{ background: rgba(248,250,252,0.95); }

.mono{
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.floaty{ animation: floatY 2.8s ease-in-out infinite; }
.floaty-soft{ animation: floatYSoft 3.2s ease-in-out infinite; }

@keyframes floatY{
  0%{ transform: translateY(0); }
  50%{ transform: translateY(-5px); }
  100%{ transform: translateY(0); }
}
@keyframes floatYSoft{
  0%{ transform: translateY(0); }
  50%{ transform: translateY(-3px); }
  100%{ transform: translateY(0); }
}

.toast{
  position: fixed;
  right: 18px;
  bottom: 18px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.92);
  box-shadow: 0 22px 60px rgba(15,23,42,0.14);
  font-size: 13px;
  font-weight: 900;
  color:#0f172a;
  z-index: 9999;
  backdrop-filter: blur(10px);
}
.toast.success{ border-color: rgba(16,185,129,0.22); }
.toast.info{ border-color: rgba(37,99,235,0.18); }

.badge-hero{
  width: 92px;
  height: 92px;
  border-radius: 24px;
  border: 1px solid rgba(226,232,240,0.9);
  background: rgba(255,255,255,0.78);
  box-shadow: 0 18px 46px rgba(15,23,42,0.10);
  display:grid;
  place-items:center;
  position: relative;
  flex: 0 0 auto;
}

.badge-ring{
  position:absolute;
  inset: -14px;
  border-radius: 30px;
  background: radial-gradient(circle at 50% 50%, rgba(37,99,235,0.22), rgba(37,99,235,0) 60%);
  filter: blur(2px);
  opacity: .9;
  pointer-events:none;
  animation: ringPulse 2.0s ease-in-out infinite;
}

.badge-mark{
  width: 60px;
  height: 60px;
  border-radius: 20px;
  background:#111827;
  color:#fff;
  display:grid;
  place-items:center;
  box-shadow: 0 14px 34px rgba(17,24,39,0.20);
  position: relative;
  z-index: 1;
}

.badge-mark svg{
  width: 34px;
  height: 34px;
}

@keyframes ringPulse{
  0%{ transform: scale(0.98); opacity: .60; }
  50%{ transform: scale(1.04); opacity: 1; }
  100%{ transform: scale(0.98); opacity: .60; }
}

.hero-enter{
  opacity: 0;
  transform: translateY(10px);
  animation: enterUp 520ms cubic-bezier(.21,.9,.25,1) 120ms forwards;
}

@keyframes enterUp{
  to{
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce){
  .hero-enter{ animation: none; opacity: 1; transform: none; }
  .floaty, .floaty-soft{ animation: none !important; }
  .badge-ring{ animation: none !important; }
  .glow-breathe::after{ animation: none !important; }
  .spark{ animation: none !important; }
}

@media (max-width: 720px){
  .badge-hero{ width: 82px; height: 82px; }
  .badge-mark{ width: 54px; height: 54px; border-radius: 18px; }
  .badge-mark svg{ width: 30px; height: 30px; }
  .dock-hint{ width: 100%; }
  .mini{ min-width: 0; flex: 1; }
}


</style>
