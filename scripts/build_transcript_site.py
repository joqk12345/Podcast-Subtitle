#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import math
import random
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NAV = ROOT / "pie-podcast-nav-v2.md"
DEFAULT_OUTPUT = ROOT / "transcript-site"


@dataclass
class Cue:
    start: float
    end: float
    text: str


@dataclass
class Block:
    start: float
    end: float
    text: str
    section_id: str | None = None
    section_label: str | None = None


@dataclass
class Episode:
    title: str
    audio_url: str
    subtitle_rel: str
    subtitle_file: Path
    slug: str
    cues: list[Cue]
    blocks: list[Block]
    duration_seconds: float


@dataclass
class WordPlacement:
    text: str
    count: int
    font_size: float
    center_x: float
    center_y: float
    width: float
    height: float
    color: str


WORDCLOUD_STOP_WORDS = {
    "啊",
    "ai时代",
    "吧",
    "并且",
    "不是",
    "不是的",
    "不过",
    "比如",
    "当然",
    "大家",
    "但是",
    "的话",
    "对",
    "对于",
    "都",
    "对吧",
    "对不对",
    "非常",
    "反正",
    "感觉",
    "刚才",
    "跟",
    "各位",
    "各位朋友",
    "还是",
    "还有",
    "很多",
    "很有意思",
    "欢迎来到",
    "就是",
    "觉得",
    "开始",
    "看到",
    "可能",
    "可以",
    "肯定",
    "来说",
    "老师",
    "里面",
    "两位",
    "那么",
    "那个",
    "你们",
    "朋友",
    "其实",
    "前面",
    "然后",
    "如果",
    "如何",
    "什么",
    "什么呢",
    "时候",
    "是吧",
    "是的",
    "是不是",
    "所以",
    "他们",
    "它们",
    "我们",
    "我觉得",
    "我是",
    "现在",
    "现在是",
    "想",
    "小东",
    "因为",
    "应该",
    "一个",
    "一些",
    "一直",
    "已经",
    "以后",
    "以前",
    "一样",
    "一种",
    "有点",
    "有很多",
    "有时候",
    "又",
    "再",
    "这个",
    "这个事",
    "这个点",
    "这个事情",
    "这次",
    "这就",
    "这样",
    "这种",
    "真的",
    "之后",
    "只是",
    "自己",
    "咱们",
    "咱们今天",
    "为什么",
    "为什么呢",
    "未来",
    "未来的",
    "或者",
    "分之",
    "没这么多",
    "这是",
    "the",
    "and",
    "for",
    "from",
    "have",
    "into",
    "that",
    "this",
    "with",
}

WORDCLOUD_PALETTE = [
    "#c86432",
    "#d8874d",
    "#1d6c72",
    "#2a8b91",
    "#8f441e",
    "#b35e34",
    "#6b6259",
]

WORDCLOUD_GENERIC_PREFIXES = (
    "这个",
    "那个",
    "我们",
    "你们",
    "他们",
    "这是",
    "现在",
    "然后",
    "所以",
    "如果",
    "因为",
    "就是",
    "其实",
    "还有",
    "没有",
    "不是",
    "一个",
)

WORDCLOUD_GENERIC_SUFFIXES = (
    "的时候",
    "之后",
    "之前",
    "的话",
    "来看",
    "来说",
    "问题",
    "情况",
)

WORDCLOUD_EDGE_STOP_CHARS = set(
    "的一是在就都和也把被又还而与着啊呀吧吗呢嘛么我你他她它们这那个得让给从向对上下里外去来以于所并及"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static transcript site from nav markdown and SRT files."
    )
    parser.add_argument(
        "--nav",
        type=Path,
        default=DEFAULT_NAV,
        help=f"Navigation markdown file. Default: {DEFAULT_NAV}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional number of episodes to build from the top of the nav.",
    )
    return parser.parse_args()


