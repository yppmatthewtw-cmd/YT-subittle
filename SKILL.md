---
name: yt-subtitles
description: >
  Download YouTube video subtitles/captions from individual videos or entire channels using yt-dlp.
  Trigger this skill when the user types the command `/subtitle`, or mentions 'YouTube subtitles',
  'YouTube captions', 'download subtitles', 'extract captions', 'get transcript from YouTube',
  'channel subtitles', 'batch subtitle download', or any request involving obtaining text/transcript
  from YouTube video or channel URLs. Also trigger when the user wants to list available subtitle
  languages, list videos from a channel, or do bulk subtitle downloads.
  This skill is compatible with both Claude (claude.ai / Claude Code) and OpenClaw environments.
---

# YouTube Subtitle Downloader

Batch-download subtitles from YouTube videos or entire channels using `yt-dlp`.

## Compatibility

This skill works in **both Claude and OpenClaw** environments. The workflow and scripts are identical — the only difference is how the host model interacts with the user (chat UI vs CLI). All scripts use standard Python + yt-dlp with no platform-specific dependencies.

## Setup

```bash
pip install "yt-dlp[default,curl-cffi]" --break-system-packages -q
```

`curl-cffi` enables browser impersonation, which Patreon requires.

## Interactive Workflow (triggered by `/subtitle`)

When the user types `/subtitle`, follow these 4 steps **in order**. Do NOT skip steps.

### Step 1 — Acknowledge command

Respond: "Ready to download YouTube subtitles. Please paste a **YouTube channel URL** or a **single video URL**."

### Step 2 — Receive URL and determine type

The user provides a URL. Determine whether it is:
- **Channel/playlist URL** — contains `/channel/`, `/@`, `/c/`, or `/playlist?list=`
- **Single video URL** — contains `watch?v=` or `youtu.be/`
- **Patreon post URL** — contains `patreon.com/<creator>/posts/` (treated as a single video)

For a **single video** or **Patreon post**, skip to Step 4 (no need to list videos).

For a **channel/playlist**, proceed to Step 3.

### Step 3 — List videos and let user select

Run the channel listing script:

```bash
python <skill-path>/scripts/yt_channel.py "<CHANNEL_URL>"
```

This outputs a numbered list of videos (title + ID). Present the list to the user and ask:

> "Here are the videos found on this channel. Which ones would you like to download subtitles for?
> Enter video numbers (e.g., `1,3,5-10,all`) or type `all` for everything."

Parse the user's selection. The script also outputs a JSON file at `/tmp/yt_channel_videos.json` that you can read programmatically.

### Step 4 — Cookie file and download

Ask the user:

> "Some channels require authentication to access. If you have a **cookies file** (Netscape format, exported from your browser), please upload it now. Otherwise, type `skip` to proceed without cookies."

**Patreon posts:** patron-only posts always need a cookies file exported while logged in to a
patron account. `yt_subs.py` resolves the post's embedded video (YouTube, Vimeo, or Patreon-hosted)
through yt-dlp's Patreon extractor; subtitle availability depends on the underlying video host.

**How cookies work:**
- If the user uploads a file, note its path (in Claude: `/mnt/user-data/uploads/<filename>`; in OpenClaw: the path provided by the runtime)
- If the user types `skip`, proceed without `--cookies`

Then run the download script for each selected video:

```bash
python <skill-path>/scripts/yt_subs.py "<VIDEO_URL>" \
  --lang <lang> --format <format> --auto \
  --output /mnt/user-data/outputs/ \
  [--cookies <cookie-file-path>]
```

Default `--lang` is `en`. Default `--format` is `srt`. Always include `--auto` for maximum coverage.

If the user hasn't specified a language, first run with `--list` on one video to show available languages, then ask the user to choose.

After all downloads complete, present the output files to the user.

---

## Scripts Reference

### `scripts/yt_channel.py`

List all videos from a YouTube channel or playlist.

```
Usage: python scripts/yt_channel.py <CHANNEL_OR_PLAYLIST_URL> [--max N] [--cookies FILE]

Options:
  --max N         Maximum number of videos to retrieve (default: 50)
  --cookies FILE  Path to Netscape-format cookies file
```

**Output:** Prints a numbered list to stdout AND writes JSON to `/tmp/yt_channel_videos.json`.

### `scripts/yt_subs.py`

Download subtitles for a single video (YouTube URL or Patreon post URL).

```
Usage: python scripts/yt_subs.py <VIDEO_URL|PATREON_POST_URL> [options]

Options:
  --lang LANG      Subtitle language code (default: en)
  --auto           Include auto-generated subtitles
  --format FORMAT  Output format: srt, vtt, txt, json3 (default: srt)
  --list           List available subtitle languages and exit
  --output DIR     Output directory (default: current directory)
  --cookies FILE   Path to Netscape-format cookies file
```

### `scripts/yt_batch.py`

Batch-download subtitles for multiple videos at once.

```
Usage: python scripts/yt_batch.py --ids "ID1,ID2,ID3" [options]
       python scripts/yt_batch.py --json /tmp/yt_channel_videos.json --select "1,3,5-10" [options]

Options:
  --lang LANG      Subtitle language code (default: en)
  --auto           Include auto-generated subtitles
  --format FORMAT  Output format: srt, vtt, txt, json3 (default: srt)
  --output DIR     Output directory (default: current directory)
  --cookies FILE   Path to Netscape-format cookies file
```

## Error Handling

- If `yt-dlp` is not installed, the scripts print an install command and exit.
- If no subtitles exist for the requested language, available languages are listed.
- If a cookie file is invalid or expired, a clear error message is shown.
- Network errors produce human-readable messages with retry suggestions.

## Platform Notes

| Feature | Claude (claude.ai) | OpenClaw |
|---------|-------------------|----------|
| User uploads | `/mnt/user-data/uploads/` | Runtime-provided path |
| Output files | `/mnt/user-data/outputs/` | User-specified or `./output/` |
| Present files | Use `present_files` tool | Print file paths |
| Install packages | `pip install --break-system-packages` | `pip install` |
