<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '@/components/ui/button'

const currentStep = ref(1)
const fileUploaded = ref(true)
const question = ref('')

const nextStep = () => {
  if (currentStep.value < 2)
    currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 1)
    currentStep.value--
}

const handleSubmit = () => {
  // 处理提交逻辑
  console.log('提交')
}
</script>

<template>
  <div class="w-full max-w-xl mx-auto">
    <div class="border rounded-lg shadow-sm">
      <!-- Step 1: File Upload -->
      <div v-if="currentStep === 1" class="p-6">
        <slot name="file-upload" />
        <div class="mt-4 flex justify-end">
          <Button :disabled="!fileUploaded" @click="nextStep" size="sm">
            下一步
          </Button>
        </div>
      </div>

      <!-- Step 2: Question Input -->
      <div v-if="currentStep === 2" class="p-6">
        <slot name="question-input" />
        <div class="mt-4 flex justify-between">
          <Button variant="outline" @click="prevStep" size="sm">
            上一步
          </Button>
          <Button @click="handleSubmit" size="sm">
            开始分析
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>