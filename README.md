# YT-Subtitle

A YouTube subtitle/caption batch downloader powered by `yt-dlp`. Designed as a **Claude AI Skill** (compatible with both [Claude.ai](https://claude.ai) and [OpenClaw](https://openclaw.com)), but also works as a standalone CLI tool.

## Features

- 📺 **Channel/Playlist support** — List all videos from a YouTube channel and select which ones to download
- 🌍 **Multi-language** — Download subtitles in any available language
- 🤖 **Auto-generated subs** — Fall back to YouTube's auto-generated captions when manual subs aren't available
- 📄 **Multiple formats** — Export as SRT, VTT, plain text (timestamps stripped), or JSON3
- 🍪 **Cookie support** — Use browser cookies for age-restricted or members-only content
- 🔄 **Batch download** — Download subtitles for multiple videos in one go
- 🧠 **AI Skill** — Use as a Claude/OpenClaw skill with the `/subtitle` command

## Quick Start

### Prerequisites

```bash
pip install yt-dlp
```

### Download subtitles from a single video

```bash
python scripts/yt_subs.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang en --format srt
```

### List videos from a channel

```bash
python scripts/yt_channel.py "https://www.youtube.com/@ChannelName"
```

### Batch download from a channel

```bash
# Step 1: List videos (saves JSON to /tmp/yt_channel_videos.json)
python scripts/yt_channel.py "https://www.youtube.com/@ChannelName"

# Step 2: Download selected videos' subtitles
python scripts/yt_batch.py --json /tmp/yt_channel_videos.json --select "1,3,5-10" --lang en --auto
```

## Usage

### `yt_subs.py` — Single Video

```
python scripts/yt_subs.py <URL> [options]

Options:
  --lang LANG      Language code (default: en)
  --auto           Include auto-generated subtitles
  --format FORMAT  srt | vtt | txt | json3 (default: srt)
  --list           List available subtitle languages
  --output DIR     Output directory
  --cookies FILE   Netscape-format cookies file
```

### `yt_channel.py` — List Channel Videos

```
python scripts/yt_channel.py <CHANNEL_URL> [options]

Options:
  --max N          Max videos to retrieve (default: 50)
  --cookies FILE   Netscape-format cookies file
```

### `yt_batch.py` — Batch Download

```
python scripts/yt_batch.py --ids "ID1,ID2,ID3" [options]
python scripts/yt_batch.py --json /tmp/yt_channel_videos.json --select "1,3,5-10" [options]

Options:
  --lang LANG      Language code (default: en)
  --auto           Include auto-generated subtitles
  --format FORMAT  srt | vtt | txt | json3 (default: srt)
  --output DIR     Output directory
  --cookies FILE   Netscape-format cookies file
```

## Using as a Claude AI Skill

### Method 1: Upload `.skill` file

1. Download `yt-subtitles.skill` from [Releases](../../releases)
2. Open a **Project** on [claude.ai](https://claude.ai)
3. Upload the `.skill` file to the project knowledge
4. Type `/subtitle` to start

### Method 2: Manual setup

1. Create a new Project on claude.ai
2. Upload `SKILL.md` + all 3 scripts in `scripts/` as project knowledge
3. Type `/subtitle` to start

### Workflow

```
/subtitle
  → Paste YouTube channel or video URL
  → See list of videos, select which to download
  → Optionally provide cookies file
  → Subtitles downloaded!
```

## Cookie File

Some videos require authentication (age-restricted, members-only). To export cookies:

1. Install a browser extension like [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Log into YouTube
3. Export cookies as Netscape format `.txt` file
4. Provide the file when prompted

## Project Structure

```
YT-subtitle/
├── README.md
├── SKILL.md              # Claude/OpenClaw skill instructions
├── requirements.txt
├── LICENSE
└── scripts/
    ├── yt_subs.py        # Single video subtitle download
    ├── yt_channel.py     # List channel videos
    └── yt_batch.py       # Batch download
```

## License

MIT License — see [LICENSE](LICENSE) for details.