def normalize_space(text: str) -> str:
    cleaned = []
    for char in text:
        category = unicodedata.category(char)
        if category == "Cf":
            continue
        if category.startswith("C") and char not in {"\n", "\t", "\r"}:
            continue
        cleaned.append(char)
    return re.sub(r"\s+", " ", "".join(cleaned)).strip()


def slugify(title: str, path_text: str) -> str:
    issue_match = re.search(r"第\s*(\d+)\s*期", title)
    if issue_match:
        return f"ep-{issue_match.group(1)}"

    extra_match = re.search(r"番外\s*(\d+)", title)
    if extra_match:
        return f"extra-{extra_match.group(1)}"

    stem = Path(path_text).name
    while True:
        next_stem = Path(stem).stem
        if next_stem == stem:
            break
        stem = next_stem
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    return slug or "episode"


def parse_nav(nav_path: Path) -> list[tuple[str, str, str]]:
    text = nav_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\[(?P<title>.*?)\]\((?P<audio>https?://[^\s)]+)\)\s*\n\[字幕\]\((?P<subtitle>\./pie-srt/v2/[^)]+)\)",
        re.DOTALL,
    )
    items: list[tuple[str, str, str]] = []
    for match in pattern.finditer(text):
        title = normalize_space(match.group("title"))
        audio = match.group("audio").strip()
        subtitle = match.group("subtitle").strip()
        items.append((title, audio, subtitle))
    return items


def parse_timestamp(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_srt(srt_path: Path) -> list[Cue]:
    lines = srt_path.read_text(encoding="utf-8-sig").splitlines()
    cues: list[Cue] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if re.fullmatch(r"\d+", line):
            index += 1
            if index >= len(lines):
                break
            line = lines[index].strip()

        if "-->" not in line:
            index += 1
            continue

        start_raw, end_raw = [part.strip() for part in line.split("-->", 1)]
        start = parse_timestamp(start_raw)
        end = parse_timestamp(end_raw)
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1

        text = normalize_space(" ".join(text_lines))
        if text:
            cues.append(Cue(start=start, end=end, text=text))
        index += 1
    return cues


def should_flush(current_text: str, current_duration: float, next_gap: float) -> bool:
    length = len(current_text)
    ends_cleanly = current_text.endswith(("。", "！", "？", "!", "?", "；", ";"))
    if next_gap >= 4:
        return True
    if current_duration >= 75:
        return True
    if length >= 180:
        return True
    if length >= 110 and ends_cleanly:
        return True
    return False


def build_blocks(cues: list[Cue]) -> list[Block]:
    if not cues:
        return []

    blocks: list[Block] = []
    block_start = cues[0].start
    block_end = cues[0].end
    parts = [cues[0].text]

    for position, cue in enumerate(cues):
        if position == 0:
            continue
        previous = cues[position - 1]
        gap = cue.start - previous.end
        current_text = normalize_space(" ".join(parts))
        current_duration = block_end - block_start
        if should_flush(current_text, current_duration, gap):
            blocks.append(Block(start=block_start, end=block_end, text=current_text))
            block_start = cue.start
            block_end = cue.end
            parts = [cue.text]
            continue

        parts.append(cue.text)
        block_end = cue.end

    final_text = normalize_space(" ".join(parts))
    if final_text:
        blocks.append(Block(start=block_start, end=block_end, text=final_text))

    current_bucket: int | None = None
    for block in blocks:
        bucket = int(block.start // 600)
        if bucket != current_bucket:
            current_bucket = bucket
            block.section_id = f"section-{bucket:02d}"
            block.section_label = format_bucket_label(bucket)

    return blocks


def format_seconds(value: float) -> str:
    total = max(0, int(value))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_bucket_label(bucket: int) -> str:
    start = bucket * 10
    end = start + 10
    return f"{start:02d}-{end:02d} 分钟"


def estimate_duration(cues: list[Cue]) -> float:
    if not cues:
        return 0
    return cues[-1].end


def build_episodes(nav_items: list[tuple[str, str, str]], limit: int = 0) -> list[Episode]:
    selected_items = nav_items[:limit] if limit > 0 else nav_items
    episodes: list[Episode] = []
    for title, audio_url, subtitle_rel in selected_items:
        subtitle_file = ROOT / subtitle_rel[2:]
        if not subtitle_file.exists():
            continue
        cues = parse_srt(subtitle_file)
        blocks = build_blocks(cues)
        episodes.append(
            Episode(
                title=title,
                audio_url=audio_url,
                subtitle_rel=subtitle_rel,
                subtitle_file=subtitle_file,
                slug=slugify(title, subtitle_rel),
                cues=cues,
                blocks=blocks,
                duration_seconds=estimate_duration(cues),
            )
        )
    return episodes


def split_wordcloud_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for chunk in normalize_space(text).split(" "):
        cleaned = chunk.strip(".,!?;:()[]{}<>\"'“”‘’`·，。！？；：（）《》【】、/\\|=-_+*&^%$#@~")
        if not cleaned:
            continue

        if re.fullmatch(r"[\u4e00-\u9fff]+", cleaned):
            if len(cleaned) <= 4:
                tokens.append(cleaned)
                continue

            seen: set[str] = set()
            for size in (2, 3, 4):
                if len(cleaned) < size:
                    continue
                for index in range(len(cleaned) - size + 1):
                    token = cleaned[index : index + size]
                    if token in seen:
                        continue
                    seen.add(token)
                    tokens.append(token)
            continue

        tokens.extend(re.findall(r"[\u4e00-\u9fff]+", cleaned))
    return tokens


def is_wordcloud_token_allowed(token: str) -> bool:
    token = token.strip().lower()
    if not token:
        return False
    if token in WORDCLOUD_STOP_WORDS:
        return False
    if token.isdigit():
        return False

    if re.fullmatch(r"[a-z0-9._+-]+", token):
        return len(token) >= 3

    if not re.fullmatch(r"[\u4e00-\u9fff]+", token):
        return False

    if len(token) < 2 or len(token) > 8:
        return False
    if any(token == prefix or token.startswith(prefix) for prefix in WORDCLOUD_GENERIC_PREFIXES):
        return False
    if any(token.endswith(suffix) for suffix in WORDCLOUD_GENERIC_SUFFIXES):
        return False
    if token[0] in WORDCLOUD_EDGE_STOP_CHARS or token[-1] in WORDCLOUD_EDGE_STOP_CHARS:
        return False
    return True


def build_word_frequencies(episode: Episode) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for token in split_wordcloud_tokens(episode.title):
        if is_wordcloud_token_allowed(token):
            counts[token] = counts.get(token, 0) + 8

    for token in re.findall(r"[A-Za-z]{2,8}", episode.title):
        normalized = token.upper() if len(token) <= 4 else token.title()
        counts[normalized] = counts.get(normalized, 0) + 6

    parts = [block.text for block in episode.blocks]

    for token in split_wordcloud_tokens(" ".join(parts)):
        if not is_wordcloud_token_allowed(token):
            continue
        counts[token] = counts.get(token, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [(token, count) for token, count in ranked if count >= 2][:72]


def estimate_token_width(token: str, font_size: float) -> float:
    cjk_chars = sum(1 for char in token if "\u4e00" <= char <= "\u9fff")
    latin_chars = len(token) - cjk_chars
    units = cjk_chars * 1.0 + latin_chars * 0.58 + max(len(token) - 1, 0) * 0.06
    return font_size * max(units, 1.2)


def scale_font_size(rank: int, count: int, min_count: int, max_count: int) -> float:
    if max_count <= min_count:
        return 28.0
    weight = (count - min_count) / (max_count - min_count)
    eased = 0.2 + (weight**0.78) * 0.8
    size = 20 + eased * 72
    size -= rank * 0.18
    return max(18.0, min(size, 92.0))


def rectangles_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def pick_wordcloud_color(index: int, rng: random.Random) -> str:
    base = WORDCLOUD_PALETTE[index % len(WORDCLOUD_PALETTE)]
    if rng.random() > 0.35:
        return base
    return WORDCLOUD_PALETTE[rng.randrange(len(WORDCLOUD_PALETTE))]


def build_wordcloud_svg(
    episode: Episode,
    width: int = 1200,
    height: int = 720,
    background: str = "#fffaf4",
) -> str:
    frequencies = build_word_frequencies(episode)
    if not frequencies:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}"><rect width="100%" height="100%" fill="{background}" />'
            '<text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" '
            'fill="#6b6259" font-family="IBM Plex Sans, PingFang SC, sans-serif" font-size="28">'
            "暂无足够词频数据"
            "</text></svg>"
        )

    min_count = frequencies[-1][1]
    max_count = frequencies[0][1]
    center_x = width / 2
    center_y = height / 2
    margin = 36
    placements: list[WordPlacement] = []
    boxes: list[tuple[float, float, float, float]] = []
    rng = random.Random(episode.slug)

    for rank, (token, count) in enumerate(frequencies):
        font_size = scale_font_size(rank, count, min_count, max_count)
        word_width = estimate_token_width(token, font_size)
        word_height = font_size * 0.9
        start_angle = rng.random() * math.tau
        placed = False

        for step in range(1800):
            theta = start_angle + step * 0.33
            radius = 3.8 * theta
            x = center_x + math.cos(theta) * radius
            y = center_y + math.sin(theta) * radius
            box = (
                x - word_width / 2 - 4,
                y - word_height / 2 - 4,
                x + word_width / 2 + 4,
                y + word_height / 2 + 4,
            )

            if (
                box[0] < margin
                or box[1] < margin
                or box[2] > width - margin
                or box[3] > height - margin
            ):
                continue

            if any(rectangles_overlap(box, existing) for existing in boxes):
                continue

            boxes.append(box)
            placements.append(
                WordPlacement(
                    text=token,
                    count=count,
                    font_size=font_size,
                    center_x=x,
                    center_y=y,
                    width=word_width,
                    height=word_height,
                    color=pick_wordcloud_color(rank, rng),
                )
            )
            placed = True
            break

        if not placed and len(placements) >= 24:
            break

    placements.sort(key=lambda item: item.font_size)
    text_nodes = "\n".join(
        (
            f'<text x="{placement.center_x:.1f}" y="{placement.center_y:.1f}" '
            f'font-size="{placement.font_size:.1f}" fill="{placement.color}" text-anchor="middle" '
            'dominant-baseline="middle" font-family="IBM Plex Sans, PingFang SC, Hiragino Sans GB, '
            'Microsoft YaHei, sans-serif" font-weight="700">'
            f"{html.escape(placement.text)}</text>"
        )
        for placement in placements
    )
    subtitle = html.escape(f"{episode.title} 词云")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="title desc">
  <title>{subtitle}</title>
  <desc>根据全文转写高频词生成的词云图</desc>
  <rect width="100%" height="100%" rx="28" fill="{background}" />
  <rect x="14" y="14" width="{width - 28}" height="{height - 28}" rx="22" fill="none" stroke="#eadfce" />
  {text_nodes}
</svg>
"""


def build_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(parents=True, exist_ok=True)
    (output_dir / "pie-srt" / "v2").mkdir(parents=True, exist_ok=True)


def render_index(episodes: list[Episode]) -> str:
    cards = "\n".join(render_episode_card(episode) for episode in episodes)
    total_blocks = sum(len(episode.blocks) for episode in episodes)
    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>后互联网时代的乱弹 | 字幕阅读站</title>
  <link rel="stylesheet" href="./assets/style.css">
</head>
<body data-page="index">
  <div class="shell">
    <header class="hero">
      <p class="eyebrow">Transcript Reader Prototype</p>
      <h1>后互联网时代的乱弹</h1>
      <p class="hero-copy">把原始 SRT 整理成可读、可导航、可分享的静态阅读站。相比直接放字幕文件或大段 Markdown，这种形式更适合对外展示。</p>
      <div class="hero-stats">
        <div><span>{len(episodes)}</span><small>集数</small></div>
        <div><span>{total_blocks}</span><small>阅读段落</small></div>
        <div><span>{build_time}</span><small>生成时间</small></div>
      </div>
      <label class="search-box">
        <span>快速筛选</span>
        <input id="episode-filter" type="search" placeholder="输入标题、期号、关键词">
      </label>
    </header>
    <main>
      <section class="section-header">
        <h2>最近节目</h2>
        <p>每集都保留原始音频链接，并将字幕聚合为更适合阅读的时间轴段落。</p>
      </section>
      <section id="episode-list" class="episode-grid">
        {cards}
      </section>
    </main>
  </div>
  <script src="./assets/app.js"></script>
</body>
</html>
"""


def render_episode_card(episode: Episode) -> str:
    summary = html.escape(build_preview(episode.blocks))
    title = html.escape(episode.title)
    duration = format_seconds(episode.duration_seconds)
    return f"""
<article class="episode-card" data-filter="{html.escape((episode.title + ' ' + summary).lower())}">
  <p class="episode-meta">{duration} · {len(episode.blocks)} 段</p>
  <h3><a href="./episodes/{episode.slug}.html">{title}</a></h3>
  <p class="episode-summary">{summary}</p>
  <div class="episode-links">
    <a class="button-link" href="./episodes/{episode.slug}.html">阅读字幕</a>
    <a class="button-link subtle" href="{html.escape(episode.audio_url)}" target="_blank" rel="noreferrer">原始音频</a>
  </div>
</article>
"""


def build_preview(blocks: list[Block], max_length: int = 110) -> str:
    text = " ".join(block.text for block in blocks[:2])
    text = normalize_space(text)
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def render_episode_page(episode: Episode) -> str:
    title = html.escape(episode.title)
    timeline = "\n".join(render_block(block, index) for index, block in enumerate(episode.blocks, start=1))
    sections = "\n".join(render_section_link(block) for block in episode.blocks if block.section_id)
    duration = format_seconds(episode.duration_seconds)
    build_note = (
        "本页由原始 SRT 自动整理。规则是保留时间轴，但把过碎的句级字幕合并成段落级阅读块。"
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | 字幕阅读</title>
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body data-page="episode">
  <div class="shell episode-shell">
    <a class="back-link" href="../index.html">返回目录</a>
    <header class="episode-hero">
      <div>
        <p class="eyebrow">Episode Transcript</p>
        <h1>{title}</h1>
        <p class="hero-copy">{html.escape(build_note)}</p>
      </div>
      <div class="episode-facts">
        <div><span>{duration}</span><small>时长</small></div>
        <div><span>{len(episode.cues)}</span><small>SRT 条目</small></div>
        <div><span>{len(episode.blocks)}</span><small>阅读段落</small></div>
      </div>
    </header>
    <section class="player-panel">
      <audio id="audio-player" controls preload="none" src="{html.escape(episode.audio_url)}"></audio>
      <div class="player-links">
        <a class="button-link" href="{html.escape(episode.audio_url)}" target="_blank" rel="noreferrer">在新窗口打开音频</a>
        <a class="button-link subtle" href="../{html.escape(episode.subtitle_rel[2:])}">查看原始 SRT</a>
      </div>
    </section>
    <div class="episode-layout">
      <aside class="episode-sidebar">
        <div class="sidebar-card">
          <h2>时间导航</h2>
          <nav class="section-nav">
            {sections}
          </nav>
        </div>
      </aside>
      <main class="timeline">
        {timeline}
      </main>
    </div>
  </div>
  <script src="../assets/app.js"></script>
</body>
</html>
"""


def render_section_link(block: Block) -> str:
    if not block.section_id or not block.section_label:
        return ""
    return (
        f'<a href="#{block.section_id}">{html.escape(block.section_label)}'
        f' <small>{format_seconds(block.start)}</small></a>'
    )


def render_block(block: Block, index: int) -> str:
    anchor = f' id="{block.section_id}"' if block.section_id else ""
    text = html.escape(block.text)
    start = format_seconds(block.start)
    end = format_seconds(block.end)
    return f"""
<article class="timeline-block"{anchor} data-start="{math.floor(block.start)}" data-end="{math.ceil(block.end)}">
  <button class="timestamp" data-seek="{math.floor(block.start)}" type="button">{start}</button>
  <div class="timeline-content">
    <p class="timeline-index">第 {index} 段 · {start} - {end}</p>
    <p>{text}</p>
  </div>
</article>
"""


def write_assets(output_dir: Path) -> None:
    (output_dir / "assets" / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (output_dir / "assets" / "app.js").write_text(APP_JS, encoding="utf-8")


def write_pages(output_dir: Path, episodes: list[Episode]) -> None:
    (output_dir / "index.html").write_text(render_index(episodes), encoding="utf-8")
    for episode in episodes:
        episode_path = output_dir / "episodes" / f"{episode.slug}.html"
        episode_path.write_text(render_episode_page(episode), encoding="utf-8")
        shutil.copy2(
            episode.subtitle_file,
            output_dir / "pie-srt" / "v2" / episode.subtitle_file.name,
        )


def main() -> None:
    args = parse_args()
    nav_path = args.nav.resolve()
    output_dir = args.output.resolve()
    nav_items = parse_nav(nav_path)
    episodes = build_episodes(nav_items, args.limit)
    build_output_dir(output_dir)
    write_assets(output_dir)
    write_pages(output_dir, episodes)
    print(f"built {len(episodes)} episodes into {output_dir}")


STYLE_CSS = """
:root {
  --bg: #f3efe6;
  --surface: rgba(255, 252, 247, 0.8);
  --surface-strong: #fffaf2;
  --ink: #1d1a17;
  --muted: #5f564d;
  --line: rgba(47, 38, 29, 0.12);
  --accent: #c86432;
  --accent-2: #1d6c72;
  --shadow: 0 24px 70px rgba(64, 42, 22, 0.12);
  --radius: 24px;
  --font-sans: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  background:
    radial-gradient(circle at top left, rgba(29, 108, 114, 0.18), transparent 30%),
    radial-gradient(circle at top right, rgba(200, 100, 50, 0.2), transparent 28%),
    linear-gradient(180deg, #fcf7ef 0%, var(--bg) 100%);
}

a {
  color: inherit;
}

.shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 64px;
}

.hero,
.episode-hero,
.player-panel,
.sidebar-card,
.timeline-block,
.episode-card {
  border: 1px solid var(--line);
  background: var(--surface);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow);
}

.hero,
.episode-hero {
  padding: 32px;
  border-radius: calc(var(--radius) + 6px);
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--accent-2);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  font-weight: 700;
}

h1,
h2,
h3 {
  font-family: var(--font-serif);
  line-height: 1.1;
}

h1 {
  margin: 0;
  font-size: clamp(40px, 7vw, 76px);
}

.hero-copy {
  max-width: 720px;
  margin: 16px 0 0;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.7;
}

.hero-stats,
.episode-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.hero-stats div,
.episode-facts div {
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(47, 38, 29, 0.08);
}

.hero-stats span,
.episode-facts span {
  display: block;
  font-size: 24px;
  font-weight: 700;
}

.hero-stats small,
.episode-facts small,
.timeline-index,
.episode-meta,
.section-nav small {
  color: var(--muted);
}

.search-box {
  display: block;
  margin-top: 24px;
}

.search-box span {
  display: block;
  margin-bottom: 10px;
  font-size: 14px;
  color: var(--muted);
}

.search-box input {
  width: 100%;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  font: inherit;
}

.section-header {
  margin: 34px 0 20px;
}

.section-header h2 {
  margin: 0;
  font-size: 28px;
}

.section-header p {
  margin: 8px 0 0;
  color: var(--muted);
}

.episode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.episode-card {
  padding: 22px;
  border-radius: var(--radius);
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.episode-card:hover {
  transform: translateY(-3px);
  border-color: rgba(200, 100, 50, 0.4);
}

.episode-card h3 {
  margin: 8px 0 12px;
  font-size: 26px;
}

.episode-card h3 a {
  text-decoration: none;
}

.episode-summary {
  margin: 0 0 18px;
  color: var(--muted);
  line-height: 1.7;
}

.episode-links,
.player-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.button-link,
.timestamp {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--accent);
  color: white;
  cursor: pointer;
  font: inherit;
  text-decoration: none;
}

.button-link.subtle {
  background: transparent;
  color: var(--ink);
  border-color: var(--line);
}

.back-link {
  display: inline-block;
  margin-bottom: 16px;
  color: var(--muted);
}

.player-panel {
  margin-top: 18px;
  padding: 20px;
  border-radius: var(--radius);
}

.player-panel audio {
  width: 100%;
}

.episode-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 20px;
  margin-top: 24px;
}

