#!/usr/bin/env python3
"""Update pie-srt/duration.csv from the podcast RSS feed."""

from __future__ import annotations

import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ROOT)
CSV_PATH = os.path.join(ROOT, "pie-srt", "duration.csv")
FEED_URL = "https://hosting.wavpub.cn/pie/feed/"

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def normalize_duration(raw: str) -> str:
    text = raw.strip()
    if not text:
        raise ValueError("empty duration")
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            mm, ss = parts
            hh = "00"
        elif len(parts) == 3:
            hh, mm, ss = parts
        else:
            raise ValueError(f"unsupported duration format: {raw}")
        return f"{int(hh):02d}:{int(mm):02d}:{int(ss):02d}"
    if text.isdigit():
        total = int(text)
        hh = total // 3600
        mm = (total % 3600) // 60
        ss = total % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    raise ValueError(f"unsupported duration format: {raw}")


def fetch_feed(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_feed(xml_text: str) -> Dict[str, str]:
    root = ET.fromstring(xml_text)
    durations: Dict[str, str] = {}
    for item in root.findall("./channel/item"):
        enclosure = item.find("enclosure")
        if enclosure is None:
            continue
        url = enclosure.attrib.get("url", "")
        if not url:
            continue
        filename = os.path.basename(url)
        if not filename.endswith(".mp3"):
            continue
        duration_node = item.find(f"{{{ITUNES_NS}}}duration")
        if duration_node is None or not duration_node.text:
            continue
        try:
            duration = normalize_duration(duration_node.text)
        except ValueError:
            continue
        durations[filename] = duration
    return durations


def read_existing(path: str) -> Dict[str, str]:
    existing: Dict[str, str] = {}
    if not os.path.exists(path):
        return existing
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or "," not in line:
                continue
            name, duration = line.split(",", 1)
            existing[name] = duration
    return existing


def sort_key(name: str) -> Tuple[int, int, str]:
    match = re.match(r"^ep(\d+)\.mp3$", name)
    if match:
        return (0, int(match.group(1)), "")
    match = re.match(r"^pie-ep(\d+)\.mp3$", name)
    if match:
        return (1, int(match.group(1)), "")
    return (2, 0, name)


def main() -> int:
    xml_text = fetch_feed(FEED_URL)
    fetched = parse_feed(xml_text)
    existing = read_existing(CSV_PATH)

    updated = 0
    added = 0
    for name, duration in fetched.items():
        if name in existing:
            if existing[name] != duration:
                existing[name] = duration
                updated += 1
        else:
            existing[name] = duration
            added += 1

    names = sorted(existing.keys(), key=sort_key)
    with open(CSV_PATH, "w", encoding="utf-8") as handle:
        for name in names:
            handle.write(f"{name},{existing[name]}\n")

    print("duration.csv update complete")
    print(f"fetched: {len(fetched)}")
    print(f"added: {added}")
    print(f"updated: {updated}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - simple CLI tool
        print(f"error: {exc}")
        raise SystemExit(1)
