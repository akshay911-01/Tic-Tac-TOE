"""
Persistent leaderboard storage using SQLite.
Tracks wins, losses, draws, and a simple win-streak per player name.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "arena.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                name TEXT PRIMARY KEY,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                current_streak INTEGER NOT NULL DEFAULT 0,
                best_streak INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_player(name: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO players (name) VALUES (?)", (name,)
        )
        conn.commit()


def record_result(winner: str | None, loser: str | None, draw_players: list[str] | None = None):
    """
    Call with either (winner, loser) for a decisive game,
    or draw_players=[name1, name2] for a draw.
    """
    with get_conn() as conn:
        if draw_players:
            for name in draw_players:
                conn.execute(
                    """UPDATE players SET draws = draws + 1, current_streak = 0
                       WHERE name = ?""",
                    (name,),
                )
        else:
            conn.execute(
                """UPDATE players
                   SET wins = wins + 1,
                       current_streak = current_streak + 1,
                       best_streak = MAX(best_streak, current_streak + 1)
                   WHERE name = ?""",
                (winner,),
            )
            conn.execute(
                """UPDATE players SET losses = losses + 1, current_streak = 0
                   WHERE name = ?""",
                (loser,),
            )
        conn.commit()


def get_leaderboard(limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT name, wins, losses, draws, best_streak,
                      (wins * 3 + draws) AS score
               FROM players
               ORDER BY score DESC, wins DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
