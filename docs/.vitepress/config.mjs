import { defineConfig } from 'vitepress'

const repositoryName = process.env.GITHUB_REPOSITORY?.split('/')[1]
const base =
  process.env.GITHUB_ACTIONS === 'true' && repositoryName
    ? `/${repositoryName}/`
    : '/'

export default defineConfig({
  base,
  lang: 'zh-CN',
  title: '后互联网时代的乱弹',
  description: '播客字幕 VitePress 阅读站',
  cleanUrls: true,
  themeConfig: {
    siteTitle: '后互联网时代的乱弹',
    nav: [
      { text: '节目目录', link: '/' }
    ],
    search: {
      provider: 'local'
    }
  }
})
