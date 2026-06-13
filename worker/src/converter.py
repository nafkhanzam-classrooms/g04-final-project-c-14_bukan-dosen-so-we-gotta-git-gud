import logging
import asyncio
import os
import glob

logger = logging.getLogger(__name__)

async def convert_single_image(jpg_path: str, webp_path: str) -> None:
    """Helper to convert a single JPEG to WebP concurrently and clean up."""
    logger.info(f"Converting {jpg_path} -> {webp_path}")
    cwebp_proc = await asyncio.create_subprocess_exec(
        "cwebp",
        "-q", "80",
        "-m", "4",     
        "-mt",         
        jpg_path,
        "-o", webp_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await cwebp_proc.communicate()
    if cwebp_proc.returncode != 0:
        logger.error(f"cwebp failed for {jpg_path}: {stderr.decode()}")
        raise RuntimeError(f"cwebp failed: {stderr.decode()}")
    
    # Remove the intermediate JPEG file immediately
    os.remove(jpg_path)

async def process_pdf(room_code: str, pdf_filepath: str, volume_dir: str) -> None:
    output_dir = os.path.join(volume_dir, room_code)
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Convert PDF to JPEG slides
    logger.info(f"Extracting PDF to JPEG for room {room_code}...")
    pdftoppm_proc = await asyncio.create_subprocess_exec(
        "pdftoppm",
        "-jpeg",  
        "-r", "150",
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

    # Step 2: Gather files and process conversions concurrently
    jpg_files = sorted(glob.glob(os.path.join(output_dir, "slide-*.jpg")))
    if not jpg_files:
        raise RuntimeError(f"No JPEG slides generated for room {room_code}")

    # Create coroutines for concurrent execution instead of a blocking for-loop
    tasks = []
    for jpg_path in jpg_files:
        webp_path = jpg_path.rsplit(".", 1)[0] + ".webp"
        tasks.append(convert_single_image(jpg_path, webp_path))
    
    # Run all cwebp transformations in parallel
    await asyncio.gather(*tasks)
    logger.info(f"WebP conversion complete for {room_code}.")


async def process_pptx(room_code: str, pptx_filepath: str, volume_dir: str) -> None:
    output_dir = os.path.join(volume_dir, room_code)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Converting PPTX to PDF for room {room_code}...")
    
    # Setting an explicit temporary UserInstallation prevents LibreOffice lock failures
    libreoffice_proc = await asyncio.create_subprocess_exec(
        "libreoffice",
        "-env:UserInstallation=file:///tmp/libo_user", 
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to", "pdf",
        pptx_filepath,
        "--outdir", output_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await libreoffice_proc.communicate()
    if libreoffice_proc.returncode != 0:
        logger.error(f"LibreOffice failed for {room_code}: {stderr.decode()}")
        raise RuntimeError("LibreOffice conversion failed")

    original_filename = os.path.basename(pptx_filepath)
    pdf_filename = original_filename.replace(".pptx", ".pdf")
    generated_pdf_path = os.path.join(output_dir, pdf_filename)

    if os.path.exists(generated_pdf_path):
        await process_pdf(room_code, generated_pdf_path, volume_dir)
        os.remove(generated_pdf_path)
    else:
        print(f"Error: LibreOffice failed to generate PDF for {room_code}")
