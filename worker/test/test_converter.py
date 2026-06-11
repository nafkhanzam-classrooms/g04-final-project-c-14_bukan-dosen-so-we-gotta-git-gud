import pytest
import os
from unittest.mock import patch, AsyncMock, ANY
from src.converter import process_pdf, process_pptx


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_process_pdf_calls_pdftoppm(mock_exec, tmp_path):
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"stdout", b"stderr")
    mock_exec.return_value = mock_proc

    room_code = "XYZ123"
    pdf_filepath = "/dummy/path/file.pdf"
    volume_dir = str(tmp_path)

    await process_pdf(room_code, pdf_filepath, volume_dir)

    mock_exec.assert_called_once_with(
        "pdftoppm",
        "-webp",
        pdf_filepath,
        f"{volume_dir}/{room_code}/slide",
        stdout=ANY,
        stderr=ANY,
    )
    assert os.path.exists(os.path.join(volume_dir, room_code))


@pytest.mark.asyncio
@patch("src.converter.process_pdf")
@patch("asyncio.create_subprocess_exec")
@patch("os.path.exists")
@patch("os.remove")
async def test_process_pptx_chains_to_pdf(
    mock_remove, mock_exists, mock_exec, mock_process_pdf, tmp_path
):
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"stdout", b"stderr")
    mock_exec.return_value = mock_proc

    # Simulate that PDF is successfully created
    mock_exists.return_value = True

    room_code = "XYZ123"
    pptx_filepath = "/dummy/path/presentation.pptx"
    volume_dir = str(tmp_path)

    await process_pptx(room_code, pptx_filepath, volume_dir)

    # Verify that LibreOffice is called
    mock_exec.assert_called_once()
    assert "libreoffice" in mock_exec.call_args[0]

    mock_process_pdf.assert_called_once()
    mock_remove.assert_called_once()
