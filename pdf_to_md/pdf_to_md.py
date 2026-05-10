# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "marker-pdf",
# ]
# ///

"""
Converte um PDF para Markdown usando marker-pdf.

Uso:
    uv run pdf_to_md.py <arquivo.pdf> [saida.md]

Argumentos:
    arquivo.pdf   Caminho para o PDF de entrada (obrigatório)
    saida.md      Caminho para o arquivo Markdown gerado (opcional)
                  Padrão: mesmo nome do PDF, extensão .md

Flags opcionais:
    --force-ocr   Força OCR em todas as páginas (útil para PDFs escaneados
                  ou com texto corrompido)
    --debug       Salva imagens de layout e JSON com bounding boxes para depuração

Exemplos:
    uv run pdf_to_md.py relatorio.pdf
    uv run pdf_to_md.py relatorio.pdf saida/relatorio.md
    uv run pdf_to_md.py artigo.pdf --force-ocr
"""

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte PDF para Markdown usando marker-pdf.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "pdf",
        type=Path,
        help="Caminho para o arquivo PDF de entrada.",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="Caminho para o arquivo Markdown de saída (padrão: mesmo nome do PDF).",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Força OCR em todo o documento (recomendado para PDFs escaneados).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa modo debug: salva imagens de layout e JSON auxiliar.",
    )
    return parser.parse_args()


def resolve_output(pdf: Path, output: Path | None) -> Path:
    if output is not None:
        return output
    return pdf.with_suffix(".md")


def convert(pdf: Path, output: Path, force_ocr: bool, debug: bool) -> None:
    # Importações pesadas ficam aqui para que erros de dependência
    # apareçam com mensagem amigável, após a validação dos argumentos.
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered
    except ImportError as exc:
        print(
            f"[erro] Falha ao importar marker-pdf: {exc}\n"
            "Verifique se o pacote está instalado corretamente.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[info] Carregando modelos marker-pdf…")
    model_dict = create_model_dict()

    converter_kwargs: dict = {"artifact_dict": model_dict}
    if force_ocr:
        converter_kwargs["config"] = {"force_ocr": True}
    if debug:
        converter_kwargs.setdefault("config", {})["debug_pdf_images"] = True

    print(f"[info] Convertendo: {pdf}")
    converter = PdfConverter(**converter_kwargs)
    rendered = converter(str(pdf))

    markdown_text, _, metadata = text_from_rendered(rendered)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_text, encoding="utf-8")

    pages = metadata.get("pages", "?")
    print(f"[ok]   Markdown salvo em: {output}  ({pages} página(s))")


def main() -> None:
    args = parse_args()

    if not args.pdf.exists():
        print(f"[erro] Arquivo não encontrado: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    if args.pdf.suffix.lower() != ".pdf":
        print(
            f"[aviso] A extensão '{args.pdf.suffix}' não é .pdf — continuando mesmo assim.",
            file=sys.stderr,
        )

    output = resolve_output(args.pdf, args.output)

    convert(
        pdf=args.pdf,
        output=output,
        force_ocr=args.force_ocr,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
