<script setup lang="ts">


import AppSidebar from '@/components/AppSidebar.vue'
import UserStepper from '@/components/UserStepper.vue'
import { ref, onMounted } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FileUp } from 'lucide-vue-next'
import { getHelloWorld } from '@/apis/commonApi'
import { submitModelingTask } from '@/apis/submitModelingApi'

const uploadedFile = ref<File | null>(null)
const question = ref('')

const selectConfig = [
  {
    key: '模板',
    label: '选择模板',
    options: ['国赛', '美赛'],
  },
  {
    key: '语言',
    label: '选择语言',
    options: ['中文', '英文'],
  },
  {
    key: '格式',
    label: '选择格式',
    options: ['Markdown', 'LaTeX'],
  },
]

const selectedOptions = ref({
  template: '',
  language: '',
  format: '',
})

// 处理文件上传
const handleFileUpload = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    uploadedFile.value = input.files[0]
  }
}

// 提交任务
const handleSubmit = async () => {
  if (!uploadedFile.value || !question.value) {
    alert('请上传文件并输入问题')
    return
  }

  try {
    const response = await submitModelingTask(
      {
        task_id: `task_${Date.now()}`,
        ques_all: question.value,
        comp_template: selectedOptions.value.template.toUpperCase(),
        format_output: selectedOptions.value.format.toUpperCase()
      },
      [uploadedFile.value]
    )

    console.log('任务提交成功:', response.data)
    // 这里可以添加跳转或状态更新逻辑
  } catch (error) {
    console.error('任务提交失败:', error)
    alert('任务提交失败，请重试')
  }
}

onMounted(() => {
  getHelloWorld().then((res) => {
    console.log(res.data)
  })
})
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset>
      <header class="flex h-16 shrink-0 items-center gap-2 px-4">
        <SidebarTrigger class="-ml-1" />
      </header>

      <div class="py-5 px-4">
        <div class="space-y-6">
          <div class="text-center space-y-2 mb-10">
            <h1 class="text-2xl font-semibold">数模竞赛助手</h1>
            <p class="text-muted-foreground">
              让 AI 自主数学建模，代码撰写，论文写作
            </p>
          </div>

          <UserStepper>
            <template #file-upload>
              <div
                class="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
                @click="() => $refs.fileInput?.click()">
                <input type="file" ref="fileInput" class="hidden" @change="handleFileUpload" accept=".txt,.csv,.xlsx">
                <div class="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <FileUp class="w-6 h-6 text-primary" />
                </div>
                <div>
                  <p class="text-lg font-medium">拖拽数据集到此处或点击上传</p>
                  <p class="text-sm text-muted-foreground mt-1">
                    支持 .txt, .csv, .xlsx 等格式文件
                  </p>
                  <p v-if="uploadedFile" class="text-sm text-green-600 mt-1">
                    已上传文件: {{ uploadedFile.name }}
                  </p>
                </div>
              </div>
            </template>

            <template #question-input>
              <div class="space-y-4">
                <div class="space-y-1">
                  <h4 class="text-sm font-medium mb-2">粘贴完整题目</h4>
                  <Textarea v-model="question" placeholder="PDF 中完整题目背景和多个小问" class="min-h-[120px]" />
                </div>

                <div class="grid grid-cols-3 gap-3">
                  <div v-for="item in selectConfig" :key="item.key">
                    <Select v-model="selectedOptions[item.key.toLowerCase() as keyof typeof selectedOptions]">
                      <SelectTrigger class="h-9">
                        <SelectValue :placeholder="item.label" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectLabel>{{ item.key }}</SelectLabel>
                          <SelectItem v-for="option in item.options" :key="option" :value="option.toLowerCase()">
                            {{ option }}
                          </SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </template>
          </UserStepper>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
