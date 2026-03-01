#!/usr/bin/env python3
"""
Batch subtitle downloader.
Downloads subtitles for multiple YouTube videos, selected by ID or from a JSON list.
"""

import argparse
import json
import os
import sys
import subprocess


def parse_selection(selection: str, total: int) -> list[int]:
    """
    Parse user selection string into list of 0-based indices.
    Supports: "all", "1,3,5", "1-5", "1,3,5-10"
    """
    selection = selection.strip().lower()
    if selection == "all":
        return list(range(total))

    indices = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start.strip()), int(end.strip())
            for i in range(start, end + 1):
                if 1 <= i <= total:
                    indices.add(i - 1)  # convert to 0-based
        else:
            idx = int(part)
            if 1 <= idx <= total:
                indices.add(idx - 1)

    return sorted(indices)


def download_single(video_id: str, title: str, lang: str, auto: bool,
                    fmt: str, output_dir: str, cookies: str | None,
                    script_dir: str) -> bool:
    """Download subtitles for a single video. Returns True on success."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        sys.executable,
        os.path.join(script_dir, "yt_subs.py"),
        url,
        "--lang", lang,
        "--format", fmt,
        "--output", output_dir,
    ]
    if auto:
        cmd.append("--auto")
    if cookies:
        cmd.extend(["--cookies", cookies])

    print(f"\n{'='*60}")
    print(f"📥 [{title}]")
    print(f"   ID: {video_id}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Batch download YouTube subtitles")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ids", help="Comma-separated video IDs")
    group.add_argument("--json", help="Path to JSON file from yt_channel.py")

    parser.add_argument("--select", default="all",
                        help="Selection string when using --json (e.g., '1,3,5-10' or 'all')")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--auto", action="store_true", help="Include auto-generated subtitles")
    parser.add_argument("--format", dest="fmt", default="srt",
                        choices=["srt", "vtt", "txt", "json3"])
    parser.add_argument("--output", default=".", help="Output directory")
    parser.add_argument("--cookies", default=None, help="Path to cookies file")

    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build video list
    videos = []
    if args.ids:
        for vid in args.ids.split(","):
            vid = vid.strip()
            if vid:
                videos.append({"id": vid, "title": vid})
    elif args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_videos = data.get("videos", [])
        if not all_videos:
            print("❌ No videos found in JSON file.")
            sys.exit(1)
        indices = parse_selection(args.select, len(all_videos))
        videos = [all_videos[i] for i in indices]

    if not videos:
        print("❌ No videos selected.")
        sys.exit(1)

    print(f"\n🎬 Downloading subtitles for {len(videos)} video(s)...")
    print(f"   Language: {args.lang} | Format: {args.fmt} | Auto: {args.auto}")
    if args.cookies:
        print(f"   Cookies: {args.cookies}")
    print(f"   Output: {args.output}\n")

    os.makedirs(args.output, exist_ok=True)

    success = 0
    failed = 0
    failed_list = []

    for v in videos:
        ok = download_single(
            video_id=v["id"],
            title=v.get("title", v["id"]),
            lang=args.lang,
            auto=args.auto,
            fmt=args.fmt,
            output_dir=args.output,
            cookies=args.cookies,
            script_dir=script_dir,
        )
        if ok:
            success += 1
        else:
            failed += 1
            failed_list.append(v.get("title", v["id"]))

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Download Summary")
    print(f"{'='*60}")
    print(f"   ✅ Success: {success}")
    print(f"   ❌ Failed:  {failed}")
    if failed_list:
        print(f"\n   Failed videos:")
        for title in failed_list:
            print(f"     - {title}")
    print(f"\n   Output directory: {args.output}")


if __name__ == "__main__":
    main()
