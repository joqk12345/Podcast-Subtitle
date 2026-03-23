<script setup>
import { computed, useAttrs } from 'vue'
import { withBase } from 'vitepress'

const props = defineProps({
  src: {
    type: String,
    required: true
  }
})

const attrs = useAttrs()

const resolvedSrc = computed(() => {
  if (!props.src.startsWith('/')) return props.src
  return withBase(props.src)
})
</script>

<template>
  <img v-bind="attrs" :src="resolvedSrc">
</template>
