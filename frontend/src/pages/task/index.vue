<script setup lang="ts">
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import Bubble from '@/components/Bubble.vue'
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
import { onMounted, ref, onBeforeUnmount } from 'vue'

const props = defineProps({
  task_id: {
    type: String,
    required: true
  }
})

console.log('Task ID:', props.task_id) // 输出 

const socket = ref<WebSocket | null>(null)

const initWebSocket = () => {
  const baseUrl = import.meta.env.VITE_WS_URL
  const wsUrl = `${baseUrl}/task/${props.task_id}`
  console.log('wsUrl', wsUrl)


  // 关闭现有连接
  if (socket.value) {
    socket.value.close()
  }

  socket.value = new WebSocket(wsUrl)
  console.log('WebSocket 对象已创建:', socket.value)

  socket.value.onopen = () => {
    console.log('WebSocket 连接已建立')
  }

  socket.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    console.log('收到消息:', data)
  }

  socket.value.onclose = (event) => {
    console.log('WebSocket 连接已关闭', event.code, event.reason)
  }

  socket.value.onerror = (error) => {
    console.error('WebSocket 错误:', error)
    console.error('WebSocket 错误详情:', error.message)
  }
}


onMounted(() => {
  initWebSocket()
})

onBeforeUnmount(() => {
  if (socket.value) {
    socket.value.close()
  }
})
</script>

<template>
  <ResizablePanelGroup direction="horizontal" class="h-screen rounded-lg border">
    <ResizablePanel :default-size="25" class="h-screen">
      <div class="flex h-full flex-col p-4">
        <div class="flex-1 space-y-4 overflow-y-auto">
          <Bubble type="user">
            请帮我分析这份数据
          </Bubble>
          <Bubble type="ai">
            好的，我来帮你分析这些数据。首先，让我们看看数据的基本统计信息...
          </Bubble>
          <!-- 更多消息... -->
        </div>
      </div>
    </ResizablePanel>
    <ResizableHandle with-handle />
    <ResizablePanel :default-size="75" class="h-screen">
      <div class="flex h-full flex-col">
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

          <TabsContent value="coder" class="flex-1 p-1">
            <Card>
              <CardContent class="p-2">
                <CoderEditor />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="writer" class="flex-1 p-1">
            <Card>
              <CardContent class="p-2">
                <WriterEditor />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ResizablePanel>
  </ResizablePanelGroup>
</template>