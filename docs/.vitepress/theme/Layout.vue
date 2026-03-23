<script setup>
import DefaultTheme from 'vitepress/theme'
import { nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vitepress'

const { Layout } = DefaultTheme
const route = useRoute()

let cleanup = () => {}

function scrollToElement(target, behavior = 'smooth') {
  if (!target) return
  const offset = 96
  const top = target.getBoundingClientRect().top + window.scrollY - offset
  window.scrollTo({ top: Math.max(0, top), behavior })
}

function bindIndexFilter() {
  const input = document.querySelector('[data-episode-filter]')
  if (!input) return () => {}

  const cards = Array.from(document.querySelectorAll('[data-episode-card]'))
  const handleInput = () => {
    const query = input.value.trim().toLowerCase()
    for (const card of cards) {
      const haystack = (card.dataset.filter || '').toLowerCase()
      card.classList.toggle('is-hidden', Boolean(query) && !haystack.includes(query))
    }
  }

  input.addEventListener('input', handleInput)
  return () => input.removeEventListener('input', handleInput)
}

function bindTranscriptPlayer() {
  const page = document.querySelector('[data-transcript-page]')
  if (!page) return () => {}

  const audio = page.querySelector('[data-audio]')
  const buttons = Array.from(page.querySelectorAll('[data-seek]'))
  const blocks = Array.from(page.querySelectorAll('[data-block]'))
  const buttonHandlers = []

  for (const button of buttons) {
    const handler = () => {
      if (!audio) return
      const seconds = Number(button.dataset.seek || '0')
      audio.currentTime = seconds
      audio.play().catch(() => {})
    }
    button.addEventListener('click', handler)
    buttonHandlers.push([button, handler])
  }

  if (!audio || !blocks.length) {
    return () => {
      for (const [button, handler] of buttonHandlers) {
        button.removeEventListener('click', handler)
      }
    }
  }

  let lastActive = null
  const handleTimeUpdate = () => {
    const now = audio.currentTime
    let active = null

    for (const block of blocks) {
      const start = Number(block.dataset.start || '0')
      const end = Number(block.dataset.end || '0')
      const isActive = now >= start && now < end
      block.classList.toggle('is-active', isActive)
      if (isActive) active = block
    }

    if (active && active !== lastActive) {
      lastActive = active
      const top = active.getBoundingClientRect().top
      const inViewport = top > 120 && top < window.innerHeight - 120
      if (!inViewport) {
        active.scrollIntoView({ block: 'center', behavior: 'smooth' })
      }
    }
  }

  audio.addEventListener('timeupdate', handleTimeUpdate)

  return () => {
    for (const [button, handler] of buttonHandlers) {
      button.removeEventListener('click', handler)
    }
    audio.removeEventListener('timeupdate', handleTimeUpdate)
  }
}

function bindTranscriptNavigation() {
  const page = document.querySelector('[data-transcript-page]')
  if (!page) return () => {}

  const links = Array.from(page.querySelectorAll('.vp-transcript-section-nav a[href^="#"]'))
  const backToTop = page.querySelector('[data-scroll-top]')
  const blocks = Array.from(page.querySelectorAll('[data-block]'))
  const linkHandlers = []

  const updateActiveLink = () => {
    const currentY = window.scrollY + 140
    let currentId = ''

    for (const block of blocks) {
      const top = block.getBoundingClientRect().top + window.scrollY
      if (top <= currentY && block.id) {
        currentId = block.id
      }
    }

    for (const link of links) {
      link.classList.toggle('is-active', link.getAttribute('href') === `#${currentId}`)
    }
  }

  for (const link of links) {
    const handler = (event) => {
      event.preventDefault()
      const hash = link.getAttribute('href')
      if (!hash) return
      const target = document.querySelector(hash)
      if (!target) return
      history.replaceState(null, '', hash)
      scrollToElement(target)
      updateActiveLink()
    }
    link.addEventListener('click', handler)
    linkHandlers.push([link, handler])
  }

  const handleTopClick = () => {
    history.replaceState(null, '', window.location.pathname + window.location.search)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleScroll = () => {
    if (backToTop) {
      backToTop.classList.toggle('is-visible', window.scrollY > 480)
    }
    updateActiveLink()
  }

  if (backToTop) {
    backToTop.addEventListener('click', handleTopClick)
  }

  if (window.location.hash) {
    const target = document.querySelector(window.location.hash)
    if (target) {
      requestAnimationFrame(() => scrollToElement(target, 'auto'))
    }
  }

  handleScroll()
  window.addEventListener('scroll', handleScroll, { passive: true })

  return () => {
    for (const [link, handler] of linkHandlers) {
      link.removeEventListener('click', handler)
    }
    if (backToTop) {
      backToTop.removeEventListener('click', handleTopClick)
    }
    window.removeEventListener('scroll', handleScroll)
  }
}

async function setupPageInteractions() {
  cleanup()
  await nextTick()
  const cleanups = [bindIndexFilter(), bindTranscriptPlayer(), bindTranscriptNavigation()]
  cleanup = () => {
    for (const fn of cleanups) {
      fn()
    }
  }
}

onMounted(setupPageInteractions)
watch(() => route.path, setupPageInteractions)
onUnmounted(() => cleanup())
</script>

<template>
  <Layout />
</template>
