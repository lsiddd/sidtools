# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pymupdf4llm",
# ]
# ///

"""
Converte um PDF para Markdown usando pymupdf4llm (leve, sem GPU, sem modelos ML).

O OCR é aplicado automaticamente apenas nas páginas que precisam (escaneadas ou
com texto corrompido). Para PDFs nativos, a conversão é quase instantânea.

Uso:
    uv run pdf_to_md_light.py <arquivo.pdf> [saida.md] [opções]

Argumentos:
    arquivo.pdf     PDF de entrada (obrigatório)
    saida.md        Arquivo de saída (opcional; padrão: mesmo nome, extensão .md)

Opções:
    --force-ocr     Força OCR em todas as páginas (para PDFs com camada de texto
                    corrompida, e.g. texto embaralhado ou ilegível)
    --no-ocr        Desativa OCR completamente (páginas escaneadas ficam vazias)
    --images        Extrai imagens para uma pasta junto ao arquivo de saída
    --embed-images  Embute imagens no Markdown como base64 (sem arquivos externos)
    --lang LANG     Idioma para OCR, no formato tesseract, ex: por, eng+por
                    (padrão: eng; requer tesseract instalado para ter efeito)
    --pages N,M-P   Páginas a processar, ex: 0,2-5,8 (0-based, padrão: todas)

Exemplos:
    uv run pdf_to_md_light.py relatorio.pdf
    uv run pdf_to_md_light.py artigo.pdf artigo.md --images
    uv run pdf_to_md_light.py escaneado.pdf --force-ocr --lang por
    uv run pdf_to_md_light.py longo.pdf --pages 0,5-10,20
"""

import argparse
import sys
from pathlib import Path


# ── Parsing de páginas ──────────────────────────────────────────────────────

def parse_pages(raw: str) -> list[int]:
    """Converte '0,2-5,8' → [0, 2, 3, 4, 5, 8]."""
    pages: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte PDF para Markdown com pymupdf4llm.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", type=Path, help="Arquivo PDF de entrada.")
    parser.add_argument(
        "output", type=Path, nargs="?", default=None,
        help="Arquivo Markdown de saída (padrão: <pdf>.md).",
    )
    ocr = parser.add_mutually_exclusive_group()
    ocr.add_argument(
        "--force-ocr", action="store_true",
        help="Força OCR em todas as páginas.",
    )
    ocr.add_argument(
        "--no-ocr", action="store_true",
        help="Desativa OCR completamente.",
    )
    img = parser.add_mutually_exclusive_group()
    img.add_argument(
        "--images", action="store_true",
        help="Extrai imagens para pasta ao lado do .md.",
    )
    img.add_argument(
        "--embed-images", action="store_true",
        help="Embute imagens como base64 no Markdown.",
    )
    parser.add_argument(
        "--lang", default="eng", metavar="LANG",
        help="Idioma OCR no formato tesseract (padrão: eng).",
    )
    parser.add_argument(
        "--pages", default=None, metavar="N,M-P",
        help="Páginas a processar (0-based), ex: 0,2-5,8.",
    )
    return parser.parse_args()


# ── Conversão ────────────────────────────────────────────────────────────────

def convert(args: argparse.Namespace) -> None:
    try:
        import pymupdf4llm
    except ImportError as exc:
        print(
            f"[erro] Falha ao importar pymupdf4llm: {exc}\n"
            "Verifique se o pacote está instalado.",
            file=sys.stderr,
        )
        sys.exit(1)

    pdf: Path = args.pdf
    output: Path = args.output if args.output else pdf.with_suffix(".md")
    output.parent.mkdir(parents=True, exist_ok=True)

    # Opções de OCR
    use_ocr: bool = not args.no_ocr
    force_ocr: bool = args.force_ocr

    # Páginas
    pages: list[int] | None = parse_pages(args.pages) if args.pages else None

    # Imagens
    write_images: bool = args.images
    embed_images: bool = args.embed_images
    image_path: str | None = None
    if write_images:
        image_path = str(output.parent / (output.stem + "_images"))
        Path(image_path).mkdir(parents=True, exist_ok=True)

    ocr_mode = (
        "forçado" if force_ocr
        else "desativado" if not use_ocr
        else "automático (apenas onde necessário)"
    )
    print(f"[info] PDF     : {pdf}")
    print(f"[info] Saída   : {output}")
    print(f"[info] OCR     : {ocr_mode}")
    if pages:
        print(f"[info] Páginas : {pages}")
    print("[info] Convertendo…")

    kwargs: dict = dict(
        use_ocr=use_ocr,
        force_ocr=force_ocr,
        ocr_language=args.lang,
        write_images=write_images,
        embed_images=embed_images,
    )
    if image_path:
        kwargs["image_path"] = image_path
        kwargs["image_format"] = "png"
    if pages is not None:
        kwargs["pages"] = pages

    md_text: str = pymupdf4llm.to_markdown(str(pdf), **kwargs)

    output.write_bytes(md_text.encode("utf-8"))

    size_kb = output.stat().st_size / 1024
    print(f"[ok]   Markdown salvo em: {output} ({size_kb:.1f} KB)")
    if image_path and Path(image_path).exists():
        n_imgs = len(list(Path(image_path).iterdir()))
        if n_imgs:
            print(f"[ok]   {n_imgs} imagem(ns) salvas em: {image_path}/")


# ── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if not args.pdf.exists():
        print(f"[erro] Arquivo não encontrado: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    if args.pdf.suffix.lower() != ".pdf":
        print(
            f"[aviso] Extensão '{args.pdf.suffix}' não é .pdf — continuando mesmo assim.",
            file=sys.stderr,
        )

    convert(args)


if __name__ == "__main__":
    main()
