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
    <div class="flex h-screen">
      <div :class="[
        'transition-all duration-300 overflow-hidden',
        isCollapsed ? 'w-0' : 'w-64'
      ]">
        <Files class="w-64 border-r h-full" />
      </div>
      <SidebarInset class="flex-1 flex flex-col">
        <header class="flex h-10 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger class="-ml-1" @click="handleCollapse" />
        </header>
        <div class="flex-1 overflow-auto p-4">
          <NotebookArea></NotebookArea>
        </div>
      </SidebarInset>
    </div>
  </SidebarProvider>
</template>