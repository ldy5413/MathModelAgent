<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'vue'
import { marked } from 'marked'
import { computed } from 'vue'

interface BubbleProps {
  type: 'ai' | 'user'
  class?: HTMLAttributes['class']
  content: string
}

const props = withDefaults(defineProps<BubbleProps>(), {
  type: 'user'
})

const renderedContent = computed(() => {
  return marked.parse(props.content)
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
        ? 'bg-primary text-primary-foreground prose-invert'
        : 'bg-muted text-foreground',
      'prose prose-sm prose-slate max-w-none'
    )">
      <div v-html="renderedContent"></div>
    </div>
  </div>
</template>

<style>
.prose {
  @apply text-inherit;
}

.prose p {
  @apply my-1;
}

.prose p:not(:first-child) {
  @apply mt-1;
}

.prose h1,
.prose h2,
.prose h3,
.prose h4 {
  @apply my-1 font-semibold;
}

.prose h1 {
  @apply text-lg;
}

.prose h2 {
  @apply text-base;
}

.prose h3,
.prose h4 {
  @apply text-sm;
}

.prose ul,
.prose ol {
  @apply my-1 pl-4;
}

.prose ul {
  @apply list-disc;
}

.prose ol {
  @apply list-decimal;
}

.prose li {
  @apply my-0.5;
}

.prose code {
  @apply px-1 py-0.5 rounded bg-black/10 dark:bg-white/10;
}

.prose pre {
  @apply p-2 my-1 rounded bg-black/10 dark:bg-white/10 overflow-x-auto;
}

.prose pre code {
  @apply bg-transparent p-0;
}

.prose blockquote {
  @apply my-1 pl-3 border-l-2 border-current opacity-80 italic;
}

.prose a {
  @apply underline underline-offset-2 opacity-80 hover:opacity-100;
}

.prose img {
  @apply my-1 rounded-lg;
}

.prose table {
  @apply my-1 w-full;
}

.prose thead {
  @apply border-b border-current opacity-20;
}

.prose th {
  @apply p-2 text-left font-semibold;
}

.prose td {
  @apply p-2 border-t border-current opacity-10;
}

.prose-invert {
  @apply text-primary-foreground;
}

/* 确保透明度样式不会被继承 */
.prose thead *,
.prose td * {
  @apply opacity-100;
}
</style>