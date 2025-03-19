<script lang="ts">
export const description = 'A sidebar with a collapsible file tree.'
export const iframeHeight = '800px'
</script>
<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import Files from '@/components/Files.vue'
</script>
<template>
  <SidebarProvider>
    <Files />
    <SidebarInset>
      <div class="border-red-500 w-full h-full"></div>
    </SidebarInset>
  </SidebarProvider>
</template>