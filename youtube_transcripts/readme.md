# youtube_transcripts

Downloads a YouTube video's transcript (auto-generated or manually submitted) from a URL or bare video ID.

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
```

## Output formats

- **`txt`** — plain text, one caption segment per line, no timestamps.
- **`srt`** — numbered blocks with `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps. Compatible with most video players and subtitle editors.
- **`json`** — raw list of objects with `text`, `start`, and `duration` fields.

## Dependencies

Declared in `requirements.txt`:

```
youtube-transcript-api>=1.0.0
```

Install with `uv` or pass `--with youtube-transcript-api` directly to `uv run` as shown above.
