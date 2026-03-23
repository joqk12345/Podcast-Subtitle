<script setup>
import { computed, useAttrs } from 'vue'
import { withBase } from 'vitepress'

const props = defineProps({
  href: {
    type: String,
    required: true
  }
})

const attrs = useAttrs()

const resolvedHref = computed(() => {
  if (!props.href.startsWith('/')) return props.href
  return withBase(props.href)
})
</script>

<template>
  <a v-bind="attrs" :href="resolvedHref">
    <slot />
  </a>
</template>
