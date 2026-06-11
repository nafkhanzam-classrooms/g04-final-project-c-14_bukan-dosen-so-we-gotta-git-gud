import logging
import asyncio
import os
from .converter import process_pptx, process_pdf

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

VOLUME_DIR = "/app/public/slides"


async def handle_http_request(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    try:
        request_line = await reader.readline()
        if not request_line:
            return

        req_parts = request_line.decode().strip().split(" ")
        if len(req_parts) < 2 or req_parts[0] != "POST":
            await send_http_response(writer, 405, "Method Not Allowed")
            return

        # Expecting: /upload/XYZ123/pptx OR /upload/XYZ123/pdf
        path_parts = req_parts[1].strip("/").split("/")
        if len(path_parts) != 3 or path_parts[0] != "upload":
            await send_http_response(writer, 400, "Bad Request: Invalid URL format")
            return

        room_code = path_parts[1]
        file_type = path_parts[2].lower()  # 'pptx' or 'pdf'

        if file_type not in ["pptx", "pdf"]:
            await send_http_response(writer, 400, "Bad Request: Unsupported file type")
            return

        # Read HTTP Header
        headers = {}
        while True:
            line = await reader.readline()
            if line == b"\r\n":  # end of headers
                break
            header_str = line.decode().strip()
            if ":" in header_str:
                key, value = header_str.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        # Payload
        content_length = int(headers.get("content-length", 0))
        if content_length == 0:
            await send_http_response(writer, 400, "Bad Request: No Content-Length")
            return

        logger.info(f"Received file for room {room_code}, size: {content_length} bytes")

        # Read binary
        file_body = await reader.readexactly(content_length)
        temp_filepath = f"/tmp/{room_code}.{file_type}"

        with open(temp_filepath, "wb") as f:
            f.write(file_body)

        if file_type == "pptx":
            await process_pptx(room_code, temp_filepath, VOLUME_DIR)
        elif file_type == "pdf":
            await process_pdf(room_code, temp_filepath, VOLUME_DIR)

        os.remove(temp_filepath)

        from src.publisher import publish_slides_ready

        # Publish to redis
        output_dir = os.path.join(VOLUME_DIR, room_code)
        await publish_slides_ready(room_code, output_dir)
        await send_http_response(writer, 200, "Konversi Berhasil")

    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        await send_http_response(writer, 500, f"Internal Server Error: {str(e)}")
    finally:
        writer.close()
        await writer.wait_closed()


async def send_http_response(writer, status_code: int, message: str):
    # Simple HTTP response helper
    status_text = {
        200: "OK",
        400: "Bad Request",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }
    response_body = message.encode()

    response = (
        f"HTTP/1.1 {status_code} {status_text.get(status_code, '')}\r\n"
        f"Content-Type: text/plain\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + response_body

    writer.write(response)
    await writer.drain()


async def main():
    os.makedirs(VOLUME_DIR, exist_ok=True)
    server = await asyncio.start_server(handle_http_request, "0.0.0.0", 8080)
    logger.info("Worker HTTP Server running on http://0.0.0.0:8080")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
