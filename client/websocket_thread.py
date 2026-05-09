import asyncio
import json

import websockets
import websockets.exceptions
from PyQt6.QtCore import QThread, pyqtSignal


class WebSocketThread(QThread):
    message_received  = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self, url: str):
        super().__init__()
        self.url         = url
        self._loop       = None
        self._send_queue = None

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        finally:
            self._loop.close()
            self._loop = None

    async def _connect(self) -> None:
        self._send_queue = asyncio.Queue()
        try:
            async with websockets.connect(self.url) as ws:
                self.connection_status.emit(True)
                await asyncio.gather(
                    self._receive_loop(ws),
                    self._send_loop(ws),
                )
        except Exception:
            pass
        finally:
            self.connection_status.emit(False)

    async def _receive_loop(self, ws) -> None:
        try:
            async for raw in ws:
                try:
                    self.message_received.emit(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _send_loop(self, ws) -> None:
        while True:
            msg = await self._send_queue.get()
            if msg is None:
                await ws.close()
                break
            try:
                await ws.send(json.dumps(msg))
            except websockets.exceptions.ConnectionClosed:
                break

    def send_message(self, data: dict) -> None:
        """Thread-safe bridge from Qt main thread into the asyncio send queue."""
        if self._loop and self._send_queue:
            self._loop.call_soon_threadsafe(self._send_queue.put_nowait, data)

    def stop(self) -> None:
        if self._loop and self._send_queue:
            self._loop.call_soon_threadsafe(self._send_queue.put_nowait, None)
        self.wait()
