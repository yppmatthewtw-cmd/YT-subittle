#!/usr/bin/env python3
"""
YouTube Subtitle Downloader — single video.
Uses yt-dlp to download subtitles/captions from a YouTube video.
Supports cookie files for authenticated access.
"""

import argparse
import os
import re
import subprocess
import sys


def run_ytdlp(args: list[str]) -> subprocess.CompletedProcess:
    """Run yt-dlp with given arguments."""
    cmd = ["yt-dlp"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def list_subtitles(url: str, cookies: str | None = None) -> None:
    """List all available subtitles for a video."""
    cmd = ["--list-subs", "--no-download", url]
    if cookies:
        cmd.extend(["--cookies", cookies])
    result = run_ytdlp(cmd)
    print(result.stdout + result.stderr)


def strip_timestamps_srt(text: str) -> str:
    """Convert SRT content to plain text."""
    lines = text.strip().split("\n")
    out = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line):
            continue
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(line)
    result = "\n".join(out).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def strip_timestamps_vtt(text: str) -> str:
    """Convert VTT content to plain text."""
    lines = text.strip().split("\n")
    out = []
    skip_header = True
    for line in lines:
        line = line.strip()
        if skip_header:
            if line == "" and out == []:
                skip_header = False
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        clean = re.sub(r"<[^>]+>", "", line)
        if clean.strip():
            out.append(clean.strip())
    result = "\n".join(out).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def download_subtitles(
    url: str,
    lang: str = "en",
    auto: bool = False,
    fmt: str = "srt",
    output_dir: str = ".",
    cookies: str | None = None,
) -> str | None:
    """Download subtitles. Returns path to file or None on failure."""
    os.makedirs(output_dir, exist_ok=True)
    dl_fmt = "srt" if fmt == "txt" else fmt

    args = [
        "--skip-download",
        "--sub-lang", lang,
        "--sub-format", dl_fmt,
        "--convert-subs", dl_fmt,
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
    ]

    if cookies:
        args.extend(["--cookies", cookies])

    if auto:
        args.append("--write-auto-sub")
    else:
        args.append("--write-sub")

    args.append(url)
    result = run_ytdlp(args)
    combined = result.stdout + result.stderr

    # Check for failure
    if result.returncode != 0 or "has no subtitles" in combined.lower():
        if not auto:
            print(f"⚠️  No manual subtitles for language '{lang}'. Retrying with auto-generated...")
            return download_subtitles(url, lang, auto=True, fmt=fmt, output_dir=output_dir, cookies=cookies)
        else:
            print(f"❌ No subtitles found for language '{lang}' (including auto-generated).")
            print("\nAvailable subtitles:")
            list_subtitles(url, cookies)
            return None

    # Find downloaded file
    sub_file = None
    for f in sorted(os.listdir(output_dir), key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True):
        if f.endswith(f".{dl_fmt}"):
            candidate = os.path.join(output_dir, f)
            if os.path.getsize(candidate) > 0:
                sub_file = candidate
                break

    if not sub_file:
        print("❌ Subtitle file was not created. yt-dlp output:")
        print(combined)
        return None

    # Convert to plain text if requested
    if fmt == "txt":
        with open(sub_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        plain = strip_timestamps_srt(content) if dl_fmt == "srt" else strip_timestamps_vtt(content)
        txt_file = re.sub(rf"\.{dl_fmt}$", ".txt", sub_file)
        with open(txt_file, "w", encoding="utf-8") as fh:
            fh.write(plain)
        if txt_file != sub_file:
            os.remove(sub_file)
        sub_file = txt_file

    print(f"✅ Downloaded: {sub_file}")
    return sub_file


def main():
    parser = argparse.ArgumentParser(description="Download YouTube subtitles")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--auto", action="store_true", help="Include auto-generated subtitles")
    parser.add_argument("--format", dest="fmt", default="srt", choices=["srt", "vtt", "txt", "json3"])
    parser.add_argument("--list", action="store_true", help="List available languages")
    parser.add_argument("--output", default=".", help="Output directory")
    parser.add_argument("--cookies", default=None, help="Path to cookies file")

    args = parser.parse_args()

    if args.list:
        list_subtitles(args.url, args.cookies)
        sys.exit(0)

    result = download_subtitles(
        url=args.url, lang=args.lang, auto=args.auto,
        fmt=args.fmt, output_dir=args.output, cookies=args.cookies,
    )
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
