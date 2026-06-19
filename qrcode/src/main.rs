use std::path::PathBuf;

use anyhow::{Context, Result, anyhow, bail};
use arboard::Clipboard;
use clap::Parser;
use image::{DynamicImage, ImageBuffer, Rgba};

#[derive(Debug, Parser)]
#[command(
    name = "qrcode",
    about = "Decodifica QR codes de uma imagem ou da area de transferencia"
)]
struct Args {
    /// Caminho da imagem a decodificar. Se omitido, usa a area de transferencia.
    image: Option<PathBuf>,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let image = match args.image {
        Some(path) => load_image_from_path(path)?,
        None => load_image_from_clipboard()?,
    };

    let decoded = decode_qr_codes(image)?;
    for text in decoded {
        println!("{text}");
    }

    Ok(())
}

fn load_image_from_path(path: PathBuf) -> Result<DynamicImage> {
    image::open(&path).with_context(|| format!("nao foi possivel abrir a imagem {:?}", path))
}

fn load_image_from_clipboard() -> Result<DynamicImage> {
    let mut clipboard =
        Clipboard::new().context("nao foi possivel acessar a area de transferencia")?;
    let image = clipboard
        .get_image()
        .context("a area de transferencia nao contem uma imagem")?;

    let buffer = ImageBuffer::<Rgba<u8>, Vec<u8>>::from_raw(
        image.width as u32,
        image.height as u32,
        image.bytes.into_owned(),
    )
    .ok_or_else(|| anyhow!("imagem da area de transferencia possui dados invalidos"))?;

    Ok(DynamicImage::ImageRgba8(buffer))
}

fn decode_qr_codes(image: DynamicImage) -> Result<Vec<String>> {
    let grayscale = image.to_luma8();
    let mut prepared = rqrr::PreparedImage::prepare(grayscale);
    let grids = prepared.detect_grids();

    if grids.is_empty() {
        bail!("nenhum QR code encontrado na imagem");
    }

    let mut decoded = Vec::new();
    let mut errors = Vec::new();

    for grid in grids {
        match grid.decode() {
            Ok((_metadata, content)) => decoded.push(content),
            Err(error) => errors.push(error.to_string()),
        }
    }

    if decoded.is_empty() {
        bail!(
            "QR code encontrado, mas nao foi possivel decodificar: {}",
            errors.join("; ")
        );
    }

    Ok(decoded)
}
