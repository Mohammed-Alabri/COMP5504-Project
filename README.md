# COMP5504 — Real-Time Distributed Auction Platform

A real-time multi-client auction system built for COMP5504: Distributed Systems at Sultan Qaboos University (SQU).

## Tech Stack

- **Server:** Python 3.11+, `asyncio`, `websockets`
- **Client:** Python 3.11+, `PyQt6`, `websockets`
- **Transport:** WebSocket (`ws://localhost:8765`)

## Setup

```bash
pip install -r requirements.txt
```

## Running

Start the server (from project root):
```bash
python -m server.server
```

Start a client (one terminal per user):
```bash
python -m client.client
```

## Features

- Create and join live auctions
- Real-time bid updates pushed to all connected clients
- Circular countdown timer with color-coded urgency
- Per-auction bid serialisation via `asyncio.Lock`
- Graceful handling of client disconnections
