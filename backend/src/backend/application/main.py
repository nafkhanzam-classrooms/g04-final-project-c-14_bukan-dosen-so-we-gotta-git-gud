import asyncio

import websockets


async def echo(websocket: websockets.ServerConnection) -> None:
    print("Client connected")
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                message = message.decode("utf-8")

            print(f"Received message: {message}")
            await websocket.send(f"{message}")
    except websockets.ConnectionClosed:
        print("Client terputus")


async def main() -> None:
    async with websockets.serve(echo, "", 6767) as server:
        print("WebSocket server started on ws://localhost:6767")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
