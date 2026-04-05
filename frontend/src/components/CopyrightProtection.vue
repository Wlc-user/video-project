<template>
  <section class="py-12 bg-gray-50">
    <div class="max-w-6xl mx-auto px-4">
      <!-- 标题 -->
      <div class="text-center mb-8">
        <h2 class="text-3xl font-bold text-gray-900 mb-2">版权保护</h2>
        <p class="text-gray-600">上传原创视频，检测侵权内容，保护你的创作权益</p>
      </div>

      <!-- 标签页 -->
      <div class="flex justify-center gap-4 mb-8">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-6 py-2 rounded-full font-medium transition-all',
            activeTab === tab.id
              ? 'bg-blue-600 text-white shadow-lg'
              : 'bg-white text-gray-600 hover:bg-gray-100'
          ]"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- 指纹生成 -->
      <div v-if="activeTab === 'fingerprint'" class="bg-white rounded-2xl shadow-lg p-8">
        <h3 class="text-xl font-semibold mb-4">生成视频指纹</h3>
        <p class="text-gray-600 mb-6">
          上传你的原创视频，系统将自动生成唯一的视频指纹，用于后续侵权检测。
        </p>

        <!-- 文件上传 -->
        <div
          class="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 transition-colors"
          @click="triggerFingerprintUpload"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="handleFingerprintDrop"
          :class="{ 'border-blue-400 bg-blue-50': dragOver }"
        >
          <input
            ref="fingerprintInput"
            type="file"
            accept="video/*"
            class="hidden"
            @change="handleFingerprintFile"
          />
          <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p class="text-gray-600 mb-2">点击或拖拽上传视频文件</p>
          <p class="text-sm text-gray-400">支持 MP4, AVI, MKV 等格式</p>
        </div>

        <!-- 上传进度 -->
        <div v-if="fingerprintLoading" class="mt-6">
          <div class="flex items-center gap-3">
            <div class="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
            <span class="text-gray-600">正在生成指纹...</span>
          </div>
        </div>

        <!-- 指纹结果 -->
        <div v-if="fingerprintResult" class="mt-6 p-4 bg-green-50 rounded-xl border border-green-200">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="font-medium text-green-800">指纹生成成功</span>
          </div>
          <p class="text-sm text-green-700">视频: {{ fingerprintResult.video_name }}</p>
          <p class="text-sm text-green-700">pHash: {{ fingerprintResult.fingerprint.phash }}</p>
        </div>
      </div>

      <!-- 侵权检测 -->
      <div v-if="activeTab === 'detect'" class="bg-white rounded-2xl shadow-lg p-8">
        <h3 class="text-xl font-semibold mb-4">检测侵权内容</h3>
        <p class="text-gray-600 mb-6">
          上传疑似侵权的视频，系统将与数据库中的原创视频指纹进行比对。
        </p>

        <!-- 文件上传 -->
        <div
          class="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-red-400 transition-colors"
          @click="triggerDetectUpload"
          @dragover.prevent="detectDragOver = true"
          @dragleave="detectDragOver = false"
          @drop.prevent="handleDetectDrop"
          :class="{ 'border-red-400 bg-red-50': detectDragOver }"
        >
          <input
            ref="detectInput"
            type="file"
            accept="video/*"
            class="hidden"
            @change="handleDetectFile"
          />
          <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <p class="text-gray-600 mb-2">点击或拖拽上传待检测视频</p>
          <p class="text-sm text-gray-400">支持 MP4, AVI, MKV 等格式</p>
        </div>

        <!-- 检测进度 -->
        <div v-if="detectLoading" class="mt-6">
          <div class="flex items-center gap-3">
            <div class="animate-spin w-5 h-5 border-2 border-red-600 border-t-transparent rounded-full"></div>
            <span class="text-gray-600">正在检测...</span>
          </div>
        </div>

        <!-- 检测结果 -->
        <div v-if="detectResult" class="mt-6">
          <!-- 无侵权 -->
          <div v-if="!detectResult.has_infringement" class="p-4 bg-green-50 rounded-xl border border-green-200">
            <div class="flex items-center gap-2">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span class="font-medium text-green-800">未检测到侵权内容</span>
            </div>
            <p class="text-sm text-green-700 mt-2">与 {{ detectResult.total_checked }} 个原创视频进行比对，未发现相似内容。</p>
          </div>

          <!-- 有侵权 -->
          <div v-else class="p-4 bg-red-50 rounded-xl border border-red-200">
            <div class="flex items-center gap-2 mb-4">
              <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span class="font-medium text-red-800">检测到 {{ detectResult.matches.length }} 个疑似侵权内容！</span>
            </div>

            <div class="space-y-3">
              <div
                v-for="(match, index) in detectResult.matches"
                :key="index"
                class="p-3 bg-white rounded-lg border border-red-100"
              >
                <div class="flex justify-between items-start">
                  <div>
                    <p class="font-medium text-gray-800">{{ match.matched_video }}</p>
                    <p class="text-sm text-gray-600">相似度: {{ match.overall_similarity }}%</p>
                  </div>
                  <span
                    :class="[
                      'px-2 py-1 rounded text-xs font-medium',
                      match.overall_similarity >= 70 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    ]"
                  >
                    {{ match.overall_similarity >= 70 ? '高度疑似侵权' : '疑似相似' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 监控管理 -->
      <div v-if="activeTab === 'monitor'" class="bg-white rounded-2xl shadow-lg p-8">
        <h3 class="text-xl font-semibold mb-4">侵权监控</h3>
        <p class="text-gray-600 mb-6">
          添加原创视频标题为关键词，系统将定期在各大平台搜索疑似侵权内容。
        </p>

        <!-- 添加关键词 -->
        <div class="flex gap-3 mb-6">
          <input
            v-model="monitorKeyword"
            type="text"
            placeholder="输入原创视频标题作为关键词"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @keyup.enter="addToWatchlist"
          />
          <select
            v-model="monitorPlatform"
            class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部平台</option>
            <option value="bilibili">B站</option>
            <option value="douyin">抖音</option>
          </select>
          <button
            @click="addToWatchlist"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            添加监控
          </button>
        </div>

        <!-- 监控列表 -->
        <div class="space-y-3">
          <div
            v-for="(item, index) in watchlist"
            :key="index"
            class="flex justify-between items-center p-4 bg-gray-50 rounded-xl"
          >
            <div>
              <p class="font-medium text-gray-800">{{ item.keyword }}</p>
              <p class="text-sm text-gray-500">
                平台: {{ item.platforms?.join(', ') || '全部' }} |
                添加时间: {{ formatTime(item.added_at) }}
              </p>
            </div>
            <button
              @click="removeFromWatchlist(item.keyword)"
              class="text-red-600 hover:text-red-700"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>

          <div v-if="watchlist.length === 0" class="text-center py-8 text-gray-500">
            暂无监控关键词
          </div>
        </div>

        <!-- 手动扫描 -->
        <div class="mt-6 pt-6 border-t border-gray-200">
          <button
            @click="runScan"
            :disabled="scanLoading || watchlist.length === 0"
            class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ scanLoading ? '扫描中...' : '立即扫描' }}
          </button>

          <div v-if="scanResults.length > 0" class="mt-4">
            <p class="text-sm text-gray-600 mb-2">
              共发现 {{ scanResults.reduce((sum, r) => sum + r.matches_count, 0) }} 个疑似侵权内容
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'

