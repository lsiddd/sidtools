#!/usr/bin/env python3
"""Download a YouTube video's transcript from its URL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_LANGUAGES = ("pt-BR", "pt", "en")


def extract_video_id(url_or_id: str) -> str:
    """Return the 11-character YouTube video id from a URL or raw id."""
    value = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host.endswith("youtu.be") and path_parts:
        return path_parts[0]

    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id

        if path_parts and path_parts[0] in {"shorts", "embed", "live"} and len(path_parts) > 1:
            return path_parts[1]

    raise ValueError(f"nao foi possivel extrair o id do video: {url_or_id}")


def fetch_transcript(video_id: str, languages: list[str]) -> tuple[list[dict], str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.formatters import JSONFormatter
    except ImportError as exc:
        raise SystemExit(
            "Dependencia ausente: instale com `python -m pip install youtube-transcript-api` "
            "ou rode com `uv run --with youtube-transcript-api python download_transcript.py <url>`."
        ) from exc

    api = YouTubeTranscriptApi()

    if hasattr(api, "fetch"):
        transcript = api.fetch(video_id, languages=languages)
        fetched_language = getattr(transcript, "language_code", languages[0] if languages else "unknown")
        json_text = JSONFormatter().format_transcript(transcript)
        return json.loads(json_text), fetched_language

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    try:
        transcript = transcript_list.find_transcript(languages)
    except Exception:
        transcript = next(iter(transcript_list))
    return transcript.fetch(), transcript.language_code


def format_txt(items: list[dict]) -> str:
    lines = []
    for item in items:
        text = item.get("text", "").replace("\n", " ").strip()
        if text:
            lines.append(text)
    return "\n".join(lines) + "\n"


def srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def format_srt(items: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(items, start=1):
        start = float(item.get("start", 0))
        duration = float(item.get("duration", 0))
        text = item.get("text", "").strip()
        if not text:
            continue
        blocks.append(
            f"{index}\n"
            f"{srt_timestamp(start)} --> {srt_timestamp(start + duration)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks)


def render(items: list[dict], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(items, ensure_ascii=False, indent=2) + "\n"
    if output_format == "srt":
        return format_srt(items)
    return format_txt(items)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa a transcricao de um video do YouTube.")
    parser.add_argument("url", help="URL do YouTube ou ID do video")
    parser.add_argument(
        "-l",
        "--language",
        dest="languages",
        action="append",
        help="Idioma preferido, na ordem de prioridade. Pode ser usado mais de uma vez.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("txt", "json", "srt"),
        default="txt",
        help="Formato de saida (padrao: txt).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Arquivo de saida. Por padrao usa transcript_<video_id>.<formato>.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    video_id = extract_video_id(args.url)
    languages = args.languages or list(DEFAULT_LANGUAGES)
    output_path = args.output or Path(f"transcript_{video_id}.{args.format}")

    items, language = fetch_transcript(video_id, languages)
    output_path.write_text(render(items, args.format), encoding="utf-8")

    print(f"Transcricao salva em {output_path} (video={video_id}, idioma={language}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
