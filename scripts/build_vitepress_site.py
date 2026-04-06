#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import shutil
from datetime import datetime
from pathlib import Path

import build_transcript_site as core


DEFAULT_DOCS_ROOT = core.ROOT / "docs"


def yaml_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or append VitePress transcript pages from nav markdown and SRT files."
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=DEFAULT_DOCS_ROOT,
        help=f"Docs directory to write. Default: {DEFAULT_DOCS_ROOT}",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--append-new",
        action="store_true",
        help="Only append the latest episodes that do not yet exist under docs/episodes.",
    )
    mode_group.add_argument(
        "--fill-missing",
        action="store_true",
        help="Scan all episodes and fill only the missing docs pages, public SRT files, wordclouds, and index cards.",
    )
    mode_group.add_argument(
        "--episode",
        action="append",
        default=[],
        metavar="SLUG",
        help="Force rebuild a specific episode slug, e.g. ep-207. Repeat the flag to rebuild multiple episodes.",
    )
    mode_group.add_argument(
        "--srt",
        action="append",
        default=[],
        metavar="FILE",
        help="Force rebuild by SRT file, e.g. pie-ep207.mp3.srt or ./pie-srt/v2/pie-ep207.mp3.srt. Repeat the flag to rebuild multiple episodes.",
    )
    return parser.parse_args()


def get_docs_paths(docs_root: Path) -> tuple[Path, Path, Path]:
    episodes_root = docs_root / "episodes"
    public_srt_root = docs_root / "public" / "pie-srt" / "v2"
    public_wordcloud_root = docs_root / "public" / "wordclouds"
    return episodes_root, public_srt_root, public_wordcloud_root


def build_docs_root(docs_root: Path) -> None:
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    if episodes_root.exists():
        shutil.rmtree(episodes_root)
    if public_srt_root.exists():
        shutil.rmtree(public_srt_root)
    if public_wordcloud_root.exists():
        shutil.rmtree(public_wordcloud_root)
    episodes_root.mkdir(parents=True, exist_ok=True)
    public_srt_root.mkdir(parents=True, exist_ok=True)
    public_wordcloud_root.mkdir(parents=True, exist_ok=True)


def ensure_docs_root(docs_root: Path) -> None:
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    docs_root.mkdir(parents=True, exist_ok=True)
    episodes_root.mkdir(parents=True, exist_ok=True)
    public_srt_root.mkdir(parents=True, exist_ok=True)
    public_wordcloud_root.mkdir(parents=True, exist_ok=True)


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
    <details class="vp-transcript-wordcloud-details" data-wordcloud-details open>
      <summary class="vp-transcript-wordcloud-summary">
        <div class="vp-transcript-wordcloud-copy">
          <p class="vp-transcript-eyebrow">Word Cloud</p>
          <h2>概念词云</h2>
          <p class="vp-transcript-note">默认展开，需要时可以折叠起来节省页面空间。</p>
        </div>
        <span class="vp-transcript-wordcloud-toggle" data-wordcloud-toggle>收起</span>
      </summary>
      <div class="vp-transcript-wordcloud-content">
        <SiteLink class="vp-transcript-wordcloud-link" href="{wordcloud_url}" target="_blank" rel="noreferrer">
          <SiteImage class="vp-transcript-wordcloud" src="{wordcloud_url}" alt="{title} 概念词云" loading="lazy"></SiteImage>
        </SiteLink>
      </div>
    </details>
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


def write_episode_assets(episode: core.Episode, docs_root: Path) -> None:
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    (episodes_root / f"{episode.slug}.md").write_text(
        render_episode_page(episode),
        encoding="utf-8",
    )
    subtitle_text = episode.subtitle_file.read_text(encoding="utf-8-sig")
    (public_srt_root / episode.subtitle_file.name).write_text(
        subtitle_text,
        encoding="utf-8-sig",
    )
    (public_wordcloud_root / f"{episode.slug}.svg").write_text(
        core.build_wordcloud_svg(episode, kind="concept", background="#f7fbfb"),
        encoding="utf-8",
    )


def write_missing_episode_assets(episode: core.Episode, docs_root: Path) -> dict[str, int]:
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    written = {"pages": 0, "srts": 0, "wordclouds": 0}

    episode_page = episodes_root / f"{episode.slug}.md"
    if not episode_page.exists():
        episode_page.write_text(render_episode_page(episode), encoding="utf-8")
        written["pages"] += 1

    public_srt = public_srt_root / episode.subtitle_file.name
    if not public_srt.exists():
        subtitle_text = episode.subtitle_file.read_text(encoding="utf-8-sig")
        public_srt.write_text(subtitle_text, encoding="utf-8-sig")
        written["srts"] += 1

    public_wordcloud = public_wordcloud_root / f"{episode.slug}.svg"
    if not public_wordcloud.exists():
        public_wordcloud.write_text(
            core.build_wordcloud_svg(episode, kind="concept", background="#f7fbfb"),
            encoding="utf-8",
        )
        written["wordclouds"] += 1

    return written


