import pytest
from unittest.mock import patch, mock_open
from src.main import handle_http_request


class MockStreamReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    async def readline(self):
        if self._pos >= len(self._data):
            return b""
        idx = self._data.find(b"\n", self._pos)
        if idx == -1:
            res = self._data[self._pos :]
            self._pos = len(self._data)
            return res
        res = self._data[self._pos : idx + 1]
        self._pos = idx + 1
        return res

    async def readexactly(self, n):
        res = self._data[self._pos : self._pos + n]
        self._pos += n
        return res


class MockStreamWriter:
    def __init__(self):
        self.written_data = b""
        self.is_closed = False

    def write(self, data):
        self.written_data += data

    async def drain(self):
        pass

    def close(self):
        self.is_closed = True

    async def wait_closed(self):
        pass


@pytest.mark.asyncio
@patch("src.publisher.publish_slides_ready")
@patch("os.listdir", return_value=["slide-01.webp"])
@patch("src.main.process_pdf")
@patch("builtins.open", new_callable=mock_open)
@patch("os.remove")
async def test_handle_valid_pdf_upload(
    mock_remove, mock_file, mock_process_pdf, mock_listdir, mock_publish
):
    mock_process_pdf.return_value = None

    body = b"%PDF-1.4 mock binary data"
    request = (
        b"POST /upload/ROOM123/pdf HTTP/1.1\r\n"
        b"Host: localhost:8080\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"\r\n" + body
    )

    reader = MockStreamReader(request)
    writer = MockStreamWriter()

    await handle_http_request(reader, writer)

    mock_process_pdf.assert_called_once()
    assert mock_process_pdf.call_args[0][0] == "ROOM123"

    assert b"200 OK" in writer.written_data
    assert b"Conversion Successful" in writer.written_data


@pytest.mark.asyncio
async def test_handle_invalid_method():
    request = b"GET /upload/ROOM123/pdf HTTP/1.1\r\n\r\n"
    reader = MockStreamReader(request)
    writer = MockStreamWriter()

    await handle_http_request(reader, writer)

    assert b"405 Method Not Allowed" in writer.written_data


@pytest.mark.asyncio
async def test_handle_invalid_file_type():
    request = (
        b"POST /upload/ROOM123/docx HTTP/1.1\r\nContent-Length: 10\r\n\r\ndummy data"
    )
    reader = MockStreamReader(request)
    writer = MockStreamWriter()

    await handle_http_request(reader, writer)

    assert b"400 Bad Request" in writer.written_data
    assert b"Unsupported file type" in writer.written_data
