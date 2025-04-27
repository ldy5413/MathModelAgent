<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'

// 单元格数据
const cells = ref([
  {
    type: 'markdown',
    content: '# 数据分析报告\n\n这个笔记本分析了我们的季度销售数据，以识别趋势和增长机会。\n\n## 主要发现\n- 销售额持续增长\n- 客户满意度提升\n- 新产品线表现优异',
    output: null,
    isPreview: true
  },
  {
    type: 'code',
    content: `import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 加载数据集
df = pd.read_csv('sales_data.csv')

# 预览数据
df.head()`,
    output: {
      type: 'table',
      data: {
        headers: ['Date', 'Revenue', 'Units', 'Region'],
        rows: [
          ['2023-01-01', '2450.32', '45', 'North'],
          ['2023-01-02', '1890.45', '38', 'South'],
          ['2023-01-03', '3120.75', '62', 'East'],
          ['2023-01-04', '2780.90', '55', 'West'],
          ['2023-01-05', '1950.60', '39', 'North']
        ]
      }
    }
  },
  {
    type: 'markdown',
    content: '## 销售趋势分析\n\n从上面的数据可以看出，各个地区的销售情况都比较稳定，其中：\n\n1. 东部地区表现最好\n2. 北部和西部地区紧随其后\n3. 南部地区有待提升',
    output: null,
    isPreview: true
  },
  {
    type: 'code',
    content: '# 计算统计摘要\ndf.describe()',
    output: {
      type: 'table',
      data: {
        headers: ['Metric', 'Count', 'Mean', 'Std', 'Min', '25%', '50%', '75%', 'Max'],
        rows: [
          ['Revenue', '1200', '2450.32', '1204.56', '450.00', '1560.25', '2240.50', '3120.75', '5890.00'],
          ['Units', '1200', '45.2', '22.1', '5', '28', '42', '60', '125']
        ]
      }
    }
  }
])

const textareaRefs = ref([])

// Markdown 渲染
const renderMarkdown = (content) => {
  return marked(content, { breaks: true })
}

// 切换 Markdown 预览
const toggleMarkdownPreview = (index) => {
  cells.value[index].isPreview = !cells.value[index].isPreview
}

// 自动调整文本区域高度
const autoResize = (event, index) => {
  const textarea = event.target
  textarea.style.height = 'auto'
  textarea.style.height = textarea.scrollHeight + 'px'
}

// 计算内容行数
const getContentRows = (content) => {
  return content.split('\n').length
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
              v-html="renderMarkdown(cell.content)"></div>
            <div v-else class="p-4">
              <textarea v-model="cell.content"
                class="w-full font-mono text-sm bg-transparent outline-none resize-none rounded"
                :rows="getContentRows(cell.content)" @input="(e) => autoResize(e, index)" ref="textareaRefs"
                readonly></textarea>
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
                    <template v-if="cell.output.type === 'table'">
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
                    <template v-else-if="cell.output.type === 'plot'">
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
</style>