def write_docs(episodes: list[core.Episode], docs_root: Path) -> None:
    (docs_root / "index.md").write_text(render_index(episodes), encoding="utf-8")
    for episode in episodes:
        write_episode_assets(episode, docs_root)


def read_utf8_sig_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def episode_needs_append(
    item: tuple[str, str, str],
    docs_root: Path,
    index_text: str,
) -> bool:
    title, _, subtitle_rel = item
    slug = core.slugify(title, subtitle_rel)
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    episode_page = episodes_root / f"{slug}.md"
    public_srt = public_srt_root / Path(subtitle_rel).name
    public_wordcloud = public_wordcloud_root / f"{slug}.svg"

    if not episode_page.exists():
        return True
    if not public_srt.exists():
        return True
    if not public_wordcloud.exists():
        return True
    if f'href="/episodes/{slug}"' not in index_text:
        return True

    subtitle_source = core.ROOT / subtitle_rel[2:]
    if not subtitle_source.exists():
        return False

    return read_utf8_sig_text(subtitle_source) != read_utf8_sig_text(public_srt)


def find_append_candidates(
    nav_items: list[tuple[str, str, str]],
    docs_root: Path,
) -> list[tuple[str, str, str]]:
    index_path = docs_root / "index.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    candidates: list[tuple[str, str, str]] = []
    for item in nav_items:
        if episode_needs_append(item, docs_root, index_text):
            candidates.append(item)
    return candidates


def find_items_by_slug(
    nav_items: list[tuple[str, str, str]],
    requested_slugs: list[str],
) -> list[tuple[str, str, str]]:
    requested = {slug.strip() for slug in requested_slugs if slug.strip()}
    if not requested:
        return []

    matched: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in nav_items:
        title, _, subtitle_rel = item
        slug = core.slugify(title, subtitle_rel)
        if slug not in requested or slug in seen:
            continue
        matched.append(item)
        seen.add(slug)

    missing = sorted(requested - seen)
    if missing:
        raise SystemExit(f"unknown episode slug(s): {', '.join(missing)}")

    return matched


