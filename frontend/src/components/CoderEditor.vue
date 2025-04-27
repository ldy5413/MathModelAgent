<script lang="ts">
export const description = 'A sidebar with a collapsible file tree.'
export const iframeHeight = '800px'
</script>
<script setup lang="ts">
import { ref } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import Files from '@/components/Files.vue'
import NotebookArea from '@/components/NotebookArea.vue'


const isCollapsed = ref(false)

// 处理折叠状态
const handleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}


</script>
<template>
  <SidebarProvider :collapsed="isCollapsed">
    <div class="flex h-full min-h-0 w-full min-w-0">
      <div :class="[
        'transition-all duration-300 overflow-hidden',
        isCollapsed ? 'w-0' : 'w-44'
      ]">
        <Files class="w-44 border-r h-full" />
      </div>
      <SidebarInset class="flex-1 flex flex-col min-h-0 min-w-0">
        <header class="flex h-10 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger class="-ml-1" @click="handleCollapse" />
        </header>
        <div class="flex-1 min-h-0 min-w-0 overflow-auto">
          <NotebookArea class="h-full min-w-0" />
        </div>
      </SidebarInset>
    </div>
  </SidebarProvider>
</template>