<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { marked } from 'marked';

interface ContentSection {
  id: number;
  content: string;
  renderedContent: string;
}

const sections = ref<ContentSection[]>([]);
let nextId = 0;

// 添加新的内容段落
const appendContent = async (content: string) => {
  const renderedContent = await marked(content);
  sections.value.push({
    id: nextId++,
    content,
    renderedContent
  });
};

// 初始化示例内容
onMounted(async () => {
  // 模拟后端分段发送内容
  await appendContent(`# 数学建模比赛论文`);

  await appendContent(`## 摘要
本文主要研究了...`);

  await appendContent(`## 1. 问题重述
### 1.1 背景介绍
在当今快速发展的科技时代...`);

  await appendContent(`### 1.2 问题分析
根据题目要求，我们需要解决以下关键问题：
1. 第一个关键问题
2. 第二个关键问题
3. 第三个关键问题`);
});
</script>

<template>
  <div class="h-full overflow-hidden bg-gray-50">
    <div class="h-full overflow-y-auto p-6">
      <div class="max-w-4xl mx-auto space-y-6">
        <TransitionGroup name="section" tag="div" class="space-y-6">
          <div v-for="section in sections" :key="section.id"
            class="bg-white rounded-lg shadow-lg overflow-hidden transform transition-all duration-500">
            <div class="p-6">
              <div class="prose prose-slate max-w-none" v-html="section.renderedContent"></div>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>
  </div>
</template>

<style>
.section-enter-active,
.section-leave-active {
  transition: all 0.5s ease;
}

.section-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.section-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.prose {
  @apply text-gray-800;
}

.prose h1 {
  @apply text-3xl font-bold mb-6 text-gray-900;
}

.prose h2 {
  @apply text-2xl font-semibold mt-4 mb-4 text-gray-800;
}

.prose h3 {
  @apply text-xl font-semibold mt-3 mb-3 text-gray-800;
}

.prose p {
  @apply mb-4 leading-relaxed;
}

.prose ul {
  @apply list-disc ml-6 mb-4 space-y-2;
}

.prose ol {
  @apply list-decimal ml-6 mb-4 space-y-2;
}

.prose blockquote {
  @apply border-l-4 border-gray-300 pl-4 italic my-4 text-gray-600;
}

.prose a {
  @apply text-blue-600 hover:text-blue-800 underline;
}

.prose hr {
  @apply my-8 border-gray-200;
}

.prose table {
  @apply w-full border-collapse border border-gray-300 my-4;
}

.prose th,
.prose td {
  @apply border border-gray-300 p-2;
}

.prose thead {
  @apply bg-gray-50;
}
</style>