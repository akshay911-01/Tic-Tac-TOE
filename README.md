
# Tic-Tac-Toe Arena

Real-time 1v1 tic-tac-toe with live matchmaking and a persistent leaderboard.

## Stack
- **Backend:** Python, FastAPI, native WebSockets, SQLite
- **Frontend:** Vanilla HTML/CSS/JS (no build step, no framework)

## How it works
1. A player enters a name and clicks **Find Opponent**, opening a WebSocket connection to `/ws/{name}`.
2. The server holds a matchmaking queue. The first player waits; when a second player connects, they're paired into a `Game` and both get a `match_found` message with their symbol (X/O) and the live board state.
3. Every move is validated server-side (correct turn, empty cell, game not already over) and the new board state is broadcast to both sockets over WebSockets — no polling.
4. When a game ends (win or draw), the result is written to SQLite (`wins`, `losses`, `draws`, `current_streak`, `best_streak` per player name) and both players get a `game_over` message.
5. The leaderboard is served via a normal REST endpoint (`GET /api/leaderboard`) and ranked by `wins * 3 + draws`.

## Run it locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open **http://localhost:8000** in two different browser tabs (or two browsers / incognito windows) to simulate two players. The SQLite database (`arena.db`) is created automatically on first run.

