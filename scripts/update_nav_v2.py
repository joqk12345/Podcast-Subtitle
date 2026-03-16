#!/usr/bin/env python3
"""Update pie-podcast-nav-v2.md from urls.txt and v2 SRT filenames.

Input: urls.txt with one media item per line, containing a URL plus either:
- an episode number such as "190"
- an episode media filename such as "pie-ep190.mp3"
- a special media filename such as "pie-4th-anniversary"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ROOT)
V2_DIR = os.path.join(ROOT, "pie-srt", "v2")
NAV_PATH = os.path.join(ROOT, "pie-podcast-nav-v2.md")
URLS_PATH = os.path.join(ROOT, "urls.txt")

LINK_LINE_RE = re.compile(r"^\[(.+?)\]\((.+)\)\s*$")
SUB_LINE_RE = re.compile(r"^\[字幕\]\(\./pie-srt/v2/(.+\.srt)\)\s*$")
ORIG_EP_SRT_RE = re.compile(r"^第\s*(\d+)\s*期\s*(.+?)_原文\.srt$")
ORIG_GENERIC_SRT_RE = re.compile(r"^(.+?)_原文\.srt$")
EP_LABEL_RE = re.compile(r"^第\s*(\d+)\s*期(?:\s+(.*))?$")
URL_IN_LINE_RE = re.compile(r"https?://\S+")
URL_EP_RE = re.compile(r"pie-ep(\d+)\.mp3$")
URL_DATE_RE = re.compile(r"/(20\d{2})/(0[1-9]|1[0-2])/")
ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)")

CIRCLED_NUMERALS = {
    1: "①",
    2: "②",
    3: "③",
    4: "④",
    5: "⑤",
    6: "⑥",
    7: "⑦",
    8: "⑧",
    9: "⑨",
    10: "⑩",
}
CHINESE_NUMERALS = {
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
}


@dataclass(frozen=True)
class UrlEntry:
    media_name: str
    url: str
    episode: Optional[int]
    source_hint: Optional[str]
    date_key: Optional[Tuple[int, int]]


@dataclass(frozen=True)
class NavEntry:
    start: int
    end: int
    label: str
    url: str
    subtitle_name: Optional[str]
    media_name: Optional[str]
    episode: Optional[int]


def parse_media_name_from_url(url: str) -> Optional[str]:
    path = urlsplit(url).path
    media_name = os.path.basename(path)
    if not media_name:
        return None
    if media_name.endswith(".mp3"):
        return media_name
    return None


def parse_episode_from_media_name(media_name: Optional[str]) -> Optional[int]:
    if not media_name:
        return None
    match = URL_EP_RE.search(media_name)
    if not match:
        return None
    return int(match.group(1))


def parse_episode_hint(text: str) -> Optional[int]:
    stripped = text.strip()
    if not stripped:
        return None

    direct = re.fullmatch(r"(\d{1,3})", stripped)
    if direct:
        return int(direct.group(1))

    embedded = re.search(r"pie-ep(\d+)\.mp3", stripped)
    if embedded:
        return int(embedded.group(1))

    return None


def parse_date_key(url: str) -> Optional[Tuple[int, int]]:
    match = URL_DATE_RE.search(url)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def build_media_name(prefix: str, url: str) -> str:
    media_name = parse_media_name_from_url(url)
    if media_name:
        return media_name

    prefix = prefix.strip()
    if prefix.endswith(".mp3"):
        return os.path.basename(prefix)

    episode = parse_episode_hint(prefix)
    if episode is not None:
        return f"pie-ep{episode}.mp3"

    if prefix:
        return f"{prefix}.mp3"

    raise ValueError(f"No media filename or episode number found in line: {prefix} {url}".strip())


def subtitle_name_for_media(media_name: str) -> str:
    return f"{media_name}.srt"


def subtitle_line_for_media(media_name: str) -> str:
    return f"[字幕](./pie-srt/v2/{subtitle_name_for_media(media_name)})"


def subtitle_to_media_name(subtitle_name: str) -> Optional[str]:
    if not subtitle_name.endswith(".srt"):
        return None
    return subtitle_name[:-4]


def parse_urls(path: str) -> Dict[str, UrlEntry]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"urls.txt not found: {path}")

    urls: Dict[str, UrlEntry] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            url_match = URL_IN_LINE_RE.search(line)
            if not url_match:
                raise ValueError(f"No URL found in line: {line}")
            url = url_match.group(0)
            prefix = line[: url_match.start()].strip()
            media_name = build_media_name(prefix, url)
            entry = UrlEntry(
                media_name=media_name,
                url=url,
                episode=parse_episode_from_media_name(media_name) or parse_episode_hint(prefix),
                source_hint=prefix or None,
                date_key=parse_date_key(url),
            )
            existing = urls.get(media_name)
            if existing and existing.url != url:
                raise ValueError(f"Duplicate media with different URL: {media_name}")
            urls[media_name] = entry
    return urls


def parse_episode_from_label(label: str) -> Optional[int]:
    match = EP_LABEL_RE.match(label.strip())
    if not match:
        return None
    return int(match.group(1))


def label_title(label: str, episode: Optional[int]) -> str:
    if episode is None:
        return label.strip()

    match = EP_LABEL_RE.match(label.strip())
    if not match:
        return label.strip()
    return (match.group(2) or "").strip()


def parse_entries(lines: List[str]) -> List[NavEntry]:
    entries: List[NavEntry] = []
    i = 0
    while i < len(lines):
        match = LINK_LINE_RE.match(lines[i].strip())
        if not match or match.group(1) == "字幕":
            i += 1
            continue

        label = match.group(1).strip()
        url = match.group(2).strip()
        if not url.startswith(("http://", "https://")):
            i += 1
            continue
        subtitle_name: Optional[str] = None
        end = i

        if i + 1 < len(lines):
            subtitle_match = SUB_LINE_RE.match(lines[i + 1].strip())
            if subtitle_match:
                subtitle_name = subtitle_match.group(1).strip()
                end = i + 1

        media_name = parse_media_name_from_url(url)
        if not media_name and subtitle_name:
            media_name = subtitle_to_media_name(subtitle_name)

        entries.append(
            NavEntry(
                start=i,
                end=end,
                label=label,
                url=url,
                subtitle_name=subtitle_name,
                media_name=media_name,
                episode=parse_episode_from_label(label) or parse_episode_from_media_name(media_name),
            )
        )
        i = end + 1

    return entries


def format_entry(entry: UrlEntry, title: Optional[str]) -> List[str]:
    if entry.episode is not None:
        label = f"第{entry.episode}期"
        if title:
            label = f"{label} {title}"
    else:
        label = title or entry.source_hint or os.path.splitext(entry.media_name)[0]

    return [
        f"[{label}]({entry.url})",
        subtitle_line_for_media(entry.media_name),
        "",
    ]


def entry_identity(entry: NavEntry) -> Optional[str]:
    if entry.media_name:
        return entry.media_name
    if entry.subtitle_name:
        return subtitle_to_media_name(entry.subtitle_name)
    return None


def is_multiline_link_start(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") and "](" not in stripped


def describe_entry(entry: NavEntry) -> str:
    if entry.episode is not None:
        return f"ep{entry.episode}"
    if entry.media_name:
        return entry.media_name
    return entry.label


def ordinal_variants(text: str) -> Set[str]:
    variants: Set[str] = set()
    match = ORDINAL_RE.search(text)
    if not match:
        return variants

    value = int(match.group(1))
    variants.add(str(value))
    if value in CIRCLED_NUMERALS:
        variants.add(CIRCLED_NUMERALS[value])
    if value in CHINESE_NUMERALS:
        variants.add(CHINESE_NUMERALS[value])
    return variants


def score_special_title(title: str, entry: UrlEntry) -> int:
    title_text = title.strip()
    source_text = " ".join(filter(None, [entry.media_name, entry.source_hint or ""])).lower()
    score = 0

    if "特别篇" in title_text:
        score += 1

    if "anniv" in source_text or "anniversary" in source_text:
        if "周年" in title_text:
            score += 3

    variants = ordinal_variants(source_text)
    if variants and "周年" in title_text and any(variant in title_text for variant in variants):
        score += 4

    return score


def maybe_rename_source(source_name: str, target_name: str, title: str, dry_run: bool) -> Tuple[Optional[str], bool]:
    source_path = os.path.join(V2_DIR, source_name)
    target_path = os.path.join(V2_DIR, target_name)

    if os.path.exists(target_path) and source_path != target_path:
        print(f"warn: target exists, skip rename: {target_name}")
        return title, False

    if source_path != target_path:
        if not dry_run:
            os.rename(source_path, target_path)
        return title, True

    return title, False


def find_title_and_rename(entry: UrlEntry, dry_run: bool = False) -> Tuple[Optional[str], bool]:
    if not os.path.isdir(V2_DIR):
        return None, False

    target_name = subtitle_name_for_media(entry.media_name)

    if entry.episode is not None:
        for name in sorted(os.listdir(V2_DIR)):
            match = ORIG_EP_SRT_RE.match(name)
            if not match or int(match.group(1)) != entry.episode:
                continue
            title = match.group(2).strip()
            return maybe_rename_source(name, target_name, title, dry_run)
        return None, False

    candidates: List[Tuple[int, str, str]] = []
    for name in sorted(os.listdir(V2_DIR)):
        ep_match = ORIG_EP_SRT_RE.match(name)
        if ep_match:
            continue
        title_match = ORIG_GENERIC_SRT_RE.match(name)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        candidates.append((score_special_title(title, entry), title, name))

    if not candidates:
        return None, False

    best_score = max(score for score, _title, _name in candidates)
    if best_score > 0:
        matched = [candidate for candidate in candidates if candidate[0] == best_score]
        if len(matched) == 1:
            _score, title, name = matched[0]
            return maybe_rename_source(name, target_name, title, dry_run)

    if len(candidates) == 1:
        _score, title, name = candidates[0]
        return maybe_rename_source(name, target_name, title, dry_run)

    return None, False


def find_insert_index(lines: List[str], new_entry: UrlEntry) -> int:
    entries = parse_entries(lines)

    if new_entry.episode is not None:
        for entry in entries:
            if entry.episode is not None and entry.episode < new_entry.episode:
                return entry.start
        return len(lines)

    if new_entry.date_key is not None:
        for entry in entries:
            existing_date = parse_date_key(entry.url)
            if existing_date is None:
                continue
            if existing_date < new_entry.date_key:
                return entry.start
        return len(lines)

    return len(lines)


def find_multiline_title_issues(lines: List[str]) -> List[Tuple[int, str]]:
    issues: List[Tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not is_multiline_link_start(line):
            continue
        if i + 1 < len(lines) and lines[i + 1].lstrip().startswith("]("):
            issues.append((i + 1, line.strip()[1:]))
    return issues


def fix_multiline_titles(lines: List[str]) -> Tuple[List[str], int]:
    fixed: List[str] = []
    i = 0
    changes = 0
    while i < len(lines):
        line = lines[i]
        if is_multiline_link_start(line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.lstrip().startswith("]("):
                fixed.append(f"{line.rstrip()}{next_line.lstrip()}")
                i += 2
                changes += 1
                continue
        fixed.append(line)
        i += 1
    return fixed, changes


def fix_subtitle_links(lines: List[str]) -> Tuple[List[str], int]:
    fixed = list(lines)
    changes = 0

    for entry in parse_entries(fixed):
        if entry.subtitle_name is None or entry.media_name is None:
            continue

        expected_line = subtitle_line_for_media(entry.media_name)
        if fixed[entry.end] != expected_line:
            fixed[entry.end] = expected_line
            changes += 1

    return fixed, changes


def validate_nav(lines: List[str]) -> List[str]:
    errors: List[str] = []

    multiline = find_multiline_title_issues(lines)
    for line_no, label_start in multiline:
        errors.append(f"line {line_no}: {label_start!r} has multi-line title (not allowed)")

    seen: Set[str] = set()
    for entry in parse_entries(lines):
        identity = entry_identity(entry)
        if identity and identity in seen:
            errors.append(f"line {entry.start + 1}: duplicate entry for {identity}")
        if identity:
            seen.add(identity)

        if entry.subtitle_name is None:
            errors.append(f"line {entry.start + 1}: missing subtitle line for {describe_entry(entry)}")
            continue

        if entry.media_name:
            expected_subtitle = subtitle_name_for_media(entry.media_name)
            if entry.subtitle_name != expected_subtitle:
                errors.append(
                    f"line {entry.end + 1}: subtitle linked to {entry.subtitle_name} under {describe_entry(entry)}"
                )

        sub_path = os.path.join(V2_DIR, entry.subtitle_name)
        if not os.path.exists(sub_path):
            errors.append(f"line {entry.end + 1}: subtitle file not found: {sub_path}")

    return errors


def run_check() -> int:
    _ = parse_urls(URLS_PATH)
    with open(NAV_PATH, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    errors = validate_nav(lines)
    if errors:
        print("check failed")
        for err in errors:
            print(f"- {err}")
        return 1

    print("check passed")
    return 0


def run_fix_wrap() -> int:
    with open(NAV_PATH, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    fixed_lines, changes = fix_multiline_titles(lines)
    if changes == 0:
        print("fix-wrap complete")
        print("fixed: -")
        return 0

    with open(NAV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(fixed_lines) + "\n")

    print("fix-wrap complete")
    print(f"fixed: {changes}")
    return 0


def run_fix_links() -> int:
    with open(NAV_PATH, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    fixed_lines, changes = fix_subtitle_links(lines)
    if changes == 0:
        print("fix-links complete")
        print("fixed: -")
        return 0

    with open(NAV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(fixed_lines) + "\n")

    print("fix-links complete")
    print(f"fixed: {changes}")
    return 0


def format_status(media_names: List[str], entries: Dict[str, UrlEntry]) -> str:
    if not media_names:
        return "-"

    ordered = sorted(
        media_names,
        key=lambda name: (
            entries[name].episode is not None,
            entries[name].episode or 0,
            name,
        ),
        reverse=True,
    )

    labels: List[str] = []
    for media_name in ordered:
        entry = entries[media_name]
        if entry.episode is not None:
            labels.append(str(entry.episode))
        else:
            labels.append(os.path.splitext(media_name)[0])
    return ", ".join(labels)


def run_update(dry_run: bool = False) -> int:
    urls = parse_urls(URLS_PATH)

    with open(NAV_PATH, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    renamed: List[str] = []
    added: List[str] = []
    updated: List[str] = []

    ordered_entries = sorted(
        urls.values(),
        key=lambda entry: (
            entry.date_key or (0, 0),
            entry.episode is not None,
            entry.episode or 0,
            entry.media_name,
        ),
        reverse=True,
    )

    for url_entry in ordered_entries:
        title, did_rename = find_title_and_rename(url_entry, dry_run=dry_run)
        if did_rename:
            renamed.append(url_entry.media_name)

        entries = parse_entries(lines)
        by_media = {entry_identity(item): item for item in entries if entry_identity(item)}
        existing = by_media.get(url_entry.media_name)

        if existing is not None:
            existing_title = label_title(existing.label, existing.episode)
            if not title:
                title = existing_title or None
            entry_lines = format_entry(url_entry, title)
            lines[existing.start : existing.end + 1] = entry_lines[:2]
            updated.append(url_entry.media_name)
            continue

        entry_lines = format_entry(url_entry, title)
        insert_at = find_insert_index(lines, url_entry)
        lines[insert_at:insert_at] = entry_lines
        added.append(url_entry.media_name)

    if not dry_run:
        with open(NAV_PATH, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    if dry_run:
        print("dry-run complete")
    else:
        print("update complete")
    print(f"renamed: {format_status(renamed, urls)}")
    print(f"added: {format_status(added, urls)}")
    print(f"updated: {format_status(updated, urls)}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update or check pie-podcast-nav-v2.md")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Validate urls/nav consistency only")
    mode.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    mode.add_argument("--fix-wrap", action="store_true", help="Fix multi-line titles in nav file")
    mode.add_argument("--fix-links", action="store_true", help="Fix subtitle links to match media filename")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.check:
        return run_check()
    if args.fix_wrap:
        return run_fix_wrap()
    if args.fix_links:
        return run_fix_links()
    return run_update(dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - simple CLI tool
        print(f"error: {exc}")
        raise SystemExit(1)
