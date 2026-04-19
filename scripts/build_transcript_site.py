#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import math
import random
import re
import shutil
import unicodedata
from collections import Counter
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
    word_candidates: list[WordCandidate] | None = None


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


@dataclass
class WordCandidate:
    token: str
    count: int
    block_hits: int
    title_hits: int
    score: float


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
    "token",
    "agent",
    "with",
}

WORDCLOUD_LOW_SIGNAL_WORDS = {
    "东西",
    "些东西",
    "这个东西",
    "事情",
    "件事",
    "件事情",
    "这个事情",
    "比如说",
    "如说",
    "比较",
    "实际",
    "意思",
    "知道",
    "今天",
    "时间",
    "有些",
    "一些",
    "方面",
    "地方",
    "最后",
    "包括",
    "完全",
    "到了",
    "为什么",
    "不能",
    "不会",
    "必须",
    "主要",
    "当时",
    "后面",
    "里面",
    "外面",
    "国内",
    "专门",
    "推荐",
    "理解",
    "有点",
    "人工",
    "为什",
    "会有",
    "有很",
    "有意",
    "有一些",
    "叫做",
    "特别",
    "能够",
    "重要",
    "提到",
    "第二",
    "简单",
    "真正",
    "需要",
    "结果",
    "基本",
    "程度",
    "当中",
    "有人",
    "些东",
    "些事",
    "些事情",
    "者说",
    "或者说",
    "有意思",
    "不知道",
    "不知",
    "怎么样",
    "大概",
    "到底",
    "不到",
    "认为",
    "甚至",
    "虽然",
    "普通",
    "各种",
    "确实",
    "喜欢",
    "很有",
    "很快",
    "很大",
    "不了",
    "本书",
    "片子",
    "话题",
    "过程",
}

WORDCLOUD_GENERIC_PENALTIES = {
    "价格": 1.5,
    "关系": 2.0,
    "价值": 1.6,
    "风险": 1.6,
    "方面": 2.8,
    "地方": 2.8,
    "系统": 1.5,
    "产品": 1.4,
    "能力": 1.5,
    "工具": 1.2,
    "开发": 1.2,
    "时代": 1.0,
    "国家": 2.0,
}

WORDCLOUD_LATIN_ALIASES = {
    "agi": "AGI",
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "cpu": "CPU",
    "cuda": "CUDA",
    "cursor": "Cursor",
    "deepseek": "DeepSeek",
    "gpt": "GPT",
    "gpu": "GPU",
    "grok": "Grok",
    "google": "Google",
    "ide": "IDE",
    "ios": "iOS",
    "llm": "LLM",
    "meta": "Meta",
    "openai": "OpenAI",
    "qwen": "Qwen",
    "sdk": "SDK",
    "sora": "Sora",
}

WORDCLOUD_TECH_CONCEPT_TERMS = {
    "AGI",
    "AI",
    "API",
    "CPU",
    "CUDA",
    "GPU",
    "GPT",
    "IDE",
    "LLM",
    "SDK",
}

WORDCLOUD_ENTITY_TERMS = {
    "DeepSeek",
    "OpenAI",
    "ChatGPT",
    "Claude",
    "Cursor",
    "Qwen",
    "Google",
    "Meta",
    "AWS",
    "Sora",
    "中国",
    "美国",
    "日本",
    "伊朗",
    "以色列",
    "中东",
    "欧洲",
    "俄罗斯",
    "乌克兰",
    "华为",
    "苹果",
    "谷歌",
    "微软",
    "腾讯",
    "阿里",
    "百度",
    "字节",
    "英伟达",
    "特斯拉",
    "川普",
    "特朗普",
    "拜登",
    "马斯克",
    "奥特曼",
    "黄仁勋",
    "懂王",
    "千问",
}

WORDCLOUD_ENTITY_SUFFIXES = (
    "公司",
    "大学",
    "学院",
    "银行",
    "集团",
    "政府",
    "法院",
    "议会",
    "联盟",
    "平台",
    "品牌",
    "团队",
)

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

WORDCLOUD_ENTITY_ALLOWLIST = {
    "以色列",
}


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
    if token in WORDCLOUD_ENTITY_ALLOWLIST:
        return True
    if token in WORDCLOUD_STOP_WORDS:
        return False
    if token in WORDCLOUD_LOW_SIGNAL_WORDS:
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