// 开发环境直接请求后端，生产环境用代理
const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000/api/copyright' : '/api/copyright'

// 标签页
const tabs = [
  { id: 'fingerprint', name: '指纹生成' },
  { id: 'detect', name: '侵权检测' },
  { id: 'monitor', name: '监控管理' }
]
const activeTab = ref('fingerprint')

// 指纹生成
const fingerprintInput = ref(null)
const dragOver = ref(false)
const fingerprintLoading = ref(false)
const fingerprintResult = ref(null)

function triggerFingerprintUpload() {
  fingerprintInput.value?.click()
}

function handleFingerprintFile(e) {
  const file = e.target.files[0]
  if (file) uploadFingerprint(file)
}

function handleFingerprintDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('video/')) {
    uploadFingerprint(file)
  }
}

async function uploadFingerprint(file) {
  fingerprintLoading.value = true
  fingerprintResult.value = null

  const formData = new FormData()
  formData.append('video', file)

  console.log('上传文件:', file.name, file.size, 'bytes')

  try {
    const res = await fetch(`${API_BASE}/fingerprint/generate`, {
      method: 'POST',
      body: formData
    })
    
    console.log('响应状态:', res.status)
    const text = await res.text()
    console.log('响应内容:', text)
    
    const data = JSON.parse(text)
    if (data.status === 'success') {
      fingerprintResult.value = data
    } else {
      alert('生成失败: ' + (data.detail || '未知错误'))
    }
  } catch (err) {
    console.error('上传错误:', err)
    alert('生成失败: ' + err.message)
  } finally {
    fingerprintLoading.value = false
  }
}

