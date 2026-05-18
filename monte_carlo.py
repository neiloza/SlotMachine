"""
Monte Carlo simulation of Lucky Gold Slots.
Mirrors the exact game logic from game.js (weights, payouts, paylines, bet levels).
Players start with 100 coins and spin until broke; we track the peak balance reached.
"""

import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter

# ---------------------------------------------------------------------------
# Game constants (mirrored from game.js)
# ---------------------------------------------------------------------------

# (name, weight, payout)
SYMBOLS = [
    ("cherry",  35,   4),
    ("lemon",   25,   8),
    ("bell",    20,  16),
    ("star",    12,  35),
    ("seven",    6, 100),
    ("diamond",  2, 500),
]
TOTAL_WEIGHT = sum(s[1] for s in SYMBOLS)  # 100

# Paylines as (reel, row) index pairs — grid is indexed grid[reel][row]
ALL_PAYLINES = [
    [(0, 0), (1, 0), (2, 0)],  # row-top
    [(0, 1), (1, 1), (2, 1)],  # row-mid  ← only active at bet=1
    [(0, 2), (1, 2), (2, 2)],  # row-bot
    [(0, 0), (1, 1), (2, 2)],  # diag top-left → bottom-right
    [(0, 2), (1, 1), (2, 0)],  # diag bottom-left → top-right
]

MULTIPLIERS = [1, 3, 5, 10]

STARTING_COINS = 100
N_SIMULATIONS  = 10_000

# Simulation uses bet=3 → all 5 paylines (3 rows + 2 diagonals)
BET        = 3   # 3-coin bet → 5 active paylines
MULTIPLIER = 1   # 1× multiplier


# ---------------------------------------------------------------------------
# Core game mechanics
# ---------------------------------------------------------------------------

def pick_symbol() -> int:
    """Return symbol index using weighted-random selection (mirrors pickSymbol in game.js)."""
    roll = random.random() * TOTAL_WEIGHT
    for i, (_, weight, _) in enumerate(SYMBOLS):
        roll -= weight
        if roll < 0:
            return i
    return 0


def make_grid() -> list[list[int]]:
    """Return a 3-reel × 3-row grid of symbol indices."""
    return [[pick_symbol() for _ in range(3)] for _ in range(3)]


def get_active_paylines(bet: int) -> list:
    if bet == 1:
        return [ALL_PAYLINES[1]]   # middle row only
    elif bet == 2:
        return ALL_PAYLINES[:3]    # all 3 rows
    else:
        return ALL_PAYLINES        # all 5 lines


def evaluate_spin(grid, paylines, multiplier: int) -> int:
    """Calculate total winnings for one spin (mirrors evaluateSpin in game.js)."""
    total = 0
    for payline in paylines:
        a, b, c = (grid[r][row] for r, row in payline)
        if a == b == c:
            total += SYMBOLS[a][2] * multiplier
    return total


# ---------------------------------------------------------------------------
# Single-player simulation
# ---------------------------------------------------------------------------

def simulate_player(
    starting_coins: int = STARTING_COINS,
    bet: int = BET,
    multiplier: int = MULTIPLIER,
) -> tuple[int, int]:
    """
    Play until broke. Returns (peak_coins, spins_taken).
    Peak is the highest balance reached at any point during the session.
    """
    coins      = starting_coins
    peak       = coins
    spin_cost  = bet * multiplier
    paylines   = get_active_paylines(bet)
    spins      = 0

    while coins >= spin_cost:
        coins -= spin_cost
        coins += evaluate_spin(make_grid(), paylines, multiplier)
        spins += 1
        if coins > peak:
            peak = coins

    return peak, spins


# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------

print(f"Running {N_SIMULATIONS:,} simulations  (bet={BET}, multiplier={MULTIPLIER}×, start={STARTING_COINS} coins)…")
results = [simulate_player() for _ in range(N_SIMULATIONS)]
peaks, spins_list = zip(*results)
peaks      = np.array(peaks,      dtype=np.int64)
spins_list = np.array(spins_list, dtype=np.int64)

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def pct_above(arr, threshold):
    return 100 * np.mean(arr > threshold)

stats = {
    "mean_peak":    peaks.mean(),
    "median_peak":  np.median(peaks),
    "std_peak":     peaks.std(),
    "min_peak":     peaks.min(),
    "max_peak":     peaks.max(),
    "p25":          np.percentile(peaks, 25),
    "p75":          np.percentile(peaks, 75),
    "p90":          np.percentile(peaks, 90),
    "p95":          np.percentile(peaks, 95),
    "p99":          np.percentile(peaks, 99),
    "mean_spins":   spins_list.mean(),
    "median_spins": np.median(spins_list),
    "pct_no_gain":  100 * np.mean(peaks <= STARTING_COINS),
    "pct_2x":       pct_above(peaks, STARTING_COINS * 2),
    "pct_5x":       pct_above(peaks, STARTING_COINS * 5),
    "pct_10x":      pct_above(peaks, STARTING_COINS * 10),
}