def normalize_latin_token(token: str) -> str:
    normalized = token.strip().lower()
    if not normalized:
        return ""
    if normalized in WORDCLOUD_STOP_WORDS:
        return ""
    alias = WORDCLOUD_LATIN_ALIASES.get(normalized)
    if alias:
        return alias
    if len(normalized) <= 4:
        return normalized.upper()
    return normalized.title()


def collect_cjk_candidates(text: str, max_len: int = 6) -> Counter[str]:
    counts: Counter[str] = Counter()
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", normalize_space(text)):
        upper = min(max_len, len(sequence))
        for size in range(2, upper + 1):
            for index in range(len(sequence) - size + 1):
                token = sequence[index : index + size]
                if not is_wordcloud_token_allowed(token):
                    continue
                counts[token] += 1
    return counts


def collect_latin_candidates(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9.+-]{1,15}", normalize_space(text)):
        token = normalize_latin_token(raw)
        if not token:
            continue
        counts[token] += 1
    return counts


def collect_candidates(text: str) -> Counter[str]:
    counts = collect_cjk_candidates(text)
    counts.update(collect_latin_candidates(text))
    return counts


def is_dominated_candidate(
    candidate: WordCandidate,
    selected: list[WordCandidate],
) -> bool:
    for existing in selected:
        if len(existing.token) <= len(candidate.token):
            continue
        if candidate.token not in existing.token:
            continue
        if existing.count < max(2, math.ceil(candidate.count * 0.86)):
            continue
        if existing.block_hits < max(1, math.ceil(candidate.block_hits * 0.75)):
            continue
        return True
    return False


def has_global_dominator(
    candidate: WordCandidate,
    all_candidates: list[WordCandidate],
) -> bool:
    for other in all_candidates:
        if other.token == candidate.token:
            continue
        if len(other.token) <= len(candidate.token):
            continue
        if candidate.token not in other.token:
            continue
        if other.count < max(2, math.ceil(candidate.count * 0.82)):
            continue
        if other.block_hits < max(1, math.ceil(candidate.block_hits * 0.7)):
            continue
        if other.score + 0.8 < candidate.score:
            continue
        return True
    return False


def score_word_candidate(
    token: str,
    count: int,
    block_hits: int,
    title_hits: int,
) -> float:
    if re.fullmatch(r"[\u4e00-\u9fff]+", token):
        length_bonus = {2: 0.2, 3: 1.3, 4: 1.8, 5: 2.2, 6: 2.5}.get(len(token), 1.0)
        generic_penalty = WORDCLOUD_GENERIC_PENALTIES.get(token, 0.0)
    else:
        length_bonus = 1.6 if len(token) >= 4 else 1.0
        generic_penalty = 0.0

    return (
        count * 1.0
        + block_hits * 2.2
        + title_hits * 6.5
        + length_bonus
        - generic_penalty
    )


def classify_word_candidate(token: str) -> str:
    if token in WORDCLOUD_TECH_CONCEPT_TERMS:
        return "concept"
    if token in WORDCLOUD_ENTITY_TERMS or token in WORDCLOUD_ENTITY_ALLOWLIST:
        return "entity"
    if len(token) > 2 and token.endswith(WORDCLOUD_ENTITY_SUFFIXES):
        return "entity"
    return "concept"


def build_word_candidates(episode: Episode) -> list[WordCandidate]:
    if episode.word_candidates is not None:
        return episode.word_candidates

    total_counts: Counter[str] = Counter()
    block_hits: Counter[str] = Counter()
    title_counts = collect_candidates(episode.title)

    for token, count in title_counts.items():
        total_counts[token] += count * 4
        block_hits[token] += 1

    for block in episode.blocks:
        block_counts = collect_candidates(block.text)
        if not block_counts:
            continue
        total_counts.update(block_counts)
        for token in block_counts:
            block_hits[token] += 1

    candidates: list[WordCandidate] = []
    for token, count in total_counts.items():
        title_hits = title_counts.get(token, 0)
        hits = block_hits.get(token, 0)
        if count < 2 and title_hits == 0:
            continue
        if hits < 2 and count < 4 and title_hits == 0:
            continue
        if token in WORDCLOUD_LOW_SIGNAL_WORDS:
            continue
        candidates.append(
            WordCandidate(
                token=token,
                count=count,
                block_hits=hits,
                title_hits=title_hits,
                score=score_word_candidate(token, count, hits, title_hits),
            )
        )

    candidates = [
        candidate
        for candidate in candidates
        if not has_global_dominator(candidate, candidates)
    ]
    candidates.sort(key=lambda item: (-item.score, -len(item.token), -item.block_hits, item.token))

    selected: list[WordCandidate] = []
    for candidate in candidates:
        if is_dominated_candidate(candidate, selected):
            continue
        selected.append(candidate)
        if len(selected) >= 72:
            break

    episode.word_candidates = selected
    return selected


