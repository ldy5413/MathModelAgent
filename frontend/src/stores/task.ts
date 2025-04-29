import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { TaskWebSocket } from '@/utils/websocket'
import type { Message, CoderMessage, WriterMessage } from '@/utils/response'
import messageData from '@/test/20250428-200915-ebc154d4.json'

export const useTaskStore = defineStore('task', () => {
  const messages = ref<Message[]>([])
  let ws: TaskWebSocket | null = null

  // 连接 WebSocket
  function connectWebSocket(taskId: string) {
    const baseUrl = import.meta.env.VITE_WS_URL
    const wsUrl = `${baseUrl}/task/${taskId}`

    ws = new TaskWebSocket(wsUrl, (data) => {
      console.log(data)
      messages.value.push(data)
    })
    messages.value = messageData as Message[]
    ws.connect()
  }

  // 关闭 WebSocket
  function closeWebSocket() {
    ws?.close()
  }

  // 下载消息
  function downloadMessages() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(messages.value, null, 2))
    const downloadAnchorNode = document.createElement('a')
    downloadAnchorNode.setAttribute("href", dataStr)
    downloadAnchorNode.setAttribute("download", "message.json")
    document.body.appendChild(downloadAnchorNode)
    downloadAnchorNode.click()
    downloadAnchorNode.remove()
  }

  // 计算属性
  const chatMessages = computed(() =>
    messages.value.filter(
      (msg) => {
        if (msg.msg_type === 'agent' && msg.agent_type === 'CoderAgent' && msg.content == null) {
          return false
        }
        if (msg.msg_type === 'agent' && msg.agent_type === 'WriterAgent') {
          return false
        }
        return msg.msg_type === 'agent' && msg.content || msg.msg_type === 'system'
      }
    )
  )

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


  const files = computed(() => {
    // 反向遍历消息找到最新的文件列表
    for (let i = coderMessages.value.length - 1; i >= 0; i--) {
      const msg = coderMessages.value[i]
      if ('files' in msg && msg.files?.length) {
        return msg.files
      }
    }
    return []
  })
  

  return {
    messages,
    chatMessages,
    coderMessages,
    writerMessages,
    files,
    connectWebSocket,
    closeWebSocket,
    downloadMessages
  }
}) 