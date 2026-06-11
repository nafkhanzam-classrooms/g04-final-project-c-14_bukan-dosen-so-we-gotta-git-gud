import asyncio
import os


async def process_pdf(room_code: str, pdf_filepath: str, volume_dir: str) -> None:
    # Handles the final PDF -> WebP extraction
    output_dir = os.path.join(volume_dir, room_code)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Extracting PDF to WebP for room {room_code}...")
    pdftoppm_proc = await asyncio.create_subprocess_exec(
        "pdftoppm",
        "-webp",
        pdf_filepath,
        f"{output_dir}/slide",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await pdftoppm_proc.communicate()
    print(f"Extraction complete for {room_code}.")


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
    await libreoffice_proc.communicate()

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