def build_word_frequencies(
    episode: Episode,
    kind: str = "all",
) -> list[tuple[str, int]]:
    candidates = build_word_candidates(episode)
    if kind == "entity":
        filtered = [candidate for candidate in candidates if classify_word_candidate(candidate.token) == "entity"]
    elif kind == "concept":
        filtered = [candidate for candidate in candidates if classify_word_candidate(candidate.token) == "concept"]
    else:
        filtered = candidates

    filtered.sort(key=lambda item: (-item.count, -item.score, item.token))
    return [(candidate.token, candidate.count) for candidate in filtered]


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
    kind: str = "all",
    width: int = 1200,
    height: int = 720,
    background: str = "#fffaf4",
) -> str:
    frequencies = build_word_frequencies(episode, kind=kind)
    if not frequencies:
        empty_label = {
            "entity": "暂无足够实体词数据",
            "concept": "暂无足够概念词数据",
        }.get(kind, "暂无足够词频数据")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}"><rect width="100%" height="100%" fill="{background}" />'
            '<text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" '
            'fill="#6b6259" font-family="IBM Plex Sans, PingFang SC, sans-serif" font-size="28">'
            f"{empty_label}"
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
    subtitle = html.escape(
        {
            "entity": f"{episode.title} 实体词云",
            "concept": f"{episode.title} 概念词云",
        }.get(kind, f"{episode.title} 词云")
    )
    description = {
        "entity": "根据全文转写提取的人物、国家、组织、品牌等实体词生成的词云图",
        "concept": "根据全文转写提取的技术、议题、概念短语生成的词云图",
    }.get(kind, "根据全文转写高频词生成的词云图")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="title desc">
  <title>{subtitle}</title>
  <desc>{html.escape(description)}</desc>
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
  /* ========== 阅读版样式 (默认) ========== */
  --bg: #faf9f7;
  --surface: #ffffff;
  --surface-soft: rgba(255, 255, 255, 0.7);
  --ink: #1a1a1a;
  --ink-light: #2d2d2d;
  --muted: #6b6b6b;
  --muted-light: #8a8a8a;
  --line: rgba(0, 0, 0, 0.08);
  --line-strong: rgba(0, 0, 0, 0.12);
  --accent: #292929;
  --accent-2: #1d6c72;
  --accent-hover: #000000;
  --highlight: #f5f5f0;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  --shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.08);
  --radius: 4px;
  --radius-lg: 8px;
  --content-width: 720px;
  --shell-width: 1100px;
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
}

/* ========== 经典版样式 ========== */
body.classic {
  --bg: #f3efe6;
  --surface: rgba(255, 252, 247, 0.8);
  --surface-strong: #fffaf2;
  --ink: #1d1a17;
  --ink-light: #2d2d2d;
  --muted: #5f564d;
  --muted-light: #6b6b6b;
  --line: rgba(47, 38, 29, 0.12);
  --line-strong: rgba(47, 38, 29, 0.18);
  --accent: #c86432;
  --accent-2: #1d6c72;
  --accent-hover: #a54d20;
  --highlight: rgba(200, 100, 50, 0.08);
  --shadow: 0 24px 70px rgba(64, 42, 22, 0.12);
  --radius: 24px;
  --radius-lg: 24px;
  --shell-width: 1180px;
}

body.classic .toggle-mode {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

body.classic .toggle-mode:hover {
  background: var(--accent-hover);
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
  background: var(--bg);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: inherit;
}

.shell {
  width: min(var(--shell-width), calc(100% - 48px));
  margin: 0 auto;
  padding: 48px 0 96px;
}

body[data-page="episode"] .shell {
  max-width: var(--content-width);
}

.hero,
.episode-hero,
.player-panel,
.sidebar-card,
.timeline-block,
.episode-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
}

