const WS_HOST = window.location.host;
const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";

let ws = null;
let mySymbol = null;
let myName = "";
let currentGameId = null;

// ----- DOM refs -----
const screens = {
  lobby: document.getElementById("screen-lobby"),
  queue: document.getElementById("screen-queue"),
  game: document.getElementById("screen-game"),
};
const nameInput = document.getElementById("name-input");
const findMatchBtn = document.getElementById("find-match-btn");
const cancelQueueBtn = document.getElementById("cancel-queue-btn");
const playAgainBtn = document.getElementById("play-again-btn");
const board = document.getElementById("board");
const cells = Array.from(document.querySelectorAll(".cell"));
const turnIndicator = document.getElementById("turn-indicator");
const resultBanner = document.getElementById("result-banner");
const resultText = document.getElementById("result-text");
const playerXName = document.getElementById("player-x-name");
const playerOName = document.getElementById("player-o-name");
const toast = document.getElementById("toast");

const leaderboardDrawer = document.getElementById("leaderboard-drawer");
const leaderboardToggle = document.getElementById("leaderboard-toggle");
const closeLeaderboard = document.getElementById("close-leaderboard");
const leaderboardBody = document.getElementById("leaderboard-body");

function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.remove("active"));
  screens[name].classList.add("active");
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3000);
}

// ----- Leaderboard -----
async function loadLeaderboard() {
  try {
    const res = await fetch("/api/leaderboard");
    const data = await res.json();
    leaderboardBody.innerHTML = data
      .map(
        (p, i) => `<tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(p.name)}</td>
          <td>${p.wins}</td>
          <td>${p.losses}</td>
          <td>${p.draws}</td>
          <td>${p.best_streak}</td>
        </tr>`
      )
      .join("");
  } catch (e) {
    leaderboardBody.innerHTML = `<tr><td colspan="6">Couldn't load rankings.</td></tr>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

leaderboardToggle.addEventListener("click", () => {
  loadLeaderboard();
  leaderboardDrawer.classList.add("open");
});
closeLeaderboard.addEventListener("click", () => {
  leaderboardDrawer.classList.remove("open");
});

// ----- Matchmaking -----
findMatchBtn.addEventListener("click", connectAndQueue);
nameInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") connectAndQueue();
});

function connectAndQueue() {
  const name = nameInput.value.trim();
  if (!name) {
    showToast("Enter a fighter name first.");
    return;
  }
  myName = name;
  findMatchBtn.disabled = true;

  ws = new WebSocket(`${WS_PROTOCOL}//${WS_HOST}/ws/${encodeURIComponent(name)}`);

  ws.onopen = () => {
    showScreen("queue");
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleMessage(msg);
  };

  ws.onclose = () => {
    findMatchBtn.disabled = false;
  };

  ws.onerror = () => {
    showToast("Connection error. Is the backend running?");
    findMatchBtn.disabled = false;
  };
}

cancelQueueBtn.addEventListener("click", () => {
  if (ws) ws.close();
  showScreen("lobby");
  findMatchBtn.disabled = false;
});

playAgainBtn.addEventListener("click", () => {
  if (ws) ws.close();
  resultBanner.classList.add("hidden");
  showScreen("lobby");
  findMatchBtn.disabled = false;
});

// ----- Message handling -----
function handleMessage(msg) {
  switch (msg.type) {
    case "queued":
      showScreen("queue");
      break;

    case "match_found":
      mySymbol = msg.symbol;
      currentGameId = msg.game_id;
      playerXName.textContent = msg.state.players.X;
      playerOName.textContent = msg.state.players.O;
      resultBanner.classList.add("hidden");
      renderBoard(msg.state);
      showScreen("game");
      break;

    case "state_update":
      renderBoard(msg.state);
      break;

    case "game_over":
      renderBoard(msg.state);
      showResult(msg.result, msg.state);
      loadLeaderboard();
      break;

    case "opponent_left":
      showToast("Your opponent disconnected.");
      resultBanner.classList.remove("hidden");
      resultText.textContent = "Opponent left the arena.";
      resultText.className = "";
      break;

    case "error":
      showToast(msg.message);
      break;
  }
}

// ----- Board rendering -----
function renderBoard(state) {
  state.board.forEach((val, i) => {
    const cell = cells[i];
    cell.textContent = val;
    cell.className = "cell";
    if (val === "X") cell.classList.add("mark-x");
    if (val === "O") cell.classList.add("mark-o");
    cell.disabled = !!val || !!state.winner;
  });

  if (state.winning_line) {
    state.winning_line.forEach((i) => cells[i].classList.add("win-line"));
  }

  if (!state.winner) {
    turnIndicator.textContent =
      state.turn === mySymbol ? "Your move" : `Waiting for ${state.players[state.turn]}…`;
    turnIndicator.className = "turn-indicator " + (state.turn === "X" ? "active-x" : "active-o");
  } else {
    turnIndicator.textContent = "";
  }
}

function showResult(result, state) {
  resultBanner.classList.remove("hidden");
  if (result === "win") {
    resultText.textContent = "Victory. You win the duel.";
    resultText.className = "win";
  } else if (result === "loss") {
    resultText.textContent = "Defeated. Better luck next round.";
    resultText.className = "loss";
  } else {
    resultText.textContent = "Draw. Evenly matched.";
    resultText.className = "draw";
  }
}

// ----- Player moves -----
cells.forEach((cell) => {
  cell.addEventListener("click", () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const idx = parseInt(cell.dataset.cell, 10);
    ws.send(JSON.stringify({ type: "move", cell: idx }));
  });
});

// Load leaderboard once on page load so it's ready when opened
loadLeaderboard();
