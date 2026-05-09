import asyncio
import datetime
import json
import logging
import websockets
import websockets.exceptions

from .auction import Auction
from protocol import (
    MSG_CREATE_AUCTION, MSG_JOIN, MSG_BID, MSG_LIST_AUCTIONS,
    build_error, build_rejected, build_update, build_auction_created,
    build_auction_list, parse_message,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global state (all in-memory)
connected_clients: dict = {}   # { ws: {"user": str|None, "subscribed_auctions": set()} }
active_auctions:   dict = {}   # { auction_id: Auction }
timer_tasks:       dict = {}   # { auction_id: asyncio.Task }
_next_id:          int  = 1    # auto-increment auction ID


def _ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _new_auction_id() -> int:
    global _next_id
    aid      = _next_id
    _next_id += 1
    return aid


async def send_json(websocket, data: dict) -> None:
    try:
        await websocket.send(json.dumps(data))
    except websockets.exceptions.ConnectionClosed:
        pass


async def broadcast_auction_list() -> None:
    msg = build_auction_list([a.to_dict() for a in active_auctions.values()])
    for ws in set(connected_clients):
        await send_json(ws, msg)


async def handle_list_auctions(websocket, message: dict) -> None:
    await send_json(websocket, build_auction_list(
        [a.to_dict() for a in active_auctions.values()]
    ))


async def handle_create_auction(websocket, message: dict) -> None:
    item_name   = str(message.get("item_name", "")).strip()
    start_price = message.get("start_price")
    duration    = message.get("duration")
    user        = str(message.get("user", "Anonymous")).strip()

    if not item_name:
        return await send_json(websocket, build_error("item_name is required"))
    if not isinstance(start_price, (int, float)) or isinstance(start_price, bool) or start_price < 0:
        return await send_json(websocket, build_error("start_price must be a non-negative number"))
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        return await send_json(websocket, build_error("duration must be a positive integer (seconds)"))

    auction_id = _new_auction_id()
    auction    = Auction(auction_id, item_name, float(start_price), int(duration))
    active_auctions[auction_id] = auction

    task = asyncio.create_task(auction.run_timer())
    timer_tasks[auction_id] = task

    logger.info("[%s] Auction #%d created: '%s' by %s (start=%.2f OMR, %ds)",
                _ts(), auction_id, item_name, user, start_price, duration)

    await send_json(websocket, build_auction_created(auction_id, item_name))
    await broadcast_auction_list()


async def handle_join(websocket, message: dict) -> None:
    auction_id = message.get("auction_id")
    user       = str(message.get("user", "")).strip()

    if auction_id not in active_auctions:
        return await send_json(websocket, build_error("Auction not found"))

    auction = active_auctions[auction_id]
    auction.subscribers.add(websocket)
    if websocket in connected_clients:
        connected_clients[websocket]["subscribed_auctions"].add(auction_id)
        connected_clients[websocket]["user"] = user or connected_clients[websocket].get("user")

    logger.info("[%s] %s joined auction #%d '%s'", _ts(), user, auction_id, auction.item_name)

    await send_json(websocket, build_update(
        auction.auction_id, auction.item_name,
        auction.highest_bid, auction.highest_bidder, auction.time_left,
    ))


async def handle_bid(websocket, message: dict) -> None:
    auction_id = message.get("auction_id")
    user       = str(message.get("user", "")).strip()
    amount     = message.get("amount")

    if not user:
        return await send_json(websocket, build_error("user is required"))
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
        return await send_json(websocket, build_error("Invalid bid amount"))
    if auction_id not in active_auctions:
        return await send_json(websocket, build_error("Auction not found"))

    auction = active_auctions[auction_id]

    async with auction.lock:
        if auction.status != "active":
            return await send_json(websocket, build_error("Auction is closed"))
        if amount <= auction.highest_bid:  
            return await send_json(websocket, build_rejected(auction_id, "Bid too low"))

        auction.highest_bid    = float(amount)
        auction.highest_bidder = user
        logger.info("[%s] Bid accepted: %s bid %.2f OMR on auction #%d",
                    _ts(), user, amount, auction_id)
        await auction.broadcast_update()


async def route_message(websocket, message: dict) -> None:
    msg_type = message.get("type")
    if msg_type == MSG_LIST_AUCTIONS:
        await handle_list_auctions(websocket, message)
    elif msg_type == MSG_CREATE_AUCTION:
        await handle_create_auction(websocket, message)
    elif msg_type == MSG_JOIN:
        await handle_join(websocket, message)
    elif msg_type == MSG_BID:
        await handle_bid(websocket, message)
    else:
        await send_json(websocket, build_error(f"Unknown message type: {msg_type!r}"))


async def cleanup_client(websocket) -> None:
    if websocket not in connected_clients:
        return
    client_info = connected_clients.pop(websocket)
    for auction_id in client_info.get("subscribed_auctions", set()):
        auction = active_auctions.get(auction_id)
        if auction:
            auction.subscribers.discard(websocket)
    logger.info("[%s] Client disconnected: %s", _ts(), websocket.remote_address)


async def connection_handler(websocket) -> None:
    connected_clients[websocket] = {"user": None, "subscribed_auctions": set()}
    logger.info("[%s] Client connected: %s", _ts(), websocket.remote_address)
    try:
        async for raw in websocket:
            message = parse_message(raw)
            if message is None:
                await send_json(websocket, build_error("Invalid JSON"))
                continue
            await route_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logger.error("[%s] Unexpected error in connection_handler: %s", _ts(), e)
    finally:
        await cleanup_client(websocket)


async def main() -> None:
    async with websockets.serve(connection_handler, "localhost", 8765):
        logger.info("[%s] Server listening on ws://localhost:8765", _ts())
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
