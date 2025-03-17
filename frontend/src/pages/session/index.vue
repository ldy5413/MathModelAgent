<script setup lang="ts">
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
</script>

<template>
  <ResizablePanelGroup id="handle-demo-group-1" direction="horizontal" class="h-screen rounded-lg border">
    <ResizablePanel id="handle-demo-panel-1" :default-size="25" class="h-screen">
      <div class="flex h-full items-center justify-center p-6">
        <span class="font-semibold">Sidebar</span>
      </div>
    </ResizablePanel>
    <ResizableHandle id="handle-demo-handle-1" with-handle />
    <ResizablePanel id="handle-demo-panel-2" :default-size="75" class="h-screen">
      <div class="flex h-full items-center justify-center p-6">
        <span class="font-semibold">Content</span>
      </div>
    </ResizablePanel>
  </ResizablePanelGroup>
</template>