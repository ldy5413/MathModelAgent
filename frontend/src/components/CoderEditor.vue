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
  useSidebar
} from '@/components/ui/sidebar'
import Files from '@/components/Files.vue'


import RenderJupyterNotebook from 'render-jupyter-notebook-vue'
import example from '@/assets/jupyter.json'

const isCollapsed = ref(false)

// 处理折叠状态
const handleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}




const notebook = ref(example)



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
          <RenderJupyterNotebook :notebook="notebook" />
        </div>
      </SidebarInset>
    </div>
  </SidebarProvider>
</template>