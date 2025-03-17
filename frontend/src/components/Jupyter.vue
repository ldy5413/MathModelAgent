<template>
  <div class="home">
    <RenderJupyterNotebook :notebook="notebook" />
  </div>
</template>

<script setup>
import RenderJupyterNotebook from 'render-jupyter-notebook-vue'
import example from '../assets/OutputExamples.json'
import { ref } from 'vue'

const notebook = ref(example)
</script>