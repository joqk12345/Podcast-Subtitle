# Podcast-Subtitle

为 “后互联网时代的乱弹” 播客提供字幕内容，喜欢听音频的朋友请移步到[主站](https://hosting.wavpub.cn/pie/)、[B站](https://space.bilibili.com/760331/channel/collectiondetail?sid=276050/)、[RSS](https://proxy.wavpub.com/pie.xml)。最新导航见 `pie-podcast-nav-v2.md`，已更新至第196期。


# 采用的开源项目

1. Whisper 是 OpenAI 推出的语音转换文字的人工智能工具包，支持很多种语言，目前本repo采用 OpenAI whisper  large 模型。具体whisper详细内容请参考[Whisper](https://github.com/openai/whisper/)。
2. pie-podcast-nav-v2 采用1000h aishell的数据采用LoRA finetune技术对中文进行finetune.

# 目录
1. [后互联网时代的乱弹-导航（v2）](./pie-podcast-nav-v2.md)
2. [每个音频明细](./pie-srt/duration.csv)
3. [导航更新工具说明](./scripts/update_nav_v2_usage.md)
4. `scripts/build_transcript_site.py`：把 `pie-podcast-nav-v2.md` 和 `pie-srt/v2/*.srt` 生成成一个适合外部分享的静态字幕阅读站，输出目录默认是 `transcript-site/`
5. `scripts/build_vitepress_site.py`：把同一批数据生成成 `docs/` 下的 VitePress 站点源码

# 更新
1. 支持了字幕(SRT/Subtitle)；
2. 同时支持了Markdown & Html格式；
3. 导航更新至第194期，补充第188-193期字幕条目。

# 字幕阅读站原型

当前仓库已经有 `SRT / Markdown / HTML` 三种导出，但都更偏“存档”，不太适合作为对外阅读页。新增的生成脚本会做两件事：

1. 保留原始音频与时间轴；
2. 把过碎的句级字幕合并成段落级阅读块，并生成目录页与单集页。

生成方法：

```bash
python3 scripts/build_transcript_site.py
```

可选参数：

```bash
python3 scripts/build_transcript_site.py --limit 8
python3 scripts/build_transcript_site.py --output ./some-dir
```

# VitePress 站点

如果希望把字幕站作为一个完整文档站来部署，当前推荐走 VitePress：

```bash
npm install
npm run docs:dev
```

正式构建：

```bash
npm run docs:build
```

这套命令会先运行 `scripts/build_vitepress_site.py`，再把 `docs/` 里的页面交给 VitePress 构建。

## GitHub Pages 发布

仓库已经可以直接走 GitHub Actions 发布 VitePress 页面。

```bash
npm install
npm run docs:build
```

推送到 `main` 后，`.github/workflows/deploy-pages.yml` 会自动构建并发布到 GitHub Pages。首次启用时，到仓库 `Settings -> Pages` 把 `Source` 设为 `GitHub Actions` 即可。

# 贡献
1. 欢迎大家提issues、pr。
