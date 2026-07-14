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

## Project structure
```
tictactoe-arena/
├── backend/
│   ├── main.py           # FastAPI app + WebSocket endpoint (matchmaking + move handling)
│   ├── game_manager.py   # In-memory queue, Game/Player classes, win detection
│   ├── database.py       # SQLite leaderboard persistence
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js          # WebSocket client, board rendering, leaderboard drawer
```

## Talking points for interviews
- **Real-time sync without polling:** state is pushed to both clients the instant a move is made, using a single WebSocket connection per player.
- **Server-authoritative game logic:** the client never decides who won — every move and win condition is validated server-side, so a modified client can't cheat.
- **Matchmaking as a queue, not a lobby list:** models the same "first-available-opponent" pattern used in real matchmaking systems (like competitive game queues), rather than manual room codes.
- **Clean disconnect handling:** if a player closes the tab mid-game, the opponent is notified immediately instead of hanging.
- **Persistent ranking with a derived score:** `wins*3 + draws` is a simple scoring formula you can defend and easily extend (e.g. ELO) if asked "how would you scale this?"

## Natural extensions (if you want to go further)
- Swap SQLite for MongoDB Atlas — you already have that on your resume, so mention you chose SQLite here deliberately for a zero-config demo, but the schema maps directly.
- Add a "rematch" button that re-queues both players against each other.
- Deploy backend on Render/Railway and frontend anywhere static — gives you a live demo link for your resume.
- Add reconnect/resume-game support using the `game_id`.
