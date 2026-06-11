#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "youtube-transcript-api",
# ]
# ///
"""Download a YouTube video's transcript from its URL."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi


DEFAULT_LANGUAGES = ("pt-BR", "pt", "en")
ANNOTATION_RE = re.compile(r"\[.*?\]|\(.*?\)")


class TranscriptError(Exception):
    pass


def extract_video_id(url_or_id: str) -> str:
    value = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path_parts = [p for p in parsed.path.split("/") if p]

    if host.endswith("youtu.be") and path_parts:
        return path_parts[0]

    if "youtube.com" in host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            return query_id
        if path_parts and path_parts[0] in {"shorts", "embed", "live"} and len(path_parts) > 1:
            return path_parts[1]

    raise ValueError(f"não foi possível extrair o ID do vídeo: {url_or_id!r}")


def fetch_video_title(video_id: str) -> str:
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())["title"]


def slugify(title: str) -> str:
    title = unicodedata.normalize("NFKC", title)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)
    title = re.sub(r"\s+", " ", title).strip(". ")
    return (title or "transcript")[:200]


def _transcript_list(video_id: str):
    api = YouTubeTranscriptApi()
    try:
        return api.list(video_id)
    except TranscriptsDisabled:
        raise TranscriptError(f"transcrições desabilitadas para {video_id}")
    except Exception as exc:
        raise TranscriptError(f"erro ao acessar transcrições: {exc}") from exc


def list_languages(video_id: str) -> None:
    transcript_list = _transcript_list(video_id)
    print(f"Idiomas disponíveis para {video_id}:")
    for t in transcript_list:
        flags = []
        if t.is_generated:
            flags.append("gerada automaticamente")
        if t.is_translatable:
            flags.append("traduzível")
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {t.language_code:12} {t.language}{suffix}")


def fetch_transcript(video_id: str, languages: list[str]) -> tuple[list[dict], str]:
    transcript_list = _transcript_list(video_id)

    try:
        transcript = transcript_list.find_transcript(languages)
    except NoTranscriptFound:
        try:
            transcript = next(iter(transcript_list))
        except StopIteration:
            raise TranscriptError(f"nenhuma transcrição disponível para {video_id}")

    fetched = transcript.fetch()
    return fetched.to_raw_data(), fetched.language_code


def clean_annotations(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        text = re.sub(r"\s+", " ", ANNOTATION_RE.sub("", item.get("text", ""))).strip()
        result.append({**item, "text": text})
    return result


def srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def format_txt(items: list[dict], timestamps: bool = False) -> str:
    lines = []
    for item in items:
        text = item.get("text", "").replace("\n", " ").strip()
        if not text:
            continue
        if timestamps:
            t = srt_timestamp(float(item.get("start", 0))).replace(",", ".")
            lines.append(f"[{t}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines) + "\n"


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


def render(items: list[dict], output_format: str, timestamps: bool = False) -> str:
    if output_format == "json":
        return json.dumps(items, ensure_ascii=False, indent=2) + "\n"
    if output_format == "srt":
        return format_srt(items)
    return format_txt(items, timestamps=timestamps)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa a transcrição de um ou mais vídeos do YouTube.",
    )
    parser.add_argument("urls", nargs="+", metavar="url", help="URL do YouTube ou ID do vídeo")
    parser.add_argument(
        "-l", "--language",
        dest="languages",
        action="append",
        metavar="LANG",
        help="Idioma preferido (ex: pt-BR, en). Repetível em ordem de prioridade.",
    )
    parser.add_argument(
        "-f", "--format",
        choices=("txt", "json", "srt"),
        default="txt",
        help="Formato de saída (padrão: txt).",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        metavar="FILE",
        help="Arquivo de saída — só válido com uma única URL.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Escreve para stdout em vez de arquivo.",
    )
    parser.add_argument(
        "--no-title",
        action="store_true",
        help="Usa o ID do vídeo no nome do arquivo em vez do título.",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="Lista os idiomas de transcrição disponíveis e sai.",
    )
    parser.add_argument(
        "--strip-annotations",
        action="store_true",
        help="Remove anotações automáticas do tipo [Música] e [Aplausos].",
    )
    parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Inclui marcação de tempo em cada linha (somente formato txt).",
    )
    return parser.parse_args(argv)


def process_video(video_id: str, args: argparse.Namespace) -> None:
    if args.list_languages:
        list_languages(video_id)
        return

    languages = args.languages or list(DEFAULT_LANGUAGES)

    print(f"[{video_id}] Buscando transcrição...", file=sys.stderr)
    items, language = fetch_transcript(video_id, languages)

    if args.strip_annotations:
        items = clean_annotations(items)

    content = render(items, args.format, timestamps=args.timestamps)

    if args.stdout:
        sys.stdout.write(content)
        return

    if args.output is not None:
        output_path = args.output
    elif args.no_title:
        output_path = Path(f"transcript_{video_id}.{args.format}")
    else:
        try:
            title = slugify(fetch_video_title(video_id))
            print(f"[{video_id}] Título: {title}", file=sys.stderr)
        except Exception:
            title = f"transcript_{video_id}"
        output_path = Path(f"{title}.{args.format}")

    output_path.write_text(content, encoding="utf-8")
    print(f"[{video_id}] Salvo em {output_path} (idioma={language}).", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.output and len(args.urls) > 1:
        print("Erro: -o/--output só pode ser usado com uma única URL.", file=sys.stderr)
        return 1

    errors = 0
    for url in args.urls:
        try:
            video_id = extract_video_id(url)
        except ValueError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            errors += 1
            continue

        try:
            process_video(video_id, args)
        except TranscriptError as exc:
            print(f"Erro [{video_id}]: {exc}", file=sys.stderr)
            errors += 1

    return min(errors, 1)


if __name__ == "__main__":
    raise SystemExit(main())
