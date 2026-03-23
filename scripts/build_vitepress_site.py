#!/usr/bin/env python3
from __future__ import annotations

import html
import shutil
from datetime import datetime
from pathlib import Path

import build_transcript_site as core


DOCS_ROOT = core.ROOT / "docs"
EPISODES_ROOT = DOCS_ROOT / "episodes"
PUBLIC_SRT_ROOT = DOCS_ROOT / "public" / "pie-srt" / "v2"
PUBLIC_WORDCLOUD_ROOT = DOCS_ROOT / "public" / "wordclouds"


def yaml_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def build_docs_root() -> None:
    if EPISODES_ROOT.exists():
        shutil.rmtree(EPISODES_ROOT)
    if PUBLIC_SRT_ROOT.exists():
        shutil.rmtree(PUBLIC_SRT_ROOT)
    if PUBLIC_WORDCLOUD_ROOT.exists():
        shutil.rmtree(PUBLIC_WORDCLOUD_ROOT)
    EPISODES_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLIC_SRT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLIC_WORDCLOUD_ROOT.mkdir(parents=True, exist_ok=True)


def render_index(episodes: list[core.Episode]) -> str:
    cards = "\n".join(render_episode_card(episode) for episode in episodes)
    total_blocks = sum(len(episode.blocks) for episode in episodes)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""---
layout: page
title: 字幕阅读站
titleTemplate: false
---

<div class="vp-transcript-home">
  <section class="vp-transcript-hero">
    <p class="vp-transcript-eyebrow">VitePress Transcript Reader</p>
    <h1>后互联网时代的乱弹</h1>
    <p class="vp-transcript-copy">这不是把字幕硬塞进文档站，而是用 VitePress 管理目录、搜索和部署，同时保留播客字幕应有的时间轴阅读体验。</p>
    <div class="vp-transcript-stats">
      <div><span>{len(episodes)}</span><small>集数</small></div>
      <div><span>{total_blocks}</span><small>阅读段落</small></div>
      <div><span>{generated_at}</span><small>生成时间</small></div>
    </div>
    <div class="vp-transcript-search">
      <label for="episode-filter">快速筛选</label>
      <input id="episode-filter" data-episode-filter type="search" placeholder="输入期号、标题或关键词">
    </div>
  </section>

  <section class="vp-transcript-section">
    <h2>节目目录</h2>
    <p class="vp-transcript-note">每一集都保留原始音频入口、原始 SRT 下载，以及按时间聚合后的阅读稿。</p>
  </section>

  <section class="vp-transcript-grid">
    {cards}
  </section>
</div>
"""


def render_episode_card(episode: core.Episode) -> str:
    preview = html.escape(core.build_preview(episode.blocks))
    filter_text = html.escape(f"{episode.title} {preview}".lower())
    title = html.escape(episode.title)
    duration = core.format_seconds(episode.duration_seconds)
    return f"""
<article class="vp-transcript-card" data-episode-card data-filter="{filter_text}">
  <p class="vp-transcript-meta">{duration} · {len(episode.blocks)} 段</p>
  <h3><SiteLink href="/episodes/{episode.slug}">{title}</SiteLink></h3>
  <p class="vp-transcript-summary">{preview}</p>
  <div class="vp-transcript-links">
    <SiteLink class="vp-transcript-button" href="/episodes/{episode.slug}">阅读字幕</SiteLink>
    <a class="vp-transcript-button is-subtle" href="{html.escape(episode.audio_url)}" target="_blank" rel="noreferrer">原始音频</a>
  </div>
</article>
"""


def render_episode_page(episode: core.Episode) -> str:
    title = html.escape(episode.title)
    sections = "\n".join(render_section_link(block) for block in episode.blocks if block.section_id)
    timeline = "\n".join(
        render_block(block, index) for index, block in enumerate(episode.blocks, start=1)
    )
    duration = core.format_seconds(episode.duration_seconds)
    subtitle_url = f"/pie-srt/v2/{episode.subtitle_file.name}"
    wordcloud_url = f"/wordclouds/{episode.slug}.svg"
    return f"""---
layout: page
title: {yaml_quote(episode.title)}
description: {yaml_quote('播客字幕阅读页')}
titleTemplate: false
outline: false
aside: false
lastUpdated: false
---