// 侵权检测
const detectInput = ref(null)
const detectDragOver = ref(false)
const detectLoading = ref(false)
const detectResult = ref(null)

function triggerDetectUpload() {
  detectInput.value?.click()
}

function handleDetectFile(e) {
  const file = e.target.files[0]
  if (file) detectPlagiarism(file)
}

function handleDetectDrop(e) {
  detectDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('video/')) {
    detectPlagiarism(file)
  }
}

async function detectPlagiarism(file) {
  detectLoading.value = true
  detectResult.value = null

  const formData = new FormData()
  formData.append('video', file)

  console.log('检测文件:', file.name, file.size, 'bytes')

  try {
    const res = await fetch(`${API_BASE}/detect`, {
      method: 'POST',
      body: formData
    })
    
    console.log('响应状态:', res.status)
    const text = await res.text()
    console.log('响应内容:', text)
    
    const data = JSON.parse(text)
    if (data.status === 'success') {
      detectResult.value = data
    } else {
      alert('检测失败: ' + (data.detail || JSON.stringify(data)))
    }
  } catch (err) {
    console.error('检测错误:', err)
    alert('检测失败: ' + err.message)
  } finally {
    detectLoading.value = false
  }
}

// 监控管理
const monitorKeyword = ref('')
const monitorPlatform = ref('')
const watchlist = ref([])
const scanLoading = ref(false)
const scanResults = ref([])

onMounted(() => {
  fetchWatchlist()
})

async function fetchWatchlist() {
  try {
    const res = await fetch(`${API_BASE}/watchlist`)
    const data = await res.json()
    if (data.status === 'success') {
      watchlist.value = data.watchlist || []
    }
  } catch (err) {
    console.error('获取监控列表失败:', err)
  }
}

async function addToWatchlist() {
  if (!monitorKeyword.value.trim()) return

  const platforms = monitorPlatform.value ? [monitorPlatform.value] : ['bilibili', 'douyin']

  try {
    const res = await fetch(`${API_BASE}/watchlist/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyword: monitorKeyword.value,
        platforms: platforms
      })
    })
    const data = await res.json()
    if (data.status === 'success') {
      monitorKeyword.value = ''
      monitorPlatform.value = ''
      fetchWatchlist()
    } else {
      alert('添加失败: ' + (data.detail || '未知错误'))
    }
  } catch (err) {
    alert('添加失败: ' + err.message)
  }
}

async function removeFromWatchlist(keyword) {
  try {
    const res = await fetch(`${API_BASE}/watchlist/${encodeURIComponent(keyword)}`, {
      method: 'DELETE'
    })
    const data = await res.json()
    if (data.status === 'success') {
      fetchWatchlist()
    }
  } catch (err) {
    console.error('移除失败:', err)
  }
}

async function runScan() {
  scanLoading.value = true
  scanResults.value = []

  try {
    const res = await fetch(`${API_BASE}/scan`, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'success') {
      scanResults.value = data.results || []
    }
  } catch (err) {
    alert('扫描失败: ' + err.message)
  } finally {
    scanLoading.value = false
  }
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleDateString('zh-CN')
}
</script>
