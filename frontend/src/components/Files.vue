<script setup lang="ts">
import { computed } from 'vue'
import Tree from '@/components/Tree.vue'
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
} from '@/components/ui/sidebar'
import { File } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()

// 从消息中提取最新的文件列表
const files = taskStore.files

// 将文件列表转换为树形结构
const fileTree = computed(() => {
  return files.map(file => file)
})

const handleFileClick = (file: string) => {
  // 处理文件点击
  console.log('File clicked:', file)
}

const handleFileDownload = (file: string) => {
  // 处理文件下载
  console.log('Download file:', file)
}
</script>

<template>
  <div class="h-full">
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Files</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <div v-if="fileTree.length === 0" class="px-4 py-2 text-sm text-gray-500">
              No files
            </div>
            <Tree v-else v-for="(item, index) in fileTree" :key="index" :item="item" @click="handleFileClick(item)"
              @download="handleFileDownload(item)" />
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  </div>
</template>
