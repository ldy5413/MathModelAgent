<script setup lang="ts">
import Tree from '@/components/Tree.vue'
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
} from '@/components/ui/sidebar'
import { File } from 'lucide-vue-next'

// This is sample data.
const data = {
  changes: [
    {
      file: 'README.md',
      state: 'M',
    },
    {
      file: 'api/hello/route.ts',
      state: 'U',
    },
    {
      file: 'app/layout.tsx',
      state: 'M',
    },
  ],
  tree: [
    [
      'app',
      [
        'api',
        ['hello', ['route.ts']],
        'page.tsx',
        'layout.tsx',
        ['blog', ['page.tsx']],
      ],
    ],
    [
      'components',
      ['ui', 'button.tsx', 'card.tsx'],
      'header.tsx',
      'footer.tsx',
    ],
    ['lib', ['util.ts']],
    ['public', 'favicon.ico', 'vercel.svg'],
    '.eslintrc.json',
    '.gitignore',
    'next.config.js',
    'tailwind.config.js',
    'package.json',
    'README.md',
  ],
}
</script>

<template>
  <div class="h-full">
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Files</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <Tree v-for="(item, index) in data.tree" :key="index" :item="item" />
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  </div>
</template>