# Theoretical single-payline RTP (bet=1, multiplier=1)
rtp = sum((w / TOTAL_WEIGHT) ** 3 * payout for _, w, payout in SYMBOLS)
house_edge = 1 - rtp

print(f"\n{'─'*52}")
print(f"  PEAK BALANCE STATISTICS  ({N_SIMULATIONS:,} players)")
print(f"{'─'*52}")
print(f"  Theoretical RTP           : {rtp*100:.2f}%")
print(f"  House edge per spin       : {house_edge*100:.2f}%")
print(f"  Mean peak balance         : {stats['mean_peak']:.1f} coins")
print(f"  Median peak balance       : {stats['median_peak']:.0f} coins")
print(f"  Std deviation             : {stats['std_peak']:.1f} coins")
print(f"  Min peak                  : {stats['min_peak']} coins")
print(f"  Max peak                  : {stats['max_peak']} coins")
print(f"{'─'*52}")
print(f"  Percentiles:")
print(f"    25th                    : {stats['p25']:.0f} coins")
print(f"    75th                    : {stats['p75']:.0f} coins")
print(f"    90th                    : {stats['p90']:.0f} coins")
print(f"    95th                    : {stats['p95']:.0f} coins")
print(f"    99th                    : {stats['p99']:.0f} coins")
print(f"{'─'*52}")
print(f"  Session length:")
print(f"    Mean spins              : {stats['mean_spins']:.0f}")
print(f"    Median spins            : {stats['median_spins']:.0f}")
print(f"{'─'*52}")
print(f"  Outcome breakdown:")
print(f"    Never exceeded start    : {stats['pct_no_gain']:.1f}%")
print(f"    Peaked above 2× start   : {stats['pct_2x']:.1f}%")
print(f"    Peaked above 5× start   : {stats['pct_5x']:.1f}%")
print(f"    Peaked above 10× start  : {stats['pct_10x']:.1f}%")
print(f"{'─'*52}\n")


# ---------------------------------------------------------------------------
# Histogram + analysis chart
# ---------------------------------------------------------------------------

ACCENT   = "#FFD700"   # gold
BG       = "#1a1a2e"   # deep navy (matches game theme)
PANEL    = "#16213e"
TEXT     = "#f0e6d3"
DIM_TEXT = "#9a9aaa"
RED_LINE = "#ff6b6b"
GRN_LINE = "#69db7c"

fig = plt.figure(figsize=(14, 10), facecolor=BG)
fig.suptitle(
    "Lucky Gold Slots — Monte Carlo Simulation\n"
    f"{N_SIMULATIONS:,} players · {STARTING_COINS} starting coins · "
    f"Bet {BET} · {MULTIPLIER}× multiplier",
    fontsize=15, fontweight="bold", color=ACCENT, y=0.97,
)

gs = gridspec.GridSpec(
    2, 2,
    figure=fig,
    hspace=0.42, wspace=0.32,
    top=0.90, bottom=0.07, left=0.09, right=0.97,
)

ax_main  = fig.add_subplot(gs[0, :])   # top-row: spans both columns
ax_log   = fig.add_subplot(gs[1, 0])   # bottom-left: log-scale close-up
ax_cdf   = fig.add_subplot(gs[1, 1])   # bottom-right: CDF

for ax in (ax_main, ax_log, ax_cdf):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=DIM_TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2a2a4a")

def add_vline(ax, x, label, color):
    ax.axvline(x, color=color, linewidth=1.5, linestyle="--", alpha=0.85)
    ax.text(x, ax.get_ylim()[1] * 0.96, f" {label}\n {x:.0f}", color=color,
            fontsize=7.5, va="top")

# ── Main histogram ──────────────────────────────────────────────────────────
clip = int(np.percentile(peaks, 98))   # clip extreme outliers for readability
clipped = peaks[peaks <= clip]
bins = min(100, len(np.unique(clipped)))

n, bin_edges, patches = ax_main.hist(
    clipped, bins=bins, color=ACCENT, edgecolor="#2a2a4a", linewidth=0.4, alpha=0.9,
)

# Colour bars by zone
for patch, left in zip(patches, bin_edges[:-1]):
    if left < STARTING_COINS:
        patch.set_facecolor("#c0392b")
        patch.set_alpha(0.85)
    elif left < STARTING_COINS * 2:
        patch.set_facecolor(ACCENT)
    else:
        patch.set_facecolor("#2ecc71")
        patch.set_alpha(0.85)

ax_main.set_title("Peak Balance Distribution (clipped at 98th pct for visibility)",
                   color=TEXT, fontsize=11, pad=6)
