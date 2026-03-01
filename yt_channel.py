#!/usr/bin/env python3
"""
List all videos from a YouTube channel or playlist.
Outputs a numbered list to stdout and writes JSON to /tmp/yt_channel_videos.json.
"""

import argparse
import json
import subprocess
import sys


def list_channel_videos(url: str, max_videos: int = 50, cookies: str | None = None) -> list[dict]:
    """Fetch video list from a YouTube channel or playlist."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(duration_string)s",
        "--playlist-end", str(max_videos),
        "--no-warnings",
        url,
    ]
    if cookies:
        cmd.extend(["--cookies", cookies])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip()
        print(f"❌ Error fetching channel videos: {error_msg}", file=sys.stderr)
        sys.exit(1)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            video = {
                "id": parts[0].strip(),
                "title": parts[1].strip(),
                "duration": parts[2].strip() if len(parts) >= 3 else "N/A",
            }
            videos.append(video)

    return videos


def main():
    parser = argparse.ArgumentParser(description="List videos from a YouTube channel or playlist")
    parser.add_argument("url", help="YouTube channel or playlist URL")
    parser.add_argument("--max", type=int, default=50, help="Max videos to retrieve (default: 50)")
    parser.add_argument("--cookies", default=None, help="Path to Netscape-format cookies file")

    args = parser.parse_args()
    videos = list_channel_videos(args.url, args.max, args.cookies)

    if not videos:
        print("❌ No videos found. Check the URL or try with --cookies.")
        sys.exit(1)

    # Print numbered list
    print(f"\n📺 Found {len(videos)} video(s):\n")
    print(f"{'#':<5} {'ID':<15} {'Duration':<12} Title")
    print("-" * 80)
    for i, v in enumerate(videos, 1):
        title_display = v['title'][:48] + "..." if len(v['title']) > 50 else v['title']
        print(f"{i:<5} {v['id']:<15} {v['duration']:<12} {title_display}")

    # Write JSON
    output_path = "/tmp/yt_channel_videos.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"total": len(videos), "videos": videos}, f, ensure_ascii=False, indent=2)

    print(f"\n📄 Full list saved to: {output_path}")
    print(f"\nEnter video numbers to download (e.g., 1,3,5-10) or 'all'.")


if __name__ == "__main__":
    main()
