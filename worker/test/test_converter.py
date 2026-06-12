import pytest
import os
from unittest.mock import patch, AsyncMock
from src.converter import process_pdf, process_pptx


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("glob.glob")
@patch("os.remove")
async def test_process_pdf_converts_to_webp(
    mock_remove, mock_glob, mock_exec, tmp_path
):
    # Setup: first call is pdftoppm (success), subsequent calls are cwebp (success)
    mock_proc_pdftoppm = AsyncMock()
    mock_proc_pdftoppm.communicate.return_value = (b"", b"")
    mock_proc_pdftoppm.returncode = 0

    mock_proc_cwebp = AsyncMock()
    mock_proc_cwebp.communicate.return_value = (b"", b"")
    mock_proc_cwebp.returncode = 0

    # mock_exec.side_effect: first pdftoppm, then cwebp for each PNG
    mock_exec.side_effect = [mock_proc_pdftoppm, mock_proc_cwebp]

    mock_glob.return_value = [os.path.join(tmp_path, "room", "slide-01.png")]

    volume_dir = str(tmp_path)
    await process_pdf("room", "/fake.pdf", volume_dir)

    # Verify pdftoppm call with -png
    assert mock_exec.call_args_list[0][0][1] == "-png"
    assert "cwebp" in mock_exec.call_args_list[1][0]
    mock_remove.assert_called_once()


@pytest.mark.asyncio
@patch("src.converter.process_pdf")
@patch("asyncio.create_subprocess_exec")
@patch("os.path.exists")
@patch("os.remove")
async def test_process_pptx_chains_to_pdf(
    mock_remove, mock_exists, mock_exec, mock_process_pdf, tmp_path
):
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
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