def normalize_srt_request(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    if text.startswith("./"):
        text = text[2:]
    return Path(text).name


def find_items_by_srt(
    nav_items: list[tuple[str, str, str]],
    requested_srts: list[str],
) -> list[tuple[str, str, str]]:
    requested = {normalize_srt_request(value) for value in requested_srts if value.strip()}
    if not requested:
        return []

    matched: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in nav_items:
        _, _, subtitle_rel = item
        subtitle_name = Path(subtitle_rel).name
        if subtitle_name not in requested or subtitle_name in seen:
            continue
        matched.append(item)
        seen.add(subtitle_name)

    missing = sorted(requested - seen)
    if missing:
        raise SystemExit(f"unknown srt file(s): {', '.join(missing)}")

    return matched


def parse_numeric_stat(index_text: str, label: str) -> int | None:
    match = re.search(
        rf"<div><span>(\d+)</span><small>{re.escape(label)}</small></div>",
        index_text,
    )
    if not match:
        return None
    return int(match.group(1))


def replace_stat(index_text: str, label: str, value: str) -> str:
    pattern = re.compile(
        rf"(<div><span>)([^<]+)(</span><small>{re.escape(label)}</small></div>)"
    )
    return pattern.sub(rf"\g<1>{value}\g<3>", index_text, count=1)


def prepend_index_cards(index_text: str, episodes: list[core.Episode]) -> str:
    marker = '<section class="vp-transcript-grid">'
    rendered_cards = [
        render_episode_card(episode).strip("\n")
        for episode in episodes
        if f'href="/episodes/{episode.slug}"' not in index_text
    ]
    if not rendered_cards:
        return index_text
    cards_block = "\n\n".join(rendered_cards)
    indented_block = "\n".join(f"    {line}" if line else "" for line in cards_block.splitlines())
    return index_text.replace(marker, f"{marker}\n{indented_block}\n", 1)


def append_docs(episodes: list[core.Episode], docs_root: Path) -> dict[str, int]:
    ensure_docs_root(docs_root)
    index_path = docs_root / "index.md"
    episodes_root, _, _ = get_docs_paths(docs_root)
    new_pages = 0

    for episode in episodes:
        if not (episodes_root / f"{episode.slug}.md").exists():
            new_pages += 1
        write_episode_assets(episode, docs_root)

    if not index_path.exists():
        index_path.write_text(render_index(episodes), encoding="utf-8")
        return {"episodes": len(episodes), "new_pages": len(episodes), "new_cards": len(episodes)}

    index_text = index_path.read_text(encoding="utf-8")
    new_cards = [
        episode for episode in episodes if f'href="/episodes/{episode.slug}"' not in index_text
    ]
    if not new_cards:
        return {"episodes": len(episodes), "new_pages": new_pages, "new_cards": 0}

    next_episode_count = (parse_numeric_stat(index_text, "集数") or 0) + len(new_cards)
    next_block_count = (parse_numeric_stat(index_text, "阅读段落") or 0) + sum(
        len(episode.blocks) for episode in new_cards
    )
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    updated_index = prepend_index_cards(index_text, new_cards)
    updated_index = replace_stat(updated_index, "集数", str(next_episode_count))
    updated_index = replace_stat(updated_index, "阅读段落", str(next_block_count))
    updated_index = replace_stat(updated_index, "生成时间", generated_at)
    index_path.write_text(updated_index, encoding="utf-8")
    return {"episodes": len(episodes), "new_pages": new_pages, "new_cards": len(new_cards)}


def collect_missing_episodes(
    episodes: list[core.Episode],
    docs_root: Path,
) -> list[core.Episode]:
    episodes_root, public_srt_root, public_wordcloud_root = get_docs_paths(docs_root)
    index_path = docs_root / "index.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    missing: list[core.Episode] = []
    for episode in episodes:
        page_missing = not (episodes_root / f"{episode.slug}.md").exists()
        srt_missing = not (public_srt_root / episode.subtitle_file.name).exists()
        wordcloud_missing = not (public_wordcloud_root / f"{episode.slug}.svg").exists()
        card_missing = f'href="/episodes/{episode.slug}"' not in index_text
        if page_missing or srt_missing or wordcloud_missing or card_missing:
            missing.append(episode)
    return missing


def fill_missing_docs(episodes: list[core.Episode], docs_root: Path) -> dict[str, int]:
    ensure_docs_root(docs_root)
    missing_episodes = collect_missing_episodes(episodes, docs_root)
    written = {"episodes": 0, "pages": 0, "srts": 0, "wordclouds": 0, "cards": 0}

    if not missing_episodes:
        return written

    index_path = docs_root / "index.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    missing_cards = [
        episode for episode in missing_episodes if f'href="/episodes/{episode.slug}"' not in index_text
    ]

    for episode in missing_episodes:
        episode_written = write_missing_episode_assets(episode, docs_root)
        written["episodes"] += 1
        written["pages"] += episode_written["pages"]
        written["srts"] += episode_written["srts"]
        written["wordclouds"] += episode_written["wordclouds"]

    if missing_cards:
        written["cards"] = append_docs(missing_cards, docs_root)["new_cards"]

    return written


def main() -> None:
    args = parse_args()
    docs_root = args.docs_root.resolve()
    nav_items = core.parse_nav(core.DEFAULT_NAV)
    episodes = core.build_episodes(nav_items)

    if args.episode:
        selected_items = find_items_by_slug(nav_items, args.episode)
        episodes = core.build_episodes(selected_items)
        appended = append_docs(episodes, docs_root)
        print(
            f"processed {appended['episodes']} requested episode(s) under {docs_root} "
            f"({appended['new_pages']} new pages, {appended['new_cards']} new index cards)"
        )
        return

    if args.srt:
        selected_items = find_items_by_srt(nav_items, args.srt)
        episodes = core.build_episodes(selected_items)
        appended = append_docs(episodes, docs_root)
        print(
            f"processed {appended['episodes']} requested episode(s) under {docs_root} "
            f"({appended['new_pages']} new pages, {appended['new_cards']} new index cards)"
        )
        return

    if args.append_new:
        candidates = find_append_candidates(nav_items, docs_root)
        episodes = core.build_episodes(candidates)
        appended = append_docs(episodes, docs_root)
        print(
            f"processed {appended['episodes']} episode(s) under {docs_root} "
            f"({appended['new_pages']} new pages, {appended['new_cards']} new index cards)"
        )
        return

    if args.fill_missing:
        written = fill_missing_docs(episodes, docs_root)
        print(
            "filled missing VitePress assets under "
            f"{docs_root}: {written['pages']} pages, {written['srts']} srts, "
            f"{written['wordclouds']} wordclouds, {written['cards']} index cards"
        )
        return

    build_docs_root(docs_root)
    write_docs(episodes, docs_root)
    print(f"generated {len(episodes)} VitePress pages under {docs_root}")


if __name__ == "__main__":
    main()