ax_main.set_xlabel("Peak coin balance reached", color=DIM_TEXT, fontsize=9)
ax_main.set_ylabel("Number of players", color=DIM_TEXT, fontsize=9)
ax_main.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))

ylim = ax_main.get_ylim()
ax_main.axvline(STARTING_COINS, color=RED_LINE, linewidth=2, linestyle="-",
                label=f"Start ({STARTING_COINS})")
ax_main.axvline(stats["mean_peak"], color=GRN_LINE, linewidth=1.5, linestyle="--",
                label=f"Mean ({stats['mean_peak']:.0f})")
ax_main.axvline(stats["median_peak"], color="#74c0fc", linewidth=1.5, linestyle="--",
                label=f"Median ({stats['median_peak']:.0f})")

ax_main.legend(facecolor=PANEL, edgecolor="#2a2a4a", labelcolor=TEXT, fontsize=8,
               loc="upper right")

# Annotation: no-gain zone
ax_main.text(
    STARTING_COINS / 2, ylim[1] * 0.6,
    f"{stats['pct_no_gain']:.1f}%\nnever\ngained",
    color=RED_LINE, fontsize=9, ha="center", va="center", fontweight="bold",
)
ax_main.text(
    STARTING_COINS * 1.5, ylim[1] * 0.6,
    f"{100 - stats['pct_no_gain'] - stats['pct_2x']:.1f}%\ngained\nbut < 2×",
    color=ACCENT, fontsize=9, ha="center", va="center", fontweight="bold",
)
ax_main.text(
    min(STARTING_COINS * 3, clip * 0.75), ylim[1] * 0.6,
    f"{stats['pct_2x']:.1f}%\npeak\n≥ 2×",
    color=GRN_LINE, fontsize=9, ha="center", va="center", fontweight="bold",
)

# ── Log-scale histogram ─────────────────────────────────────────────────────
ax_log.hist(peaks, bins=80, color=ACCENT, edgecolor="#2a2a4a", linewidth=0.3, alpha=0.9)
ax_log.set_yscale("log")
ax_log.set_title("Full Range (log scale)", color=TEXT, fontsize=10, pad=6)
ax_log.set_xlabel("Peak coin balance", color=DIM_TEXT, fontsize=9)
ax_log.set_ylabel("Players (log)", color=DIM_TEXT, fontsize=9)
ax_log.axvline(STARTING_COINS, color=RED_LINE, linewidth=1.5, linestyle="--")
ax_log.set_xlim(left=0)

# Annotate rare big wins
rare_thresholds = [500, 1000, 5000]
for t in rare_thresholds:
    count = np.sum(peaks >= t)
    if count > 0:
        ax_log.axvline(t, color="#aaa", linewidth=0.8, linestyle=":")
        ax_log.text(t, 1.5, f"≥{t}\n({count})", color=DIM_TEXT, fontsize=6.5,
                    ha="center")

# ── CDF ────────────────────────────────────────────────────────────────────
sorted_peaks = np.sort(peaks)
cdf = np.arange(1, len(sorted_peaks) + 1) / len(sorted_peaks)

ax_cdf.plot(sorted_peaks, cdf * 100, color=ACCENT, linewidth=2)
ax_cdf.set_title("Cumulative Distribution (CDF)", color=TEXT, fontsize=10, pad=6)
ax_cdf.set_xlabel("Peak coin balance", color=DIM_TEXT, fontsize=9)
ax_cdf.set_ylabel("% of players at or below", color=DIM_TEXT, fontsize=9)
ax_cdf.set_xlim(0, int(np.percentile(peaks, 99.5)))
ax_cdf.set_ylim(0, 100)
ax_cdf.grid(True, color="#2a2a4a", linewidth=0.5)

for p_val, pct, color in [
    (stats["median_peak"], 50, "#74c0fc"),
    (stats["p90"],         90, GRN_LINE),
    (stats["p99"],         99, "#ff922b"),
]:
    ax_cdf.axhline(pct, color=color, linewidth=0.8, linestyle=":")
    ax_cdf.axvline(p_val, color=color, linewidth=0.8, linestyle=":")
    ax_cdf.text(p_val + 2, pct + 1, f"p{pct}={p_val:.0f}", color=color, fontsize=7.5)

# ── Footer stats bar ────────────────────────────────────────────────────────
footer = (
    f"RTP {rtp*100:.1f}%  |  House edge {house_edge*100:.1f}%  |  "
    f"Mean spins {stats['mean_spins']:.0f}  |  "
    f"Median spins {stats['median_spins']:.0f}  |  "
    f"Max peak {stats['max_peak']:,} coins"
)
fig.text(0.5, 0.01, footer, ha="center", va="bottom", color=DIM_TEXT, fontsize=8)

output_path = "/home/user/SlotMachine/monte_carlo_histogram.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"Histogram saved → {output_path}")
plt.close()
