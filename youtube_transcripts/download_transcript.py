#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "youtube-transcript-api",
#   "yt-dlp",
# ]
# ///
"""Download transcripts from YouTube videos or channels."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi


DEFAULT_LANGUAGES = ("pt-BR", "pt", "en")
ANNOTATION_RE = re.compile(r"\[.*?\]|\(.*?\)")


class TranscriptError(Exception):
    pass


class ChannelError(Exception):
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


def channel_videos_url(channel: str) -> str:
    value = channel.strip().rstrip("/")
    if value.startswith("@"):
        return f"https://www.youtube.com/{value}/videos"

    parsed = urlparse(value)
    if not parsed.scheme:
        raise ValueError(
            "canal deve ser uma URL do YouTube ou um @handle "
            f"(recebido: {channel!r})"
        )
    if "youtube.com" not in parsed.netloc.lower():
        raise ValueError(f"URL de canal inválida: {channel!r}")

    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        raise ValueError(f"URL de canal inválida: {channel!r}")
    if path_parts[-1] in {"featured", "shorts", "streams", "playlists", "community"}:
        path_parts.pop()
    if not path_parts or path_parts[-1] != "videos":
        path_parts.append("videos")
    return f"https://www.youtube.com/{'/'.join(path_parts)}"


def fetch_channel_video_ids(channel: str, limit: int | None) -> list[str]:
    try:
        url = channel_videos_url(channel)
    except ValueError as exc:
        raise ChannelError(str(exc)) from exc

    options = {
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
    }
    if limit is not None:
        options["playlistend"] = limit

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise ChannelError(f"erro ao listar vídeos do canal: {exc}") from exc

    entries = info.get("entries", []) if info else []
    video_ids = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        if isinstance(video_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            video_ids.append(video_id)

    if not video_ids:
        raise ChannelError("nenhum vídeo encontrado no canal")
    return video_ids


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
    parser.add_argument("urls", nargs="*", metavar="url", help="URL do YouTube ou ID do vídeo")
    parser.add_argument(
        "--channel",
        metavar="CHANNEL",
        help="URL ou @handle de um canal do YouTube.",
    )
    channel_amount = parser.add_mutually_exclusive_group()
    channel_amount.add_argument(
        "--latest",
        type=int,
        metavar="N",
        help="Baixa as transcrições dos N vídeos mais recentes do canal.",
    )
    channel_amount.add_argument(
        "--all",
        action="store_true",
        help="Baixa as transcrições de todos os vídeos do canal.",
    )
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
    args = parser.parse_args(argv)

    if args.channel and args.urls:
        parser.error("--channel não pode ser usado junto com URLs de vídeos")
    if args.channel and args.latest is None and not args.all:
        parser.error("--channel exige --latest N ou --all")
    if not args.channel and (args.latest is not None or args.all):
        parser.error("--latest e --all só podem ser usados com --channel")
    if not args.channel and not args.urls:
        parser.error("informe ao menos uma URL/ID de vídeo ou use --channel")
    if args.latest is not None and args.latest < 1:
        parser.error("--latest deve ser maior que zero")

    return args


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
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.channel:
        try:
            args.urls = fetch_channel_video_ids(args.channel, None if args.all else args.latest)
            print(
                f"Canal: {len(args.urls)} vídeo(s) encontrado(s).",
                file=sys.stderr,
            )
        except ChannelError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

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
