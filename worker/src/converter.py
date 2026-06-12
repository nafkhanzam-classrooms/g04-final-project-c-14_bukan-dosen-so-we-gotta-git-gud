import logging
import asyncio
import os
import glob

logger = logging.getLogger(__name__)


async def process_pdf(room_code: str, pdf_filepath: str, volume_dir: str) -> None:
    output_dir = os.path.join(volume_dir, room_code)
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Convert PDF to PNG slides
    logger.info(f"Extracting PDF to PNG for room {room_code}...")
    pdftoppm_proc = await asyncio.create_subprocess_exec(
        "pdftoppm",
        "-png",
        "-r",
        "150",
        pdf_filepath,
        os.path.join(output_dir, "slide"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await pdftoppm_proc.communicate()
    if pdftoppm_proc.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error(f"pdftoppm failed for {room_code}: {error_msg}")
        raise RuntimeError(f"pdftoppm failed: {error_msg}")

    # Step 2: Convert each PNG to WebP and remove original PNG
    png_files = sorted(glob.glob(os.path.join(output_dir, "slide-*.png")))
    if not png_files:
        raise RuntimeError(f"No PNG slides generated for room {room_code}")

    for png_path in png_files:
        webp_path = png_path.rsplit(".", 1)[0] + ".webp"
        logger.info(f"Converting {png_path} -> {webp_path}")
        cwebp_proc = await asyncio.create_subprocess_exec(
            "cwebp",
            "-q",
            "80",
            png_path,
            "-o",
            webp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await cwebp_proc.communicate()
        if cwebp_proc.returncode != 0:
            logger.error(f"cwebp failed for {png_path}: {stderr.decode()}")
            raise RuntimeError(f"cwebp failed: {stderr.decode()}")
        os.remove(png_path)

    logger.info(f"WebP conversion complete for {room_code}.")


async def process_pptx(room_code: str, pptx_filepath: str, volume_dir: str) -> None:
    # Handles PPTX -> PDF, then calls the PDF processor
    output_dir = os.path.join(volume_dir, room_code)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Converting PPTX to PDF for room {room_code}...")
    libreoffice_proc = await asyncio.create_subprocess_exec(
        "libreoffice",
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to",
        "pdf",
        pptx_filepath,
        "--outdir",
        output_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await libreoffice_proc.communicate()
    if libreoffice_proc.returncode != 0:
        logger.error(f"LibreOffice failed for {room_code}: {stderr.decode()}")
        raise RuntimeError("LibreOffice conversion failed")

    # Determine where LibreOffice saved the PDF
    original_filename = os.path.basename(pptx_filepath)
    pdf_filename = original_filename.replace(".pptx", ".pdf")
    generated_pdf_path = os.path.join(output_dir, pdf_filename)

    if os.path.exists(generated_pdf_path):
        await process_pdf(
            room_code, generated_pdf_path, volume_dir
        )  # Chain into the PDF processing function
        os.remove(generated_pdf_path)
    else:
        print(f"Error: LibreOffice failed to generate PDF for {room_code}")
