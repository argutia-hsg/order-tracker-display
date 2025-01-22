import asyncio
import websockets
from aiohttp import web
import argparse
import logging

logger = logging.getLogger()

__running = True
__connected_ws_clients = []
__webroot = './web'


# WebSocket server handler
async def websocket_handler(websocket):
    global __connected_ws_clients
    __connected_ws_clients.append(websocket)

    async for message in websocket:
        logger.debug(f"Received message: {message}")
    
    __connected_ws_clients.remove(websocket)


# WebSocket server setup
async def start_websocket_server():
    server = await websockets.serve(websocket_handler, "localhost", 8081)
    logger.info("WebSocket server started on ws://localhost:8081")
    await server.wait_closed()


async def web_update_handler(request):
    json = await request.text()

    for websocket in __connected_ws_clients:
        await websocket.send(json)
    
    return web.Response(status=204)


# HTTP file server setup
async def start_http_server():
    app = web.Application()

    app.router.add_static('/', __webroot)
    app.router.add_post('/update', web_update_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "localhost", 8080)
    logger.info("HTTP server started on http://localhost:8080")
    await site.start()


async def start_chromium_browser():
    while __running:
        process = await asyncio.create_subprocess_shell(
            "chromium http://localhost:8080/index.html --start-fullscreen --kiosk --incognito --noerrdialogs --no-first-run --disk-cache-dir=/dev/null --autoplay-policy=no-user-gesture-required",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        logger.info("Chromium started in kiosk mode on http://localhost:8080/index.html")
        await process.communicate()


# Main async entry point
async def main():
    # Run both servers concurrently
    futures = asyncio.gather(
        start_websocket_server(),
        start_http_server(),
        start_chromium_browser()
    )

    logger.info("""

    The server is up and running. Remeber to proxy http://localhost:8080/update
    so that this display can be updated.
    """)

    await futures


# Start everything
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="order-tracker display",
        description="Simple order tracking screen like at McDonald's",
        epilog="Made by Christian Schliz")

    parser.add_argument('-r', '--root', default='./web', help="path to the html files (Default: './web')")
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    __webroot = args.root

    asyncio.run(main())
