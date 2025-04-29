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
import { onMounted, ref, onBeforeUnmount, computed } from 'vue'
import { TaskWebSocket } from '@/utils/websocket'
import type { Message, CoderMessage, WriterMessage } from '@/utils/response'
import messageData from '@/pages/test/20250428-200915-ebc154d4.json'

const props = defineProps<{ task_id: string }>()
const messages = ref<Message[]>([])

console.log('Task ID:', props.task_id) // 输出 

let ws: TaskWebSocket | null = null

onMounted(() => {
  const baseUrl = import.meta.env.VITE_WS_URL
  const wsUrl = `${baseUrl}/task/${props.task_id}`

  ws = new TaskWebSocket(wsUrl, (data) => {
    console.log(data)
    // 这里可以做类型转换 
    messages.value.push(data)
  })
  ws.connect()

  // TODO: 测试模式下加载
  // 本地加载 message.json
  messages.value = messageData as Message[]
})

onBeforeUnmount(() => {
  ws?.close()
})


// CoderMessage 的 
// content
// 显示在 CoderEditor 里

const chatMessages = computed(() =>
  messages.value.filter(
    (msg) => {
      if (msg.msg_type === 'agent' && msg.agent_type === 'CoderAgent' && msg.content == null) {
        // 有 code_result 的 CoderAgent 消息不显示
        return false
      }
      // writer agent 不显示 ## TODO writer 应该显示
      if (msg.msg_type === 'agent' && msg.agent_type === 'WriterAgent') {
        return false
      }
      // 其他 agent 或 system 消息正常显示
      return msg.msg_type === 'agent' && msg.content || msg.msg_type === 'system'
    }
  )
)

// CoderMessage 的 
// code: str | None = None
// code_result
// 显示在 CoderEditor 里

const coderMessages = computed(() =>
  messages.value.filter(
    (msg): msg is CoderMessage =>
      msg.msg_type === 'agent' &&
      msg.agent_type === 'CoderAgent' &&
      (msg.code != null || msg.content != null)
  )
)


const writerMessages = computed(() =>
  messages.value.filter(
    (msg): msg is WriterMessage =>
      msg.msg_type === 'agent' &&
      msg.agent_type === 'WriterAgent' &&
      msg.content != null
  )
)

function downloadMessages() {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(messages.value, null, 2))
  const downloadAnchorNode = document.createElement('a')
  downloadAnchorNode.setAttribute("href", dataStr)
  downloadAnchorNode.setAttribute("download", "message.json")
  document.body.appendChild(downloadAnchorNode)
  downloadAnchorNode.click()
  downloadAnchorNode.remove()
}

</script>

<template>
  <ResizablePanelGroup direction="horizontal" class="h-screen rounded-lg border">
    <ResizablePanel :default-size="30" class="h-screen">
      <ChatArea :messages="chatMessages" />
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
                <CoderEditor :messages="coderMessages" class="h-full min-w-0" />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="writer" class="flex-1 p-1 h-full overflow-hidden">
            <Card class="h-full">
              <CardContent class="p-2 h-full">
                <WriterEditor :messages="writerMessages" />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ResizablePanel>
  </ResizablePanelGroup>
  <button @click="downloadMessages" class="absolute top-2 right-2 z-10 bg-blue-500 text-white px-3 py-1 rounded">
    下载消息
  </button>
</template>