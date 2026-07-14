"""
In-memory matchmaking queue + game state management.
Each active game is a Game object identified by a game_id.
"""
import uuid
from dataclasses import dataclass, field

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diagonals
]


@dataclass
class Player:
    name: str
    ws: object  # WebSocket connection
    symbol: str = ""  # "X" or "O", assigned on match


@dataclass
class Game:
    id: str
    players: list  # [Player, Player]
    board: list = field(default_factory=lambda: [""] * 9)
    turn: str = "X"
    winner: str | None = None  # "X", "O", "draw", or None
    winning_line: list | None = None

    def player_for_symbol(self, symbol: str) -> Player:
        return next(p for p in self.players if p.symbol == symbol)

    def opponent_of(self, player: Player) -> Player:
        return next(p for p in self.players if p is not player)

    def make_move(self, symbol: str, cell: int) -> bool:
        if self.winner is not None:
            return False
        if symbol != self.turn:
            return False
        if not (0 <= cell < 9) or self.board[cell] != "":
            return False

        self.board[cell] = symbol
        self._check_end()
        if self.winner is None:
            self.turn = "O" if self.turn == "X" else "X"
        return True

    def _check_end(self):
        for line in WIN_LINES:
            a, b, c = line
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                self.winner = self.board[a]
                self.winning_line = list(line)
                return
        if all(cell != "" for cell in self.board):
            self.winner = "draw"

    def to_state(self):
        return {
            "board": self.board,
            "turn": self.turn,
            "winner": self.winner,
            "winning_line": self.winning_line,
            "players": {p.symbol: p.name for p in self.players},
        }


class MatchmakingManager:
    def __init__(self):
        self.queue: list[Player] = []
        self.games: dict[str, Game] = {}

    def enqueue(self, player: Player) -> Game | None:
        """Add player to queue. Returns a Game if a match was made, else None."""
        if self.queue:
            opponent = self.queue.pop(0)
            game_id = str(uuid.uuid4())[:8]
            opponent.symbol = "X"
            player.symbol = "O"
            game = Game(id=game_id, players=[opponent, player])
            self.games[game_id] = game
            return game
        else:
            self.queue.append(player)
            return None

    def remove_from_queue(self, player: Player):
        self.queue = [p for p in self.queue if p is not player]

    def get_game(self, game_id: str) -> Game | None:
        return self.games.get(game_id)

    def end_game(self, game_id: str):
        self.games.pop(game_id, None)


manager = MatchmakingManager()