.hero {
  padding: 48px 0 40px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 48px;
}

.hero .eyebrow {
  display: none;
}

.hero h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.hero-copy {
  max-width: 580px;
  margin: 16px 0 0;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.7;
  font-family: var(--font-serif);
}

h1, h2, h3 {
  font-family: var(--font-serif);
  line-height: 1.2;
  font-weight: 600;
}

.hero-stats,
.episode-facts {
  display: flex;
  gap: 32px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.hero-stats div,
.episode-facts div {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.hero-stats span,
.episode-facts span {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink-light);
}

.hero-stats small,
.episode-facts small,
.timeline-index,
.episode-meta,
.section-nav small {
  color: var(--muted-light);
  font-size: 14px;
}

.search-box {
  display: block;
  margin-top: 28px;
  max-width: 480px;
}

.search-box span {
  display: none;
}

.search-box input {
  width: 100%;
  padding: 14px 16px;
  border-radius: var(--radius);
  border: 1px solid var(--line-strong);
  background: var(--surface);
  font: inherit;
  font-size: 15px;
  color: var(--ink);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-box input:focus {
  outline: none;
  border-color: var(--ink);
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05);
}

.search-box input::placeholder {
  color: var(--muted-light);
}

.section-header {
  margin: 0 0 32px;
}

.section-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-family: var(--font-sans);
}

.section-header p {
  display: none;
}

.episode-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
  border-top: 1px solid var(--line);
}

.episode-card {
  padding: 28px 0;
  border-bottom: 1px solid var(--line);
  transition: background-color 0.2s;
}

.episode-card:hover {
  background-color: var(--highlight);
}

.episode-card h3 {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
}

.episode-card h3 a {
  text-decoration: none;
  color: var(--ink);
  transition: color 0.15s;
}

.episode-card h3 a:hover {
  color: var(--muted);
}

.episode-summary {
  margin: 0 0 12px;
  color: var(--muted);
  line-height: 1.65;
  font-size: 15px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.episode-meta {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--muted-light);
  display: flex;
  gap: 8px;
}

.episode-links,
.player-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.button-link,
.timestamp {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--ink-light);
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  text-decoration: none;
  transition: all 0.15s ease;
}

.button-link:hover,
.timestamp:hover {
  border-color: var(--ink);
  background: var(--ink);
  color: white;
}

.button-link.subtle {
  background: transparent;
  border-color: transparent;
  color: var(--muted);
}

.button-link.subtle:hover {
  background: transparent;
  border-color: transparent;
  color: var(--ink);
}

.back-link {
  display: inline-block;
  margin-bottom: 32px;
  color: var(--muted);
  font-size: 14px;
  text-decoration: none;
}

.back-link:hover {
  color: var(--ink);
}

.episode-hero {
  padding: 0 0 32px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 32px;
}

.episode-hero .eyebrow {
  display: none;
}

.episode-hero h1 {
  margin: 0 0 16px;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--ink);
}

.episode-hero .hero-copy {
  font-size: 17px;
  margin-bottom: 24px;
}

.episode-facts {
  gap: 24px;
}

.episode-facts div {
  padding: 0;
  background: none;
  border: none;
}

.player-panel {
  margin-top: 24px;
  padding: 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line);
  background: var(--surface);
}

.player-panel audio {
  width: 100%;
  height: 40px;
  border-radius: var(--radius);
}

.episode-layout {
  display: block;
  margin-top: 40px;
}

.episode-sidebar {
  display: none;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-block {
  padding: 32px 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  display: block;
}

.timeline-block:first-child {
  padding-top: 0;
}

.timeline-block:last-child {
  border-bottom: none;
}

.timeline-block .timestamp {
  display: none;
}

.timeline-content p:first-child {
  display: none;
}

.timeline-content p:last-child {
  margin: 0;
  font-size: 18px;
  line-height: 1.8;
  color: var(--ink-light);
  font-family: var(--font-serif);
}

.timeline-block.active {
  background: var(--highlight);
}

.timeline-index {
  display: none;
}

.hidden {
  display: none;
}

hr {
  border: none;
  border-top: 1px solid var(--line);
  margin: 48px 0;
}

.toggle-mode {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 18px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--ink);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-hover);
  transition: all 0.2s ease;
  z-index: 1000;
}

