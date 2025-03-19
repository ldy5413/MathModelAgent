<script setup lang="ts">

import { ref } from 'vue';
import { MdEditor } from 'md-editor-v3';
import 'md-editor-v3/lib/style.css';

const text = ref('Hello Editor!');
const toolbars = ['italic', 'underline', '-', 'bold', '='];
</script>

<template>
  <div class="h-screen">
    <MdEditor v-model="text" :toolbars="toolbars" class="" />
  </div>
</template>