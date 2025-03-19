<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'vue'

interface BubbleProps {
  type: 'ai' | 'user'
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<BubbleProps>(), {
  type: 'user'
})
</script>

<template>
  <div :class="cn(
    'flex w-full',
    props.type === 'user' ? 'justify-end' : 'justify-start',
    props.class
  )">
    <div :class="cn(
      'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
      props.type === 'user'
        ? 'bg-primary text-primary-foreground'
        : 'bg-muted text-foreground'
    )">
      <slot />
    </div>
  </div>
</template>