.toggle-mode:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
}

@media (max-width: 920px) {
  .shell {
    width: calc(100% - 32px);
    padding: 32px 0 64px;
  }

  .hero {
    padding: 32px 0 28px;
  }

  .hero h1 {
    font-size: 32px;
  }

  .hero-copy {
    font-size: 16px;
  }

  .hero-stats {
    gap: 20px;
  }

  .episode-grid {
    gap: 0;
  }

  .episode-card {
    padding: 24px 0;
  }

  .episode-card h3 {
    font-size: 20px;
  }

  .episode-summary {
    font-size: 14px;
  }
}

@media (max-width: 640px) {
  .shell {
    width: calc(100% - 24px);
    padding: 24px 0 48px;
  }

  .hero {
    padding: 24px 0 20px;
    margin-bottom: 32px;
  }

  .hero h1 {
    font-size: 28px;
  }

  .hero-stats {
    flex-direction: column;
    gap: 12px;
  }

  .section-header {
    margin-bottom: 24px;
  }

  .episode-card {
    padding: 20px 0;
  }

  .episode-card h3 {
    font-size: 18px;
  }

  .episode-summary {
    font-size: 14px;
    -webkit-line-clamp: 3;
  }

  body[data-page="episode"] .shell {
    padding: 24px 0 48px;
  }

  .episode-hero h1 {
    font-size: 26px;
  }

  .player-panel {
    padding: 16px;
    margin-top: 20px;
  }

  .timeline-content p:last-child {
    font-size: 16px;
    line-height: 1.75;
  }
}

/* ========== 经典版覆盖样式 ========== */
body.classic {
  background:
    radial-gradient(circle at top left, rgba(29, 108, 114, 0.18), transparent 30%),
    radial-gradient(circle at top right, rgba(200, 100, 50, 0.2), transparent 28%),
    linear-gradient(180deg, #fcf7ef 0%, var(--bg) 100%);
  line-height: 1.6;
}

body.classic .shell {
  padding: 28px 0 64px;
}

body.classic .hero,
body.classic .episode-hero {
  padding: 32px;
  border-radius: calc(var(--radius) + 6px);
  border: 1px solid var(--line);
  background: var(--surface);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow);
}

body.classic .hero {
  margin-bottom: 34px;
}

body.classic .hero .eyebrow {
  display: block;
}

body.classic .hero h1 {
  font-size: clamp(40px, 7vw, 76px);
}

body.classic .hero-copy {
  max-width: 720px;
}

body.classic .hero-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

body.classic .hero-stats div {
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(47, 38, 29, 0.08);
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

body.classic .hero-stats span {
  display: block;
  font-size: 24px;
}

body.classic .search-box input {
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
}

body.classic .section-header h2 {
  font-size: 28px;
  text-transform: none;
  letter-spacing: normal;
  font-family: var(--font-serif);
}

body.classic .section-header p {
  display: block;
  margin: 8px 0 0;
}

body.classic .episode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

body.classic .episode-card {
  padding: 22px;
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  background: var(--surface);
  backdrop-filter: blur(14px);
}

body.classic .episode-card:hover {
  transform: translateY(-3px);
}

body.classic .episode-card h3 {
  font-size: 26px;
  margin: 8px 0 12px;
}

body.classic .episode-summary {
  margin: 0 0 18px;
  line-height: 1.7;
}

body.classic .episode-meta {
  margin: 0 0 12px;
}

body.classic .button-link {
  padding: 10px 14px;
  border-radius: 999px;
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

body.classic .button-link:hover {
  background: var(--accent-hover);
}

body.classic .button-link.subtle {
  background: transparent;
  border-color: var(--line);
  color: var(--ink);
}

body.classic .episode-hero .eyebrow {
  display: block;
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-2);
}

body.classic .player-panel {
  margin-top: 18px;
}

body.classic .episode-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 20px;
}

body.classic .episode-sidebar {
  display: block;
  position: sticky;
  top: 20px;
}

body.classic .sidebar-card {
  padding: 18px;
  border: 1px solid var(--line);
  background: var(--surface);
  box-shadow: var(--shadow);
}

