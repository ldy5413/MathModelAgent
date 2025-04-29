<script setup lang="ts">
import { ref } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
} from '@/components/ui/sidebar'
import { ScrollArea } from '@/components/ui/scroll-area'
import Files from '@/components/Files.vue'
import NotebookArea from '@/components/NotebookArea.vue'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable'

</script>
<template>
  <SidebarProvider>
    <SidebarInset class="flex-1 flex flex-col min-h-0 min-w-0 h-full">
      <div class="flex-1 min-h-0 min-w-0 overflow-auto h-full">
        <ResizablePanelGroup direction="horizontal" class="h-full w-full">
          <ResizablePanel :default-size="25" :min-size="15" class="h-full w-full flex flex-1">
            <ScrollArea class="h-full w-full flex flex-1">
              <Files class="h-full w-full fixed" />
            </ScrollArea>

          </ResizablePanel>
          
          <ResizableHandle with-handle />
          <ResizablePanel :default-size="75" :min-size="30" class="h-full w-full flex flex-1">
            <ScrollArea class="h-full w-full flex flex-1">
              <NotebookArea class="h-full min-w-0 pb-4" />
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>

      </div>
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped>

::-webkit-scrollbar {
  display: none; /* 或者 width: 0; height: 0; */
}

</style>
