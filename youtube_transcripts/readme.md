# youtube_transcripts

Downloads transcripts (auto-generated or manually submitted) from YouTube videos
or from the latest/all videos published by a channel.

## URL formats supported

All standard YouTube URL forms work:

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/live/VIDEO_ID`
- bare 11-character video ID

## Usage

```bash
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> [options]
```

| Option | Description |
|---|---|
| `-l`, `--language LANG` | Preferred language (repeatable, in priority order) |
| `-f`, `--format` | Output format: `txt` (default), `srt`, `json` |
| `-o`, `--output PATH` | Output file path (default: `transcript_<video_id>.<format>`) |
| `--channel CHANNEL` | Channel URL or `@handle` |
| `--latest N` | With `--channel`, download the latest N videos |
| `--all` | With `--channel`, download all videos |

Default language fallback order: `pt-BR → pt → en`.

## Examples

```bash
# Plain text, default languages
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py https://youtu.be/dQw4w9WgXcQ

# SRT with timestamps
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> -f srt -o subtitles.srt

# Specific language priority
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> -l en -l pt-BR

# Raw JSON
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> -f json

# Latest 10 videos from a channel
uv run youtube_transcripts/download_transcript.py --channel @handle --latest 10

# Every video from a channel
uv run youtube_transcripts/download_transcript.py --channel https://www.youtube.com/@handle --all
```

## Output formats

- **`txt`** — plain text, one caption segment per line, no timestamps.
- **`srt`** — numbered blocks with `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps. Compatible with most video players and subtitle editors.
- **`json`** — raw list of objects with `text`, `start`, and `duration` fields.

## Dependencies

Declared in `requirements.txt`:

```
youtube-transcript-api>=1.0.0
yt-dlp
```

The script's PEP 723 header lets `uv run download_transcript.py ...` install both
dependencies automatically.
