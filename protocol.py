import json

# Client → Server message types
MSG_CREATE_AUCTION = "create_auction"
MSG_JOIN           = "join"
MSG_BID            = "bid"
MSG_LIST_AUCTIONS  = "list_auctions"

# Server → Client message types
MSG_AUCTION_LIST    = "auction_list"
MSG_UPDATE          = "update"
MSG_REJECTED        = "rejected"
MSG_CLOSED          = "closed"
MSG_ERROR           = "error"
MSG_AUCTION_CREATED = "auction_created"


def build_update(auction_id: int, item: str, highest_bid: float,
                 highest_bidder, time_left: int) -> dict:
    return {
        "type": MSG_UPDATE,
        "auction_id": auction_id,
        "item": item,
        "highest_bid": highest_bid,
        "highest_bidder": highest_bidder,
        "time_left": time_left,
    }


def build_closed(auction_id: int, item: str, winner, final_price: float) -> dict:
    return {
        "type": MSG_CLOSED,
        "auction_id": auction_id,
        "item": item,
        "winner": winner,
        "final_price": final_price,
    }


def build_rejected(auction_id: int, reason: str) -> dict:
    return {
        "type": MSG_REJECTED,
        "auction_id": auction_id,
        "reason": reason,
    }


def build_error(message: str) -> dict:
    return {"type": MSG_ERROR, "message": message}


def build_auction_list(auctions: list) -> dict:
    return {"type": MSG_AUCTION_LIST, "auctions": auctions}


def build_auction_created(auction_id: int, item_name: str) -> dict:
    return {"type": MSG_AUCTION_CREATED, "auction_id": auction_id, "item_name": item_name}


def parse_message(raw: str):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
