<script setup lang="ts">
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import CoderEditor from '@/components/CoderEditor.vue'
import WriterEditor from '@/components/WriterEditor.vue'
import ChatArea from '@/components/ChatArea.vue'
import { onMounted, onBeforeUnmount } from 'vue'
import { useTaskStore } from '@/stores/task'


const props = defineProps<{ task_id: string }>()
const taskStore = useTaskStore()

console.log('Task ID:', props.task_id)

onMounted(() => {
  taskStore.connectWebSocket(props.task_id)
})

onBeforeUnmount(() => {
  taskStore.closeWebSocket()
})

</script>

<template>
  <ResizablePanelGroup direction="horizontal" class="h-screen rounded-lg border">
    <ResizablePanel :default-size="30" class="h-screen">
      <ChatArea :messages="taskStore.chatMessages" />
    </ResizablePanel>
    <ResizableHandle />
    <ResizablePanel :default-size="70" class="h-screen min-w-0">
      <div class="flex h-full flex-col min-w-0">
        <Tabs default-value="coder" class="w-full h-full">
          <div class="border-b px-4 py-1">
            <TabsList class="justify-center">
              <TabsTrigger value="coder" class="text-sm">
                CoderAgent
              </TabsTrigger>
              <TabsTrigger value="writer" class="text-sm">
                WriterAgent
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="coder" class="flex-1 p-1 min-w-0 h-full">
            <Card class="h-full min-w-0">
              <CardContent class="p-2 h-full min-w-0">
                <CoderEditor :messages="taskStore.coderMessages" class="h-full min-w-0" />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="writer" class="flex-1 p-1 h-full overflow-hidden">
            <Card class="h-full">
              <CardContent class="p-2 h-full">
                <WriterEditor :messages="taskStore.writerMessages" />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ResizablePanel>
  </ResizablePanelGroup>
  <button @click="taskStore.downloadMessages"
    class="absolute top-2 right-2 z-10 bg-blue-500 text-white px-3 py-1 rounded">
    下载消息
  </button>
</template>