<div class="vp-transcript-page" data-transcript-page>
  <SiteLink class="vp-transcript-back" href="/">返回目录</SiteLink>

  <section class="vp-transcript-hero">
    <p class="vp-transcript-eyebrow">Episode Transcript</p>
    <h1>{title}</h1>
    <p class="vp-transcript-copy">本页由原始 SRT 自动整理。规则是保留时间轴，但把过碎的句级字幕合并成段落级阅读块。</p>
    <div class="vp-transcript-facts">
      <div><span>{duration}</span><small>时长</small></div>
      <div><span>{len(episode.cues)}</span><small>SRT 条目</small></div>
      <div><span>{len(episode.blocks)}</span><small>阅读段落</small></div>
    </div>
  </section>

  <section class="vp-transcript-panel">
    <audio data-audio controls preload="none" src="{html.escape(episode.audio_url)}"></audio>
    <div class="vp-transcript-player-links">
      <a class="vp-transcript-button" href="{html.escape(episode.audio_url)}" target="_blank" rel="noreferrer">在新窗口打开音频</a>
      <SiteLink class="vp-transcript-button is-subtle" href="{subtitle_url}" target="_blank" rel="noreferrer">查看原始 SRT</SiteLink>
    </div>
  </section>

  <section class="vp-transcript-wordcloud-panel">
    <div class="vp-transcript-wordcloud-copy">
      <p class="vp-transcript-eyebrow">Word Cloud</p>
      <h2>主题词云</h2>
      <p class="vp-transcript-note">基于全文高频词生成，帮助快速扫一眼这期节目的关键词分布。</p>
    </div>
    <SiteLink class="vp-transcript-wordcloud-link" href="{wordcloud_url}" target="_blank" rel="noreferrer">
      <SiteImage class="vp-transcript-wordcloud" src="{wordcloud_url}" alt="{title} 词云图" loading="lazy" />
    </SiteLink>
  </section>

  <div class="vp-transcript-layout">
    <aside class="vp-transcript-sidebar">
      <div class="vp-transcript-sidebar-card">
        <h2>时间导航</h2>
        <nav class="vp-transcript-section-nav">
          {sections}
        </nav>
      </div>
    </aside>
<div class="vp-transcript-timeline">
{timeline}
</div>
  </div>

  <button class="vp-transcript-top" data-scroll-top type="button" aria-label="回到顶部">回到顶部</button>
</div>
"""


def render_section_link(block: core.Block) -> str:
    if not block.section_id or not block.section_label:
        return ""
    return (
        f'<a href="#{block.section_id}">{html.escape(block.section_label)} '
        f'<small>{core.format_seconds(block.start)}</small></a>'
    )


def render_block(block: core.Block, index: int) -> str:
    anchor = f' id="{block.section_id}"' if block.section_id else ""
    text = html.escape(block.text)
    start = core.format_seconds(block.start)
    end = core.format_seconds(block.end)
    return f"""
<article class="vp-transcript-block"{anchor} data-block data-start="{int(block.start)}" data-end="{int(block.end) + 1}">
  <button class="vp-transcript-timestamp" data-seek="{int(block.start)}" type="button">{start}</button>
  <div>
    <p class="vp-transcript-index">第 {index} 段 · {start} - {end}</p>
    <p>{text}</p>
  </div>
</article>
"""


def write_docs(episodes: list[core.Episode]) -> None:
    (DOCS_ROOT / "index.md").write_text(render_index(episodes), encoding="utf-8")
    for episode in episodes:
        (EPISODES_ROOT / f"{episode.slug}.md").write_text(
            render_episode_page(episode),
            encoding="utf-8",
        )
        subtitle_text = episode.subtitle_file.read_text(encoding="utf-8-sig")
        (PUBLIC_SRT_ROOT / episode.subtitle_file.name).write_text(
            subtitle_text,
            encoding="utf-8-sig",
        )
        (PUBLIC_WORDCLOUD_ROOT / f"{episode.slug}.svg").write_text(
            core.build_wordcloud_svg(episode),
            encoding="utf-8",
        )


def main() -> None:
    nav_items = core.parse_nav(core.DEFAULT_NAV)
    episodes = core.build_episodes(nav_items)
    build_docs_root()
    write_docs(episodes)
    print(f"generated {len(episodes)} VitePress pages under {DOCS_ROOT}")


if __name__ == "__main__":
    main()
