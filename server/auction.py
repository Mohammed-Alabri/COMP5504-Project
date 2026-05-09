import asyncio
import json
import logging

from protocol import build_update, build_closed

logger = logging.getLogger(__name__)


class Auction:
    def __init__(self, auction_id: int, item_name: str, start_price: float,
                 duration_seconds: int):
        self.auction_id      = auction_id
        self.item_name       = item_name
        self.highest_bid     = start_price
        self.highest_bidder  = None
        self.duration        = duration_seconds
        self.time_left       = duration_seconds
        self.status          = "active"
        self.subscribers     = set()
        self.lock            = asyncio.Lock()

    def to_dict(self) -> dict:
        return {
            "auction_id":      self.auction_id,
            "item_name":       self.item_name,
            "highest_bid":     self.highest_bid,
            "highest_bidder":  self.highest_bidder,
            "time_left":       self.time_left,
            "duration":        self.duration,
            "status":          self.status,
        }

    async def broadcast(self, message: dict) -> None:
        import websockets.exceptions
        data = json.dumps(message)
        dead = set()
        for ws in set(self.subscribers):
            try:
                await ws.send(data)
            except websockets.exceptions.ConnectionClosed:
                dead.add(ws)
            except Exception as e:
                logger.warning("Error sending to subscriber: %s", e)
                dead.add(ws)
        self.subscribers -= dead

    async def broadcast_update(self) -> None:
        await self.broadcast(build_update(
            self.auction_id, self.item_name,
            self.highest_bid, self.highest_bidder, self.time_left,
        ))

    async def close_auction(self) -> None:
        if self.status == "closed":
            return
        self.status = "closed"
        winner      = self.highest_bidder
        final_price = self.highest_bid
        await self.broadcast(build_closed(
            self.auction_id, self.item_name, winner, final_price,
        ))
        logger.info(
            "Auction #%d '%s' closed — winner: %s @ %.2f",
            self.auction_id, self.item_name, winner, final_price,
        )

    async def run_timer(self) -> None:
        while self.time_left > 0 and self.status == "active":
            await asyncio.sleep(1)
            async with self.lock:
                if self.status != "active":
                    break
                self.time_left -= 1
                if self.time_left <= 0:
                    await self.close_auction()
                    break
                await self.broadcast_update()
