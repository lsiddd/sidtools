# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "marker-pdf",
# ]
# ///

"""
Converte um PDF (ou todos os PDFs de uma pasta) para Markdown usando marker-pdf.

Uso:
    uv run pdf_to_md.py <arquivo.pdf|pasta> [saida]

Argumentos:
    arquivo.pdf|pasta   Caminho para o PDF de entrada ou para uma pasta
                        contendo PDFs (obrigatório)
    saida               Caminho de saída (opcional)
                        - Se a entrada for um arquivo: caminho do .md gerado
                          (padrão: mesmo nome do PDF, extensão .md)
                        - Se a entrada for uma pasta: pasta onde os .md
                          gerados serão salvos (padrão: mesma pasta de entrada)

Flags opcionais:
    --force-ocr   Força OCR em todas as páginas (útil para PDFs escaneados
                  ou com texto corrompido)
    --debug       Salva imagens de layout e JSON com bounding boxes para depuração

Exemplos:
    uv run pdf_to_md.py relatorio.pdf
    uv run pdf_to_md.py relatorio.pdf saida/relatorio.md
    uv run pdf_to_md.py artigo.pdf --force-ocr
    uv run pdf_to_md.py pasta_com_pdfs/
    uv run pdf_to_md.py pasta_com_pdfs/ pasta_de_saida/
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
        help="Caminho para o arquivo PDF de entrada ou para uma pasta com PDFs.",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Caminho de saída: arquivo .md (entrada = arquivo) ou pasta de "
            "destino (entrada = pasta). Padrão: ao lado da entrada."
        ),
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


def build_converter(force_ocr: bool, debug: bool):
    # Importações pesadas ficam aqui para que erros de dependência
    # apareçam com mensagem amigável, após a validação dos argumentos.
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
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

    return PdfConverter(**converter_kwargs)


def convert(converter, pdf: Path, output: Path) -> None:
    from marker.output import text_from_rendered

    print(f"[info] Convertendo: {pdf}")
    rendered = converter(str(pdf))

    markdown_text, _, metadata = text_from_rendered(rendered)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_text, encoding="utf-8")

    pages = metadata.get("pages", "?")
    print(f"[ok]   Markdown salvo em: {output}  ({pages} página(s))")


def convert_directory(pdf_dir: Path, output_dir: Path | None, force_ocr: bool, debug: bool) -> None:
    pdfs = sorted(p for p in pdf_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"[erro] Nenhum PDF encontrado em: {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[info] {len(pdfs)} PDF(s) encontrado(s) em: {pdf_dir}")
    converter = build_converter(force_ocr=force_ocr, debug=debug)

    for pdf in pdfs:
        if output_dir is not None:
            output = output_dir / pdf.with_suffix(".md").name
        else:
            output = pdf.with_suffix(".md")
        convert(converter=converter, pdf=pdf, output=output)


def main() -> None:
    args = parse_args()

    if not args.pdf.exists():
        print(f"[erro] Caminho não encontrado: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    if args.pdf.is_dir():
        if args.output is not None and args.output.suffix:
            print(
                f"[erro] A entrada é uma pasta; informe uma pasta de saída, não um arquivo: {args.output}",
                file=sys.stderr,
            )
            sys.exit(1)
        convert_directory(
            pdf_dir=args.pdf,
            output_dir=args.output,
            force_ocr=args.force_ocr,
            debug=args.debug,
        )
        return

    if args.pdf.suffix.lower() != ".pdf":
        print(
            f"[aviso] A extensão '{args.pdf.suffix}' não é .pdf — continuando mesmo assim.",
            file=sys.stderr,
        )

    output = resolve_output(args.pdf, args.output)
    converter = build_converter(force_ocr=args.force_ocr, debug=args.debug)
    convert(converter=converter, pdf=args.pdf, output=output)


if __name__ == "__main__":
    main()
