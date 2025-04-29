<script setup lang="ts">
import { ref } from 'vue'
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
          <div class="flex-1 min-h-0 min-w-0 overflow-auto h-full">
            <NotebookArea class="h-full min-w-0 pb-4" />
          </div>
        </SidebarInset>
      </ResizablePanel>
    </ResizablePanelGroup>
  </SidebarProvider>
</template>