#!/usr/bin/env python3
"""Update pie-podcast-nav-v2.md from urls.txt and v2 SRT filenames.

Input: urls.txt with one episode per line, containing a URL and an episode number
(either as "190" or embedded like "pie-ep190.mp3").
"""

from __future__ import annotations

import os
import re
import sys
from typing import Dict, List, Optional, Tuple

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
            urls[ep] = url
    return urls


def find_title_and_rename(ep: int) -> Optional[str]:
    if not os.path.isdir(V2_DIR):
        return None

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
            return title
        if source_path != target_path:
            os.rename(source_path, target_path)
        return title

    return None


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


def main() -> int:
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
        title = find_title_and_rename(ep)
        if title:
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

    with open(NAV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    def _fmt(nums: List[int]) -> str:
        return ", ".join(str(n) for n in sorted(nums, reverse=True)) if nums else "-"

    print("update complete")
    print(f"renamed: {_fmt(renamed)}")
    print(f"added: {_fmt(added)}")
    print(f"updated: {_fmt(updated)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - simple CLI tool
        print(f"error: {exc}")
        raise SystemExit(1)
