<script setup lang="ts">
import Bubble from './Bubble.vue'
import SystemMessage from './SystemMessage.vue'
import { ref, nextTick } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send } from 'lucide-vue-next'

interface Message {
  id: number
  type: 'user' | 'ai' | 'system'
  content: string
  systemType?: 'info' | 'warning' | 'success' | 'error'
}

const messages = ref<Message[]>([
  {
    id: 1,
    type: 'user',
    content: '请帮我分析这份数据'
  },
  {
    id: 2,
    type: 'system',
    content: '正在处理数据分析请求...',
    systemType: 'info'
  },
  {
    id: 3,
    type: 'ai',
    content: `好的，我来帮你分析这些数据。首先，让我们看看数据的基本统计信息：

1. 数据概览
   - 样本数量
   - 数值范围
   - 分布特征

2. 关键指标
   - 均值
   - 中位数
   - 标准差

接下来我们可以深入分析...`
  },
  {
    id: 4,
    type: 'system',
    content: '数据分析完成',
    systemType: 'success'
  }
])

const inputValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const scrollRef = ref<HTMLDivElement | null>(null)

// 添加新消息的方法
const addMessage = (message: Omit<Message, 'id'>) => {
  messages.value.push({
    ...message,
    id: messages.value.length + 1
  })
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

const sendMessage = () => {
  if (!inputValue.value.trim()) return
  addMessage({ type: 'user', content: inputValue.value })
  inputValue.value = ''
  inputRef.value?.focus()
}
</script>

<template>
  <div class="flex h-full flex-col p-4">
    <div ref="scrollRef" class="flex-1 overflow-y-auto">
      <template v-for="message in messages" :key="message.id">
        <div class="mb-3">
          <Bubble v-if="message.type === 'user' || message.type === 'ai'" :type="message.type"
            :content="message.content" />
          <SystemMessage v-else :content="message.content" :type="message.systemType" />
        </div>
      </template>
    </div>
    <form class="w-full max-w-2xl mx-auto flex items-center gap-2 pt-4" @submit.prevent="sendMessage">
      <Input ref="inputRef" v-model="inputValue" type="text" placeholder="请输入消息..." class="flex-1" autocomplete="off" />
      <Button type="submit" :disabled="!inputValue.trim()">
        <Send />
      </Button>
    </form>
  </div>
</template>

<style scoped>
/* 自定义滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  @apply bg-transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}
</style>