<script setup lang="ts">
import { QQ_GROUP, TWITTER, GITHUB_LINK, BILLBILL, XHS, DISCORD } from '@/utils/const'
import NavUser from './NavUser.vue'
import { onMounted, reactive } from 'vue'
import { getTasks } from '@/apis/commonApi'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  type SidebarProps,
  SidebarRail,
} from '@/components/ui/sidebar'

const props = defineProps<SidebarProps>()

// 动态数据：开始 & 历史任务
const data = reactive({
  navMain: [
    {
      title: '开始',
      url: '#',
      items: [
        {
          title: '开始新任务',
          url: '/chat',
          isActive: false,
        },
      ],
    },
    {
      title: '历史任务',
      url: '#',
      items: [] as { title: string; url: string; isActive?: boolean }[],
    },
  ],
})

function statusLabel(s?: string) {
  const m: Record<string, string> = {
    created: '未开始',
    running: '进行中',
    stopped: '已停止',
    completed: '已完成',
    failed: '失败',
    pending: '未开始',
  }
  return m[s || 'completed'] || '已完成'
}

function statusClass(s?: string) {
  const m: Record<string, string> = {
    created: 'bg-gray-100 text-gray-700',
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-emerald-100 text-emerald-700',
    stopped: 'bg-orange-100 text-orange-700',
    completed: 'bg-sky-100 text-sky-700',
    failed: 'bg-rose-100 text-rose-700',
  }
  return m[s || 'completed'] || m.completed
}

onMounted(async () => {
  try {
    const res = await getTasks()
    const tasks = Array.isArray(res.data) ? res.data : []
    data.navMain[1].items = tasks.map(t => ({
      title: `${t.task_id}`,
      url: `/task/${t.task_id}`,
      isActive: false,
      status: t.status || 'completed',
    }))
  } catch (e) {
    // 静默失败，保持空列表
    console.warn('加载历史任务失败', e)
  }
})


const socialMedia = [
  {
    name: 'QQ',
    url: QQ_GROUP,
    icon: '/qq.svg',
  },
  {
    name: 'Twitter',
    url: TWITTER,
    icon: '/twitter.svg',
  },
  {
    name: 'GitHub',
    url: GITHUB_LINK,
    icon: '/github.svg',
  },
  {
    name: '哔哩哔哩',
    url: BILLBILL,
    icon: '/bilibili.svg',
  },
  {
    name: '小红书',
    url: XHS,
    icon: '/xiaohongshu.svg',
  },
  {
    name: 'Discord',
    url: DISCORD,
    icon: '/discord.svg',
  },
]

</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <!-- 图标 -->
      <div class="flex items-center gap-2 h-15">
        <router-link to="/" class="flex items-center gap-2">
          <img src="@/assets/icon.png" alt="logo" class="w-10 h-10">
          <div class="text-lg font-bold">MathModelAgent</div>
        </router-link>
      </div>
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup v-for="item in data.navMain" :key="item.title">
        <SidebarGroupLabel>{{ item.title }}</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="childItem in item.items" :key="childItem.title">
              <SidebarMenuButton as-child :is-active="childItem.isActive">
                <router-link :to="childItem.url" class="flex items-center justify-between w-full">
                  <span>{{ childItem.title }}</span>
                  <span v-if="childItem.status" class="text-[10px] px-2 py-0.5 rounded ml-2" :class="statusClass(childItem.status)">
                    {{ statusLabel(childItem.status) }}
                  </span>
                </router-link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    <SidebarRail />
    <SidebarFooter>
      <NavUser />
    </SidebarFooter>
    <SidebarFooter>
      <!-- 展示图标社交媒体  -->
      <div class="flex items-center gap-4 justify-centermb-4 border-t  border-light-purple pt-3">
        <a v-for="item in socialMedia" :href="item.url" target="_blank">
          <img :src="item.icon" :alt="item.name" width="24" height="24" class="icon">
        </a>
      </div>
    </SidebarFooter>
  </Sidebar>
</template>
