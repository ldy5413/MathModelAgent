<script lang="ts">
export const description = 'A sidebar with a collapsible file tree.'
export const iframeHeight = '800px'
</script>
<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import Files from '@/components/Files.vue'
import NotebookArea from '@/components/NotebookArea.vue'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable'
import type { CoderMessage } from '@/utils/response'

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
  messages: CoderMessage[]
}>()

// 将代码执行结果转换为Notebook单元格
const cells = computed<Cell[]>(() => {
  const notebookCells: Cell[] = []

  for (const msg of props.messages) {
    // 如果有普通内容，创建markdown单元格
    if (msg.content) {
      notebookCells.push({
        type: 'markdown',
        content: msg.content,
        output: null,
        isPreview: true
      })
    }

    // 如果有代码，创建代码单元格
    if (msg.code) {
      const cell: Cell = {
        type: 'code',
        content: msg.code,
        output: null
      }

      // 如果有执行结果，添加到输出
      if (msg.code_results && msg.code_results.length > 0) {
        const result = msg.code_results[0] // 暂时只取第一个结果

        if (result.res_type === 'result') {
          cell.output = {
            type: 'table',
            data: {
              headers: [],
              rows: []
            }
          }
          try {
            const data = JSON.parse(result.msg || '{}')
            if (data.headers && data.rows) {
              cell.output.data = data
            }
          } catch (e) {
            cell.output = {
              type: 'text',
              content: result.msg || ''
            }
          }
        } else {
          cell.output = {
            type: 'text',
            content: result.msg || ''
          }
        }
      }

      notebookCells.push(cell)
    }
  }

  return notebookCells
})

const isCollapsed = ref(false)

// 处理折叠状态
const handleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}


</script>
<template>
  <SidebarProvider :collapsed="isCollapsed">
    <ResizablePanelGroup direction="horizontal" class="h-full w-full min-w-0 min-h-0">
      <!-- 左侧 Files 面板 -->
      <ResizablePanel :default-size="20" :min-size="10" :max-size="40" class="h-full">
        <Files class="h-full border-r" />
      </ResizablePanel>
      <!-- 拖拽手柄 -->
      <ResizableHandle />
      <!-- 右侧 Notebook 面板 -->
      <ResizablePanel :default-size="80" :min-size="60" class="h-full">
        <SidebarInset class="flex-1 flex flex-col min-h-0 min-w-0 h-full">
          <header class="flex h-10 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger class="-ml-1" @click="handleCollapse" />
          </header>
          <div class="flex-1 min-h-0 min-w-0 overflow-auto">
            <NotebookArea :cells="cells" class="h-full min-w-0" />
          </div>
        </SidebarInset>
      </ResizablePanel>
    </ResizablePanelGroup>
  </SidebarProvider>
</template>