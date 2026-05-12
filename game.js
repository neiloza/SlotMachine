(() => {
  "use strict";

  // ---------- Game config ----------
  const STORAGE_KEY = "luckyGoldSlots:v1";
  const STARTING_GOLD = 50;

  // Symbol weights tuned so per-payline RTP ≈ 0.51.
  // Combined with the payline-discount scheme (bet 1 = 1 line, bet 2 = 3 lines, bet 3 = 5 lines),
  // effective RTPs land at roughly 51% / 76% / 85% — the "punishing" range the user asked for.
  const SYMBOLS = [
    { key: "cherry",  glyph: "🍒", weight: 35, payout: 4   },
    { key: "lemon",   glyph: "🍋", weight: 25, payout: 8   },
    { key: "bell",    glyph: "🔔", weight: 20, payout: 16  },
    { key: "star",    glyph: "⭐", weight: 12, payout: 35  },
    { key: "seven",   glyph: "7️⃣", weight: 6,  payout: 100 },
    { key: "diamond", glyph: "💎", weight: 2,  payout: 500 },
  ];

  const TOTAL_WEIGHT = SYMBOLS.reduce((sum, s) => sum + s.weight, 0);

  // Each payline = 3 cell coords as [reelIndex, rowIndex].
  const PAYLINES = [
    { id: "row-top",    cells: [[0,0],[1,0],[2,0]] },
    { id: "row-mid",    cells: [[0,1],[1,1],[2,1]] },
    { id: "row-bot",    cells: [[0,2],[1,2],[2,2]] },
    { id: "diag-tl-br", cells: [[0,0],[1,1],[2,2]] },
    { id: "diag-bl-tr", cells: [[0,2],[1,1],[2,0]] },
  ];

  const BET_TO_LINES = {
    1: ["row-mid"],
    2: ["row-top", "row-mid", "row-bot"],
    3: ["row-top", "row-mid", "row-bot", "diag-tl-br", "diag-bl-tr"],
  };

  const BET_HINTS = {
    1: "Middle row only",
    2: "All three rows",
    3: "Rows + both diagonals",
  };

  const MULTIPLIERS = [1, 3, 5, 10];

  // ---------- State ----------
  const state = {
    gold: STARTING_GOLD,
    bet: 1,
    multiplier: 1,
    spinning: false,
    grid: makeRandomGrid(),
    clickerSession: 0,
  };

  // ---------- Persistence ----------
  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (typeof data.gold === "number" && Number.isFinite(data.gold) && data.gold >= 0) {
        state.gold = Math.floor(data.gold);
      }
      if ([1,2,3].includes(data.bet)) state.bet = data.bet;
      if (MULTIPLIERS.includes(data.multiplier)) state.multiplier = data.multiplier;
    } catch (e) {
      // ignore corrupted storage
    }
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        gold: state.gold,
        bet: state.bet,
        multiplier: state.multiplier,
      }));
    } catch (e) {
      // storage might be full or disabled; non-fatal
    }
  }

  // ---------- DOM refs ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const reelEls = $$(".reel");
  const cellEls = reelEls.map(r => $$(".cell", r));
  const paylineEls = {};
  $$(".payline").forEach(line => { paylineEls[line.dataset.line] = line; });

  const balanceEl = $("#balance");
  const clickerBalanceEl = $("#clicker-balance");
  const lastWinEl = $("#last-win");
  const totalBetEl = $("#total-bet");
  const messageEl = $("#message");
  const linesHintEl = $("#lines-hint");
  const spinBtn = $("#spin-btn");
  const getGoldBtn = $("#get-gold-btn");
  const paytableToggle = $("#paytable-toggle");
  const paytable = $("#paytable");
  const paytableBody = $("#paytable-body");
  const slotScreen = $("#slot-screen");
  const clickerScreen = $("#clicker-screen");
  const bigCoin = $("#big-coin");
  const backToSlots = $("#back-to-slots");
  const clickerSessionEl = $("#clicker-session");
  const winBanner = $("#win-banner");
  const winBannerText = $(".win-banner-text", winBanner);

  // ---------- Helpers ----------
  function pickSymbol() {
    let roll = Math.random() * TOTAL_WEIGHT;
    for (const sym of SYMBOLS) {
      roll -= sym.weight;
      if (roll < 0) return sym;
    }
    return SYMBOLS[0];
  }

  function makeRandomGrid() {
    const grid = [];
    for (let r = 0; r < 3; r++) {
      const reel = [];
      for (let row = 0; row < 3; row++) reel.push(pickSymbol());
      grid.push(reel);
    }
    return grid;
  }

  function getActiveLines() {
    return BET_TO_LINES[state.bet].map(id => PAYLINES.find(p => p.id === id));
  }

  function spinCost() {
    return state.bet * state.multiplier;
  }

  // ---------- Rendering ----------
  function renderGrid() {
    for (let r = 0; r < 3; r++) {
      for (let row = 0; row < 3; row++) {
        cellEls[r][row].textContent = state.grid[r][row].glyph;
        cellEls[r][row].classList.remove("win-flash");
      }
    }
  }

  function renderBalance() {
    balanceEl.textContent = state.gold.toLocaleString();
    clickerBalanceEl.textContent = state.gold.toLocaleString();
  }

  function renderBet() {
    totalBetEl.textContent = String(spinCost());
    linesHintEl.textContent = BET_HINTS[state.bet];
    $$(".bet-btn").forEach(btn => {
      const on = Number(btn.dataset.bet) === state.bet;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-checked", on ? "true" : "false");
    });
    $$(".mult-btn").forEach(btn => {
      const on = Number(btn.dataset.mult) === state.multiplier;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-checked", on ? "true" : "false");
    });
    renderActivePaylines();
  }

  function renderActivePaylines() {
    const activeIds = new Set(BET_TO_LINES[state.bet]);
    Object.entries(paylineEls).forEach(([id, el]) => {
      el.classList.toggle("active", activeIds.has(id));
      el.classList.remove("win");
    });
  }

  function renderPaytable() {
    paytableBody.innerHTML = SYMBOLS
      .slice()
      .reverse()
      .map(s => `<tr><td class="symbol">${s.glyph}${s.glyph}${s.glyph}</td><td>${s.payout}× line bet</td></tr>`)
      .join("");
  }

  function renderSpinButton() {
    const canAfford = state.gold >= spinCost();
    spinBtn.disabled = state.spinning || !canAfford;
    getGoldBtn.classList.toggle("visible", state.gold < spinCost() && !state.spinning);
  }

  function setMessage(text) {
    messageEl.textContent = text;
  }

  // ---------- Spin flow ----------
  async function spin() {
    if (state.spinning) return;
    const cost = spinCost();
    if (state.gold < cost) {
      setMessage("Not enough gold. Tap 'Get More Gold' to earn some by clicking.");
      renderSpinButton();
      return;
    }

    state.spinning = true;
    state.gold -= cost;
    renderBalance();
    save();
    renderSpinButton();

    setMessage("");
    lastWinEl.classList.remove("flash");
    Object.values(paylineEls).forEach(el => el.classList.remove("win"));

    reelEls.forEach(r => r.classList.add("spinning"));

    const reelStopDelays = [550, 800, 1100];
    const newGrid = [];
    for (let i = 0; i < 3; i++) {
      newGrid.push([pickSymbol(), pickSymbol(), pickSymbol()]);
    }

    await Promise.all(reelStopDelays.map((delay, i) => new Promise(resolve => {
      setTimeout(() => {
        state.grid[i] = newGrid[i];
        reelEls[i].classList.remove("spinning");
        for (let row = 0; row < 3; row++) {
          cellEls[i][row].textContent = newGrid[i][row].glyph;
        }
        resolve();
      }, delay);
    })));

    const wins = evaluateSpin();
    const totalWin = wins.reduce((sum, w) => sum + w.amount, 0);

    if (totalWin > 0) {
      state.gold += totalWin;
      renderBalance();
      lastWinEl.textContent = totalWin.toLocaleString();
      lastWinEl.classList.add("flash");
      wins.forEach(w => {
        const lineEl = paylineEls[w.payline.id];
        if (lineEl) lineEl.classList.add("win");
        w.payline.cells.forEach(([r, row]) => {
          cellEls[r][row].classList.add("win-flash");
        });
      });

      if (totalWin >= cost * 20) {
        showBanner("BIG WIN!");
      } else if (totalWin >= cost * 5) {
        showBanner("Nice Win!");
      }

      setMessage(`Won ${totalWin} on ${wins.length} line${wins.length > 1 ? "s" : ""}.`);
    } else {
      lastWinEl.textContent = "0";
      setMessage("No win. Try again.");
    }

    save();
    state.spinning = false;
    renderSpinButton();
  }

  function evaluateSpin() {
    const lines = getActiveLines();
    const wins = [];
    for (const line of lines) {
      const [a, b, c] = line.cells.map(([r, row]) => state.grid[r][row]);
      if (a.key === b.key && b.key === c.key) {
        wins.push({
          payline: line,
          amount: a.payout * state.multiplier,
          symbol: a,
        });
      }
    }
    return wins;
  }

  let bannerTimer = null;
  function showBanner(text) {
    winBannerText.textContent = text;
    winBanner.hidden = false;
    if (bannerTimer) clearTimeout(bannerTimer);
    bannerTimer = setTimeout(() => { winBanner.hidden = true; }, 1200);
  }

  // ---------- Clicker ----------
  function showClicker() {
    slotScreen.classList.remove("active");
    clickerScreen.hidden = false;
    clickerScreen.classList.add("active");
    state.clickerSession = 0;
    clickerSessionEl.textContent = "0";
    renderBalance();
  }

  function hideClicker() {
    clickerScreen.classList.remove("active");
    clickerScreen.hidden = true;
    slotScreen.classList.add("active");
    renderSpinButton();
  }

  function clickCoin(ev) {
    state.gold += 1;
    state.clickerSession += 1;
    renderBalance();
    clickerSessionEl.textContent = state.clickerSession.toLocaleString();
    save();
    spawnFloatPlusOne(ev);
  }

  function spawnFloatPlusOne(ev) {
    const float = document.createElement("span");
    float.className = "float-up";
    float.textContent = "+1";

    let x, y;
    if (ev && ev.clientX !== undefined && ev.clientX !== 0) {
      x = ev.clientX;
      y = ev.clientY;
    } else {
      const rect = bigCoin.getBoundingClientRect();
      x = rect.left + rect.width / 2 + (Math.random() - 0.5) * rect.width * 0.5;
      y = rect.top + rect.height / 2;
    }
    float.style.left = `${x}px`;
    float.style.top = `${y}px`;
    document.body.appendChild(float);
    setTimeout(() => float.remove(), 900);
  }

  // ---------- Wiring ----------
  function wireControls() {
    $$(".bet-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        if (state.spinning) return;
        state.bet = Number(btn.dataset.bet);
        save();
        renderBet();
        renderSpinButton();
      });
    });

    $$(".mult-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        if (state.spinning) return;
        state.multiplier = Number(btn.dataset.mult);
        save();
        renderBet();
        renderSpinButton();
      });
    });

    spinBtn.addEventListener("click", spin);
    getGoldBtn.addEventListener("click", showClicker);
    backToSlots.addEventListener("click", hideClicker);

    bigCoin.addEventListener("click", clickCoin);

    paytableToggle.addEventListener("click", () => {
      const open = paytable.hasAttribute("hidden") ? true : false;
      if (open) {
        paytable.removeAttribute("hidden");
        paytableToggle.setAttribute("aria-expanded", "true");
      } else {
        paytable.setAttribute("hidden", "");
        paytableToggle.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.key === " " || ev.key === "Enter") {
        const activeOnSlot = slotScreen.classList.contains("active");
        if (activeOnSlot && document.activeElement !== bigCoin) {
          ev.preventDefault();
          if (!spinBtn.disabled) spin();
        }
      }
    });
  }

  // ---------- Init ----------
  function init() {
    load();
    renderGrid();
    renderBalance();
    renderBet();
    renderPaytable();
    renderSpinButton();
    wireControls();

    if (state.gold < spinCost()) {
      setMessage("Welcome back! Tap 'Get More Gold' if you need to refill.");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
