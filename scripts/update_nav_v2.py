#!/usr/bin/env python3
"""Update pie-podcast-nav-v2.md from urls.txt and v2 SRT filenames.

Input: urls.txt with one episode per line, containing a URL and an episode number
(either as "190" or embedded like "pie-ep190.mp3").
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ROOT)
V2_DIR = os.path.join(ROOT, "pie-srt", "v2")
NAV_PATH = os.path.join(ROOT, "pie-podcast-nav-v2.md")
URLS_PATH = os.path.join(ROOT, "urls.txt")

EP_LINE_RE = re.compile(r"^\[第(\d+)期(?:\s*(.*?))?\]\((.+)\)\s*$")
SUB_LINE_RE = re.compile(r"^\[字幕\]\(\./pie-srt/v2/pie-ep(\d+)\.mp3\.srt\)\s*$")
ORIG_SRT_RE = re.compile(r"^第(\d+)期\s*(.+?)_原文\.srt$")
URL_IN_LINE_RE = re.compile(r"https?://\S+")
URL_EP_RE = re.compile(r"pie-ep(\d+)\.mp3")
EP_NUM_RE = re.compile(r"\b(\d{3})\b")
EP_LINE_START_RE = re.compile(r"^\[第(\d+)期")


def parse_urls(path: str) -> Dict[int, str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"urls.txt not found: {path}")

    urls: Dict[int, str] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            url_match = URL_IN_LINE_RE.search(line)
            if not url_match:
                raise ValueError(f"No URL found in line: {line}")
            url = url_match.group(0)
            ep_match = URL_EP_RE.search(line) or EP_NUM_RE.search(line)
            if not ep_match:
                raise ValueError(f"No episode number found in line: {line}")
            ep = int(ep_match.group(1))
            if ep in urls and urls[ep] != url:
                raise ValueError(f"Duplicate episode with different URL: ep{ep}")
            urls[ep] = url
    return urls


def find_title_and_rename(ep: int, dry_run: bool = False) -> Tuple[Optional[str], bool]:
    if not os.path.isdir(V2_DIR):
        return None, False

    target_name = f"pie-ep{ep}.mp3.srt"
    target_path = os.path.join(V2_DIR, target_name)

    for name in os.listdir(V2_DIR):
        match = ORIG_SRT_RE.match(name)
        if not match:
            continue
        if int(match.group(1)) != ep:
            continue
        title = match.group(2).strip()
        source_path = os.path.join(V2_DIR, name)
        if os.path.exists(target_path) and source_path != target_path:
            print(f"warn: target exists, skip rename: {target_name}")
            return title, False
        if source_path != target_path:
            if not dry_run:
                os.rename(source_path, target_path)
            return title, True
        return title, False

    return None, False


def parse_entries(lines: List[str]) -> List[Tuple[int, int, int, str, str]]:
    entries = []
    i = 0
    while i < len(lines):
        match = EP_LINE_RE.match(lines[i])
        if not match:
            i += 1
            continue
        ep = int(match.group(1))
        title = (match.group(2) or "").strip()
        url = match.group(3).strip()
        start = i
        end = i
        if i + 1 < len(lines) and SUB_LINE_RE.match(lines[i + 1]):
            end = i + 1
        entries.append((start, end, ep, title, url))
        i = end + 1
    return entries


def format_entry(ep: int, title: Optional[str], url: str) -> List[str]:
    label = f"第{ep}期"
    if title:
        label = f"{label} {title}"
    line1 = f"[{label}]({url})"
    line2 = f"[字幕](./pie-srt/v2/pie-ep{ep}.mp3.srt)"
    return [line1, line2, ""]


def find_insert_index(lines: List[str], new_ep: int) -> int:
    i = 0
    while i < len(lines):
        match = EP_LINE_RE.match(lines[i])
        if not match:
            i += 1
            continue
        ep = int(match.group(1))
        if ep < new_ep:
            return i
        # skip subtitle line if present
        if i + 1 < len(lines) and SUB_LINE_RE.match(lines[i + 1]):
            i += 2
        else:
            i += 1
    return len(lines)


def find_multiline_title_issues(lines: List[str]) -> List[Tuple[int, int]]:
    issues: List[Tuple[int, int]] = []
    for i, line in enumerate(lines):
        m = EP_LINE_START_RE.match(line.strip())
        if not m:
            continue
        if "](" in line:
            continue
        if i + 1 < len(lines) and lines[i + 1].lstrip().startswith("]("):
            issues.append((i + 1, int(m.group(1))))
    return issues


def fix_multiline_titles(lines: List[str]) -> Tuple[List[str], int]:
    fixed: List[str] = []
    i = 0
    changes = 0
    while i < len(lines):
        line = lines[i]
        m = EP_LINE_START_RE.match(line.strip())
        if m and "](" not in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.lstrip().startswith("]("):
                merged = f"{line.rstrip()}{next_line.lstrip()}"
                fixed.append(merged)
                i += 2
                changes += 1
                continue
        fixed.append(line)
        i += 1
    return fixed, changes


def fix_subtitle_links(lines: List[str]) -> Tuple[List[str], int]:
    fixed = list(lines)
    changes = 0
    i = 0
    while i < len(fixed):
        ep_match = EP_LINE_RE.match(fixed[i].strip())
        if not ep_match:
            i += 1
            continue
        ep = int(ep_match.group(1))
        sub_idx = i + 1
        if sub_idx < len(fixed):
            sub_match = SUB_LINE_RE.match(fixed[sub_idx].strip())
            if sub_match:
                sub_ep = int(sub_match.group(1))
                if sub_ep != ep:
                    fixed[sub_idx] = f"[字幕](./pie-srt/v2/pie-ep{ep}.mp3.srt)"
                    changes += 1
        i += 1
    return fixed, changes


def validate_nav(lines: List[str]) -> List[str]:
    errors: List[str] = []

    multiline = find_multiline_title_issues(lines)
    for line_no, ep in multiline:
        errors.append(f"line {line_no}: ep{ep} has multi-line title (not allowed)")

    entries = parse_entries(lines)
    seen: Set[int] = set()
    for start, _end, ep, _title, _url in entries:
        if ep in seen:
            errors.append(f"line {start + 1}: duplicate episode entry ep{ep}")
        seen.add(ep)

        sub_idx = start + 1
        if sub_idx >= len(lines) or not SUB_LINE_RE.match(lines[sub_idx]):
            errors.append(f"line {start + 1}: missing subtitle line for ep{ep}")
            continue
        sub_match = SUB_LINE_RE.match(lines[sub_idx])
        assert sub_match is not None
        sub_ep = int(sub_match.group(1))
        if sub_ep != ep:
            errors.append(f"line {sub_idx + 1}: ep{sub_ep} subtitle linked under ep{ep}")
        sub_path = os.path.join(V2_DIR, f"pie-ep{sub_ep}.mp3.srt")
        if not os.path.exists(sub_path):
            errors.append(f"line {sub_idx + 1}: subtitle file not found: {sub_path}")

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


def run_update(dry_run: bool = False) -> int:
    urls = parse_urls(URLS_PATH)

    with open(NAV_PATH, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]

    entries = parse_entries(lines)
    by_ep = {ep: (start, end, title, url) for start, end, ep, title, url in entries}

    renamed: List[int] = []
    added: List[int] = []
    updated: List[int] = []

    for ep in sorted(urls.keys(), reverse=True):
        url = urls[ep]
        title, did_rename = find_title_and_rename(ep, dry_run=dry_run)
        if did_rename:
            renamed.append(ep)
        if ep in by_ep:
            start, end, existing_title, _existing_url = by_ep[ep]
            if not title:
                title = existing_title
            entry_lines = format_entry(ep, title, url)
            # replace existing block, preserve any blank line after
            lines[start : end + 1] = entry_lines[:2]
            updated.append(ep)
        else:
            entry_lines = format_entry(ep, title, url)
            insert_at = find_insert_index(lines, ep)
            lines[insert_at:insert_at] = entry_lines
            added.append(ep)

    if not dry_run:
        with open(NAV_PATH, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _fmt(nums: List[int]) -> str:
        return ", ".join(str(n) for n in sorted(nums, reverse=True)) if nums else "-"

    if dry_run:
        print("dry-run complete")
    else:
        print("update complete")
    print(f"renamed: {_fmt(renamed)}")
    print(f"added: {_fmt(added)}")
    print(f"updated: {_fmt(updated)}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update or check pie-podcast-nav-v2.md")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Validate urls/nav consistency only")
    mode.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    mode.add_argument("--fix-wrap", action="store_true", help="Fix multi-line titles in nav file")
    mode.add_argument("--fix-links", action="store_true", help="Fix subtitle links to match episode number")
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