.episode-sidebar {
  position: sticky;
  top: 20px;
  align-self: start;
}

.sidebar-card {
  padding: 18px;
  border-radius: var(--radius);
}

.sidebar-card h2 {
  margin: 0 0 12px;
  font-size: 18px;
}

.section-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-nav a {
  text-decoration: none;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-block {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 16px;
  padding: 18px;
  border-radius: var(--radius);
  scroll-margin-top: 20px;
}

.timeline-block.active {
  border-color: rgba(29, 108, 114, 0.4);
  background: rgba(238, 250, 250, 0.95);
}

.timeline-content p:last-child {
  margin: 0;
  font-size: 18px;
  line-height: 1.9;
}

.timeline-index {
  margin: 0 0 8px;
  font-size: 13px;
}

.hidden {
  display: none;
}

@media (max-width: 920px) {
  .episode-layout {
    grid-template-columns: 1fr;
  }

  .episode-sidebar {
    position: static;
  }

  .timeline-block {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .shell {
    width: min(100% - 20px, 100%);
  }

  .hero,
  .episode-hero,
  .player-panel,
  .timeline-block,
  .episode-card,
  .sidebar-card {
    padding: 18px;
    border-radius: 20px;
  }

  h1 {
    font-size: 40px;
  }

  .timeline-content p:last-child {
    font-size: 17px;
  }
}
"""


APP_JS = """
const filterInput = document.querySelector('#episode-filter');
const episodeCards = Array.from(document.querySelectorAll('.episode-card'));

if (filterInput && episodeCards.length) {
  filterInput.addEventListener('input', () => {
    const query = filterInput.value.trim().toLowerCase();
    for (const card of episodeCards) {
      const haystack = card.dataset.filter || '';
      card.classList.toggle('hidden', Boolean(query) && !haystack.includes(query));
    }
  });
}

const audio = document.querySelector('#audio-player');
const seekButtons = Array.from(document.querySelectorAll('[data-seek]'));
const timelineBlocks = Array.from(document.querySelectorAll('.timeline-block'));

for (const button of seekButtons) {
  button.addEventListener('click', () => {
    if (!audio) return;
    const seconds = Number(button.dataset.seek || '0');
    audio.currentTime = seconds;
    audio.play().catch(() => {});
  });
}

if (audio && timelineBlocks.length) {
  const highlightCurrentBlock = () => {
    const now = audio.currentTime;
    let activeBlock = null;
    for (const block of timelineBlocks) {
      const start = Number(block.dataset.start || '0');
      const end = Number(block.dataset.end || '0');
      const isActive = now >= start && now < end;
      block.classList.toggle('active', isActive);
      if (isActive) activeBlock = block;
    }
    if (activeBlock && !activeBlock.dataset.scrolled) {
      const top = activeBlock.getBoundingClientRect().top;
      const withinViewport = top > 120 && top < window.innerHeight - 120;
      if (!withinViewport) {
        activeBlock.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }
  };

  audio.addEventListener('timeupdate', highlightCurrentBlock);
}
"""


if __name__ == "__main__":
    main()
