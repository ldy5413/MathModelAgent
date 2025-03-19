<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const content = ref('在这里开始写作...')
</script>

<template>
  <div class="flex h-full flex-col space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <Button variant="outline" size="sm">保存</Button>
        <Button variant="outline" size="sm">导出</Button>
      </div>
      <div class="flex items-center space-x-2">
        <Button variant="outline" size="sm">格式化</Button>
        <Button variant="outline" size="sm">预览</Button>
      </div>
    </div>

    <div class="flex-1 rounded-lg border bg-card">
      <Textarea v-model="content" class="h-full resize-none text-base" placeholder="在这里开始写作..." />
    </div>
  </div>
</template>