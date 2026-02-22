<template>
  <div class="note-manager">
    <h2 class="text-2xl font-bold mb-6">笔记管理</h2>
    
    <!-- 创建笔记 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
      <h3 class="text-lg font-semibold mb-4">创建新笔记</h3>
      <form @submit.prevent="createNote">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">笔记标题</label>
          <input 
            v-model="newNote.title" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">笔记内容</label>
          <textarea 
            v-model="newNote.content" 
            rows="4" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          ></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">关联模块（可选）</label>
            <select 
              v-model="newNote.module_id" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">无</option>
              <option 
                v-for="module in allModules" 
                :key="module.id" 
                :value="module.id"
              >
                {{ module.title }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">标签（用逗号分隔）</label>
            <input 
              v-model="newNote.tagsInput" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例如：重要, 复习, 难点"
            >
          </div>
        </div>
        <button 
          type="submit" 
          class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          创建笔记
        </button>
      </form>
    </div>
    
    <!-- 笔记列表 -->
    <div class="bg-white rounded-lg shadow-md p-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">我的笔记</h3>
        <div class="flex gap-2">
          <select 
            v-model="filterModule" 
            class="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有模块</option>
            <option 
              v-for="module in allModules" 
              :key="module.id" 
              :value="module.id"
            >
              {{ module.title }}
            </option>
          </select>
          <input 
            v-model="searchKeyword" 
            type="text" 
            placeholder="搜索笔记..." 
            class="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
      </div>
      
      <div v-if="filteredNotes.length === 0" class="text-center py-8 text-gray-500">
        暂无笔记，点击上方按钮创建
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div 
          v-for="note in filteredNotes" 
          :key="note.id" 
          class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <h4 class="text-lg font-medium">{{ note.title }}</h4>
            <div class="flex gap-1">
              <button 
                @click="editNote(note)" 
                class="text-blue-500 hover:text-blue-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <button 
                @click="deleteNote(note.id)" 
                class="text-red-500 hover:text-red-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
          <p class="text-gray-600 text-sm mb-3 line-clamp-3">{{ note.content }}</p>
          
          <!-- 标签 -->
          <div v-if="note.tags && note.tags.length > 0" class="flex flex-wrap gap-1 mb-3">
            <span 
              v-for="tag in note.tags" 
              :key="tag" 
              class="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full"
            >
              {{ tag }}
            </span>
          </div>
          
          <!-- 元信息 -->
          <div class="flex flex-wrap gap-2 text-xs text-gray-500">
            <span v-if="note.module_id">模块: {{ getModuleTitle(note.module_id) }}</span>
            <span>创建: {{ formatDate(note.created_at) }}</span>
            <span>更新: {{ formatDate(note.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 编辑笔记弹窗 -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-semibold">编辑笔记</h3>
          <button @click="showEditModal = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <form @submit.prevent="updateNote">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">笔记标题</label>
            <input 
              v-model="editingNote.title" 
              type="text" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">笔记内容</label>
            <textarea 
              v-model="editingNote.content" 
              rows="4" 
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            ></textarea>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">关联模块（可选）</label>
              <select 
                v-model="editingNote.module_id" 
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">无</option>
                <option 
                  v-for="module in allModules" 
                  :key="module.id" 
                  :value="module.id"
                >
                  {{ module.title }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">标签（用逗号分隔）</label>
              <input 
                v-model="editingNote.tagsInput" 
                type="text" 
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="例如：重要, 复习, 难点"
              >
            </div>
          </div>
          <div class="flex gap-2">
            <button 
              type="submit" 
              class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              保存修改
            </button>
            <button 
              type="button" 
              @click="showEditModal = false" 
              class="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NoteManager',
  data() {
    return {
      notes: [],
      allModules: [],
      newNote: {
        title: '',
        content: '',
        module_id: '',
        tagsInput: ''
      },
      editingNote: {
        id: '',
        title: '',
        content: '',
        module_id: '',
        tagsInput: ''
      },
      showEditModal: false,
      filterModule: '',
      searchKeyword: ''
    }
  },
  computed: {
    filteredNotes() {
      return this.notes.filter(note => {
        // 模块过滤
        if (this.filterModule && note.module_id !== this.filterModule) {
          return false
        }
        // 关键词搜索
        if (this.searchKeyword) {
          const keyword = this.searchKeyword.toLowerCase()
          return note.title.toLowerCase().includes(keyword) || 
                 note.content.toLowerCase().includes(keyword) ||
                 (note.tags && note.tags.some(tag => tag.toLowerCase().includes(keyword)))
        }
        return true
      })
    }
  },
  mounted() {
    this.fetchNotes()
    this.fetchAllModules()
  },
  methods: {
    async fetchNotes() {
      try {
        const response = await fetch('/api/learning/notes')
        if (response.ok) {
          this.notes = await response.json()
        }
      } catch (error) {
        console.error('获取笔记失败:', error)
      }
    },
    
    async fetchAllModules() {
      try {
        // 先获取所有学习计划
        const plansResponse = await fetch('/api/learning/plans')
        if (plansResponse.ok) {
          const plans = await plansResponse.json()
          // 收集所有模块
          const modulesPromises = plans.map(plan => 
            fetch(`/api/learning/modules/${plan.id}`)
              .then(res => res.json())
              .catch(() => [])
          )
          const modulesArrays = await Promise.all(modulesPromises)
          this.allModules = modulesArrays.flat()
        }
      } catch (error) {
        console.error('获取模块失败:', error)
      }
    },
    
    async createNote() {
      try {
        // 处理标签
        const tags = this.newNote.tagsInput
          ? this.newNote.tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag)
          : []
        
        const response = await fetch('/api/learning/notes', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            title: this.newNote.title,
            content: this.newNote.content,
            module_id: this.newNote.module_id,
            tags: JSON.stringify(tags)
          })
        })
        
        if (response.ok) {
          await this.fetchNotes()
          // 重置表单
          this.newNote = {
            title: '',
            content: '',
            module_id: '',
            tagsInput: ''
          }
        }
      } catch (error) {
        console.error('创建笔记失败:', error)
      }
    },
    
    async updateNote() {
      try {
        // 处理标签
        const tags = this.editingNote.tagsInput
          ? this.editingNote.tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag)
          : []
        
        const response = await fetch(`/api/learning/notes/${this.editingNote.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: new URLSearchParams({
            title: this.editingNote.title,
            content: this.editingNote.content,
            module_id: this.editingNote.module_id,
            tags: JSON.stringify(tags)
          })
        })
        
        if (response.ok) {
          await this.fetchNotes()
          this.showEditModal = false
        }
      } catch (error) {
        console.error('更新笔记失败:', error)
      }
    },
    
    async deleteNote(noteId) {
      if (confirm('确定要删除这个笔记吗？')) {
        try {
          const response = await fetch(`/api/learning/notes/${noteId}`, {
            method: 'DELETE'
          })
          if (response.ok) {
            await this.fetchNotes()
          }
        } catch (error) {
          console.error('删除笔记失败:', error)
        }
      }
    },
    
    editNote(note) {
      this.editingNote = {
        id: note.id,
        title: note.title,
        content: note.content,
        module_id: note.module_id || '',
        tagsInput: note.tags ? note.tags.join(', ') : ''
      }
      this.showEditModal = true
    },
    
    getModuleTitle(moduleId) {
      const module = this.allModules.find(m => m.id === moduleId)
      return module ? module.title : '未知模块'
    },
    
    formatDate(timestamp) {
      if (!timestamp) return '未知'
      const date = new Date(timestamp * 1000)
      return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.note-manager {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>