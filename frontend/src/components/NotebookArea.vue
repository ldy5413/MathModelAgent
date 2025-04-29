<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { renderMarkdown, getMarkdownLines } from '@/utils/markdown'

interface Cell {
  type: 'markdown' | 'code'
  content: string
  output: {
    type: 'text' | 'table' | 'plot'
    content?: string
    data?: {
      headers?: string[]
      rows?: any[][]
    }
  } | null
  isPreview?: boolean
}

const props = defineProps<{
  cells: Cell[]
}>()

const textareaRefs = ref<HTMLTextAreaElement[]>([])

// Markdown 渲染
const renderContent = (content: string) => {
  return renderMarkdown(content)
}

// 切换 Markdown 预览
const toggleMarkdownPreview = (index: number) => {
  props.cells[index].isPreview = !props.cells[index].isPreview
}

// 自动调整文本区域高度
const autoResize = (event: Event, index: number) => {
  const textarea = event.target as HTMLTextAreaElement
  textarea.style.height = 'auto'
  textarea.style.height = textarea.scrollHeight + 'px'
}

// 计算内容行数
const getContentRows = (content: string) => {
  return getMarkdownLines(content)
}

// 组件挂载后初始化文本区域高度
onMounted(async () => {
  await nextTick()
  textareaRefs.value.forEach(textarea => {
    if (textarea) {
      textarea.style.height = textarea.scrollHeight + 'px'
    }
  })
})
</script>


<template>
  <div class="flex-1 px-1 pt-1 bg-gray-50">
    <!-- 遍历所有单元格 -->
    <div v-for="(cell, index) in cells" :key="index" class="transform transition-all duration-200 hover:shadow-lg py-1">
      <div :class="[
        'bg-white rounded-lg shadow-sm overflow-hidden',
        'border border-gray-200 hover:border-blue-300',
        cell.type === 'code' ? 'code-cell' : 'markdown-cell'
      ]">
        <!-- 单元格头部 -->
        <div
          class="px-3 py-1 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white border-b border-gray-200">
          <div class="flex items-center space-x-2">
            <span :class="[
              'px-2 py-1 rounded text-xs font-medium',
              cell.type === 'code' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'
            ]">
              {{ cell.type === 'code' ? `In [${index + 1}]` : 'Markdown' }}
            </span>
          </div>
          <div class="flex items-center space-x-2">
            <button v-if="cell.type === 'markdown'"
              class="text-gray-400 hover:text-blue-500 transition-colors duration-200"
              @click="toggleMarkdownPreview(index)">
              <i :class="[
                'fas',
                cell.isPreview ? 'fa-edit' : 'fa-eye'
              ]"></i>
            </button>
          </div>
        </div>

        <!-- 单元格内容 -->
        <div class="relative">
          <!-- Markdown 内容 -->
          <template v-if="cell.type === 'markdown'">
            <div v-if="cell.isPreview" class="prose prose-blue max-w-none p-4 markdown-preview"
              v-html="renderContent(cell.content)"></div>
            <div v-else class="p-4">
              <textarea v-model="cell.content"
                class="w-full font-mono text-sm bg-transparent outline-none resize-none rounded"
                :rows="getContentRows(cell.content)" @input="(e) => autoResize(e, index)" ref="textareaRefs"></textarea>
            </div>
          </template>

          <!-- 代码内容 -->
          <template v-else>
            <div class="p-4 font-mono relative group">
              <pre class="text-sm overflow-x-auto"><code>{{ cell.content }}</code></pre>
            </div>

            <!-- 代码输出 -->
            <template v-if="cell.output">
              <div class="border-t border-gray-100">
                <div class="px-4 py-3 bg-gray-50">
                  <div class="text-xs font-medium text-gray-500 mb-2">输出:</div>
                  <div class="overflow-x-auto">
                    <!-- 表格输出 -->
                    <template v-if="cell.output.type === 'table' && cell.output.data">
                      <div class="rounded-lg border border-gray-200 overflow-hidden bg-white">
                        <table class="min-w-full divide-y divide-gray-200">
                          <thead class="bg-gray-50">
                            <tr>
                              <th v-for="header in cell.output.data.headers" :key="header"
                                class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {{ header }}
                              </th>
                            </tr>
                          </thead>
                          <tbody class="bg-white divide-y divide-gray-200">
                            <tr v-for="(row, rowIndex) in cell.output.data.rows" :key="rowIndex"
                              class="hover:bg-gray-50">
                              <td v-for="(cell, cellIndex) in row" :key="cellIndex"
                                class="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                                {{ cell }}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </template>

                    <!-- 图表输出 -->
                    <template v-else-if="cell.output.type === 'plot' && typeof cell.output.data === 'string'">
                      <img :src="cell.output.data" class="max-w-full rounded-lg shadow-sm" />
                    </template>

                    <!-- 文本输出 -->
                    <template v-else>
                      <div class="text-sm text-gray-600 font-mono whitespace-pre-wrap">
                        {{ cell.output.content }}
                      </div>
                    </template>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>


<style>
/* Markdown 样式 */
.markdown-preview {
  @apply text-gray-800;
}

.markdown-preview h1 {
  @apply text-2xl font-bold mb-4 text-gray-900;
}

.markdown-preview h2 {
  @apply text-xl font-semibold mb-3 text-gray-800 mt-6;
}

.markdown-preview p {
  @apply mb-4 leading-relaxed text-gray-600;
}

.markdown-preview ul {
  @apply list-disc list-inside mb-4 text-gray-600;
}

.markdown-preview li {
  @apply mb-2;
}

/* 代码样式 */
.code-cell pre {
  @apply bg-gray-50 rounded-md p-2;
}

.code-cell code {
  @apply text-gray-800;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  @apply w-1.5 h-1.5;
}

::-webkit-scrollbar-track {
  @apply bg-gray-100 rounded-full;
}

::-webkit-scrollbar-thumb {
  @apply bg-gray-300 rounded-full hover:bg-gray-400 transition-colors duration-200;
}

/* 表格样式优化 */
table {
  @apply border-collapse;
}

th {
  @apply bg-gray-50 text-left px-4 py-2 text-sm font-medium text-gray-600;
}

td {
  @apply px-4 py-2 text-sm text-gray-700 border-t border-gray-100;
}

tr:hover td {
  @apply bg-blue-50/30;
}

/* 代码高亮样式 */
.hljs {
  @apply bg-gray-50 p-4 rounded-lg my-2;
}

/* 数学公式样式 */
.katex-display {
  @apply my-4 overflow-x-auto;
}

.katex {
  @apply text-base;
}
</style>
