<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { respondCheckpoint } from '@/apis/commonApi'
import type { SystemMessage } from '@/utils/response'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const props = defineProps<{ message: SystemMessage }>()

const countdown = ref<number>(props.message.action?.timeout_sec ?? 10)
const responded = ref<boolean>(false)
const showFeedback = ref<boolean>(false)
const feedbackText = ref<string>("")
let intervalTimer: ReturnType<typeof setInterval> | null = null
let autoTimeout: ReturnType<typeof setTimeout> | null = null

const route = useRoute()
const taskId = (route.params.task_id || route.params.id || '').toString()

function stopTimers() {
  if (intervalTimer) {
    clearInterval(intervalTimer)
    intervalTimer = null
  }
  if (autoTimeout) {
    clearTimeout(autoTimeout)
    autoTimeout = null
  }
}

async function sendAction(action: 'continue' | 'feedback') {
  if (responded.value) return
  const checkpointId = props.message.action?.checkpoint_id
  if (!checkpointId) return
  responded.value = true
  // 记忆当前检查点已响应，避免回到页面后重复触发
  try {
    sessionStorage.setItem(`checkpoint:${checkpointId}:responded`, '1')
  } catch {}
  stopTimers()
  try {
    await respondCheckpoint(taskId, {
      checkpoint_id: checkpointId,
      action,
      content: action === 'feedback' ? feedbackText.value : undefined,
    })
  } catch (e) {
    // 忽略错误（后端超时也会自动继续）
  }
}

function onClickContinue() {
  sendAction('continue')
}

function onClickFeedback() {
  showFeedback.value = true
  // 需求1：用户选择提供反馈时，停止计时
  stopTimers()
  // 同步后端：进入反馈输入态（暂停后端倒计时）
  const checkpointId = props.message.action?.checkpoint_id
  if (!responded.value && checkpointId) {
    respondCheckpoint(taskId, {
      checkpoint_id: checkpointId,
      action: 'feedback_open',
    }).catch(() => {})
    try {
      sessionStorage.setItem(`checkpoint:${checkpointId}:feedback_open`, '1')
    } catch {}
  }
}

async function onSubmitFeedback() {
  if (!feedbackText.value.trim()) return
  await sendAction('feedback')
}

onMounted(() => {
  const checkpointId = props.message.action?.checkpoint_id
  // 若之前已响应该检查点（从别处或此前页面会话中），显示“已提交”，不再计时
  try {
    if (checkpointId && sessionStorage.getItem(`checkpoint:${checkpointId}:responded`) === '1') {
      responded.value = true
      return
    }
    // 若此前进入过反馈输入态，则不计时，直接展示反馈输入
    if (checkpointId && sessionStorage.getItem(`checkpoint:${checkpointId}:feedback_open`) === '1') {
      showFeedback.value = true
      // 不启动任何计时器（后端已暂停倒计时）
      return
    }
  } catch {}

  // 可视倒计时（1s刷新）
  intervalTimer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value -= 1
    } else {
      if (!responded.value) {
        sendAction('continue')
      }
      stopTimers()
    }
  }, 1000)

  // 自动提交定时器（更稳健，避免浏览器对 setInterval 节流导致未触发）
  const sec = Math.max(0, Number(props.message.action?.timeout_sec ?? 10))
  autoTimeout = setTimeout(() => {
    if (!responded.value) {
      sendAction('continue')
    }
    stopTimers()
  }, sec * 1000)
})

onBeforeUnmount(() => {
  stopTimers()
})
</script>

<template>
  <div class="flex justify-center my-2">
    <div class="inline-flex flex-col items-center gap-2 px-3 py-2 text-xs rounded-md border bg-blue-500/5 border-blue-500/10 text-blue-600 dark:text-blue-400">
      <div class="flex items-center gap-2">
        <svg class="w-3 h-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <span>{{ props.message.content }}</span>
        <span v-if="!responded" class="font-mono text-[10px] opacity-70">({{ countdown }}s)</span>
        <span v-else class="font-mono text-[10px] opacity-70">已提交</span>
      </div>
      <div v-if="!responded" class="flex items-center gap-2">
        <Button size="sm" @click="onClickContinue">继续</Button>
        <Button size="sm" variant="outline" @click="onClickFeedback">用户反馈</Button>
      </div>
      <div v-if="!responded && showFeedback" class="flex items-center gap-2 w-full">
        <Input v-model="feedbackText" placeholder="请输入反馈..." class="flex-1" />
        <Button size="sm" :disabled="!feedbackText.trim()" @click="onSubmitFeedback">提交</Button>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
