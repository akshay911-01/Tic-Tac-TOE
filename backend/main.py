"""
Tic-Tac-Toe Arena backend.

Run with:  uvicorn main:app --reload --port 8000

WebSocket protocol (client connects to /ws/{player_name}):

  Server -> Client messages:
    {"type": "queued"}
    {"type": "match_found", "game_id", "symbol", "opponent", "state"}
    {"type": "state_update", "state"}
    {"type": "game_over", "state", "result"}   # result: "win" | "loss" | "draw"
    {"type": "opponent_left"}
    {"type": "error", "message"}

  Client -> Server messages:
    {"type": "move", "cell": 0-8}
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

import database
from game_manager import manager, Player

app = FastAPI(title="Tic-Tac-Toe Arena")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# track which game a given connection belongs to, for cleanup on disconnect
connection_game = {}  # ws -> game_id
connection_player = {}  # ws -> Player


@app.on_event("startup")
def startup():
    database.init_db()


@app.get("/api/leaderboard")
def leaderboard():
    return database.get_leaderboard()


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


async def send_state(game):
    """Push the current game state to both players."""
    for p in game.players:
        try:
            await p.ws.send_json({"type": "state_update", "state": game.to_state()})
        except Exception:
            pass


async def finish_game(game):
    """Persist result and notify both players that the game has ended."""
    state = game.to_state()

    if game.winner == "draw":
        database.record_result(
            winner=None, loser=None,
            draw_players=[p.name for p in game.players],
        )
    else:
        winner_player = game.player_for_symbol(game.winner)
        loser_player = game.opponent_of(winner_player)
        database.record_result(winner=winner_player.name, loser=loser_player.name)

    for p in game.players:
        result = "draw" if game.winner == "draw" else ("win" if p.symbol == game.winner else "loss")
        try:
            await p.ws.send_json({"type": "game_over", "state": state, "result": result})
        except Exception:
            pass

    manager.end_game(game.id)


@app.websocket("/ws/{player_name}")
async def websocket_endpoint(websocket: WebSocket, player_name: str):
    await websocket.accept()
    player_name = player_name.strip()[:20] or "Player"
    database.ensure_player(player_name)

    player = Player(name=player_name, ws=websocket)
    connection_player[websocket] = player

    game = manager.enqueue(player)

    if game is None:
        await websocket.send_json({"type": "queued"})
    else:
        connection_game[game.players[0].ws] = game.id
        connection_game[game.players[1].ws] = game.id
        for p in game.players:
            opponent = game.opponent_of(p)
            await p.ws.send_json({
                "type": "match_found",
                "game_id": game.id,
                "symbol": p.symbol,
                "opponent": opponent.name,
                "state": game.to_state(),
            })

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "move":
                game_id = connection_game.get(websocket)
                game = manager.get_game(game_id) if game_id else None
                if game is None:
                    await websocket.send_json({"type": "error", "message": "Game not found."})
                    continue

                cell = data.get("cell")
                valid = game.make_move(player.symbol, cell)
                if not valid:
                    await websocket.send_json({"type": "error", "message": "Invalid move."})
                    continue

                if game.winner is not None:
                    await finish_game(game)
                else:
                    await send_state(game)

    except WebSocketDisconnect:
        pass
    finally:
        manager.remove_from_queue(player)
        game_id = connection_game.pop(websocket, None)
        connection_player.pop(websocket, None)
        if game_id:
            game = manager.get_game(game_id)
            if game is not None:
                opponent = game.opponent_of(player)
                try:
                    await opponent.ws.send_json({"type": "opponent_left"})
                except Exception:
                    pass
                manager.end_game(game_id)
