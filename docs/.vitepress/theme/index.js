import DefaultTheme from 'vitepress/theme'
import Layout from './Layout.vue'
import SiteImage from './components/SiteImage.vue'
import SiteLink from './components/SiteLink.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('SiteImage', SiteImage)
    app.component('SiteLink', SiteLink)
  }
}