body.classic .timeline-block {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 16px;
  padding: 18px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: var(--radius);
}

body.classic .timeline-block .timestamp {
  display: block;
}

body.classic .timeline-content p:first-child {
  display: block;
}

body.classic .timeline-content p:last-child {
  font-size: 18px;
  line-height: 1.9;
}

body.classic .timeline-index {
  display: block;
  margin: 0 0 8px;
  font-size: 13px;
}

@media (max-width: 920px) {
  body.classic .episode-layout {
    grid-template-columns: 1fr;
  }
  body.classic .episode-sidebar {
    position: static;
  }
  body.classic .timeline-block {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  body.classic .shell {
    width: min(100% - 20px, 100%);
  }
  body.classic .hero,
  body.classic .episode-hero,
  body.classic .player-panel,
  body.classic .timeline-block,
  body.classic .episode-card,
  body.classic .sidebar-card {
    padding: 18px;
    border-radius: 20px;
  }
}
"""


APP_JS = """
// ========== 模式切换功能 ==========
(function() {
  var STORAGE_KEY = 'podcast-view-mode';
  var MODES = { READER: 'reader', CLASSIC: 'classic' };

  function getMode() {
    return localStorage.getItem(STORAGE_KEY) || MODES.READER;
  }

  function setMode(mode) {
    document.body.classList.remove(MODES.READER, MODES.CLASSIC);
    if (mode === MODES.CLASSIC) {
      document.body.classList.add(MODES.CLASSIC);
    }
    localStorage.setItem(STORAGE_KEY, mode);
    updateButtonText();
  }

  function createToggleButton() {
    var btn = document.createElement('button');
    btn.className = 'toggle-mode';
    btn.type = 'button';
    btn.addEventListener('click', function() {
      var current = getMode();
      setMode(current === MODES.READER ? MODES.CLASSIC : MODES.READER);
    });
    document.body.appendChild(btn);
    updateButtonText();
  }

  function updateButtonText() {
    var btn = document.querySelector('.toggle-mode');
    if (!btn) return;
    var isClassic = getMode() === MODES.CLASSIC;
    btn.textContent = isClassic ? '阅读版' : '经典版';
  }

  // 初始化
  var currentMode = getMode();
  if (currentMode === MODES.CLASSIC) {
    document.body.classList.add(MODES.CLASSIC);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createToggleButton);
  } else {
    createToggleButton();
  }
})();

// ========== 搜索过滤功能 ==========
var filterInput = document.querySelector('#episode-filter');
var episodeCards = Array.from(document.querySelectorAll('.episode-card'));

if (filterInput && episodeCards.length) {
  filterInput.addEventListener('input', function() {
    var query = filterInput.value.trim().toLowerCase();
    for (var i = 0; i < episodeCards.length; i++) {
      var card = episodeCards[i];
      var haystack = card.dataset.filter || '';
      card.classList.toggle('hidden', Boolean(query) && haystack.indexOf(query) === -1);
    }
  });
}

// ========== 音频播放与时间轴同步 ==========
var audio = document.querySelector('#audio-player');
var seekButtons = Array.from(document.querySelectorAll('[data-seek]'));
var timelineBlocks = Array.from(document.querySelectorAll('.timeline-block'));

for (var i = 0; i < seekButtons.length; i++) {
  (function(button) {
    button.addEventListener('click', function() {
      if (!audio) return;
      var seconds = Number(button.dataset.seek || '0');
      audio.currentTime = seconds;
      audio.play().catch(function() {});
    });
  })(seekButtons[i]);
}

if (audio && timelineBlocks.length) {
  var highlightCurrentBlock = function() {
    var now = audio.currentTime;
    var activeBlock = null;
    for (var i = 0; i < timelineBlocks.length; i++) {
      var block = timelineBlocks[i];
      var start = Number(block.dataset.start || '0');
      var end = Number(block.dataset.end || '0');
      var isActive = now >= start && now < end;
      block.classList.toggle('active', isActive);
      if (isActive) activeBlock = block;
    }
    if (activeBlock && !activeBlock.dataset.scrolled) {
      var top = activeBlock.getBoundingClientRect().top;
      var withinViewport = top > 120 && top < window.innerHeight - 120;
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
