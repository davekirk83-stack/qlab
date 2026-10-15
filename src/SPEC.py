"""
SINGLE SOURCE OF TRUTH for the trading system specification.

WHY THIS FILE EXISTS
--------------------
On 14 Oct 2026 DK caught a silent drift: his instruction was that take-profits sit
on fib/structural levels, spec v1 honoured it (TP2 = 1.618 fib extension), then
run15.py quietly substituted a flat 3R because R-multiples are easier to sweep.
Six subsequent runs — bollinger, ichimoku, shorts, the multi-asset test — inherited
the substitution. The written spec said one thing and the code did another, and
nothing connected them.

Documents do not prevent that. This file does: every run imports these constants
rather than declaring its own, so a change happens in one place or not at all.

RULES FOR THIS FILE
-------------------
1. No run may hard-code a parameter that exists here. Import it.
2. Any change to a value requires a one-line entry in CHANGELOG below, with the
   doc number that justifies it. No entry, no change.
3. A run that deliberately departs from spec (a sweep, an experiment) must call
   `departure()` and state why. It will print the divergence in the output so it
   cannot pass unnoticed into a later run.
4. DK's design decisions are marked [DK]. They are not mine to optimise away
   without telling him.
"""

# ============================================================== THE CONSTRAINT
# Permanent. Not a parameter. Not subject to review.
MANDATE = (
    "Research and paper trading only. No live order, brokerage or exchange account, "
    "credential, authentication, or committed capital of any size, on any signal, "
    "under any circumstance."
)

# ================================================================== ENTRY SIDE
# Status after doc 29 (barrier-race test on 60 survivorship-clean ETFs).
# An entry is KEPT only if it shifts P(+3ATR before -3ATR) above baseline at |z|>2.
ENTRIES_KEPT = {
    "flag":                 dict(p3_gain_pp=+3.9, z=+2.8, mfe_mae=1.035),
    "pullback in uptrend":  dict(p3_gain_pp=+2.7, z=+3.5, mfe_mae=0.987),
    "month-high break":     dict(p3_gain_pp=+3.2, z=+2.4, mfe_mae=1.048),
}
ENTRIES_REJECTED = {
    "swing break":          "no effect (-0.2pp at 3ATR)",
    "donchian 20":          "no effect (-0.2pp at 3ATR); duplicates swing break after dedup",
    "quarter-high break":   "HARMFUL: -3.1pp at 1ATR, z=-2.9",
    "all 6 bollinger entries":  "doc 24 — best +115.7% vs incumbent +256.2%",
    "all 8 ichimoku signals":   "doc 26 — best bundle worse than its own components",
    "rally into downtrend (short)": "doc 27 — -2.9% annualised",
}

# ================================================================== EXIT SIDE
# [DK] The scale-out structure. This is DK's design and it is what carries the
# system's expectancy: strip it out and every target scheme loses money (doc 30).
# Stress-tested under pessimistic intrabar ordering: +0.60R, t=19.
SCALE_OUT = True                 # [DK] take a third, then a third, leave a runner
TP1_FRACTION = 1 / 3             # [DK]
TP2_FRACTION = 1 / 3             # [DK]
BE_OFFSET_R = 0.10               # [DK] stop goes slightly ABOVE breakeven after TP1
MEAT_BARS = 5                    # [DK] the "meat" done within the day/week
RUNNER_BARS = 60                 # [DK] runner left to take care of itself
RUNNER_HAS_TARGET = True         # [DK] "I'd like those runners to also have targets"

# Target placement. Structural targets were TESTED and REJECTED (doc 30): best
# structural scheme beat the arbitrary 3R control by +0.007R. BUT the screening
# rule below is mandatory and is the real finding of that run.
TARGET_MIN_DISTANCE_VS_STOP = 1.0   # a target nearer than the stop is negative
#   before costs. "Next swing high" sits at 0.64 ATR against a 1.5 ATR stop:
#   risking 1.5 to make 0.64 at a 56% hit rate. Negative by construction.
#   ANY target scheme must pass this screen before it is considered.

# Stop. 1.0 was spec v1 and came from a sweep that never tested past 2.5.
# Portfolio simulation (not per-trade metrics) selected 1.5 — see WARNING below.
STOP_ATR = 1.5
STOP_MIN_ATR = 0.5               # floor. Without it, a swing low sitting on the
#   entry price collapses the risk denominator and produces a -148R trade that
#   removes 74% of the account (doc 29).
STOP_MIN_COST_MULTIPLE = 2.0     # and never tighter than 2x round-trip cost

# ================================================================ POSITION SIDE
RISK_PCT = 0.005
MAX_OPEN = 4
MAX_HEAT = 0.03
MAX_POSITION_PCT = 0.25          # hard cap. Risk-based sizing implied a 268%
#   position in SHY (0.19% stop) and 472% at the extreme — uncosted, unmargined
#   leverage masquerading as an edge (doc 29).
MAX_GROSS_EXPOSURE = 1.00

# ================================================================= ENGINE RULES
# These are defaults, not options. Each was introduced because its absence
# flattered a result.
MARK_TO_MARKET_DAILY = True      # doc 28: without it, Sharpe read 3.30 and maxDD
#   -16.6%; with it, 1.34 and -43.1%. The curve was a staircase of realised P&L.
PESSIMISTIC_INTRABAR = True      # doc 30: worth 0.21R of reported performance
GAP_THROUGH_STOPS = True         # fill at the open, not the stop price
SLIPPAGE_BP = 5.0                # each way
CHARGE_COSTS = True              # ~45bp round trip on ETFs = ~0.3R per trade.
#   This is a FIRST-ORDER design constraint: any structure averaging under ~10
#   bars needs an edge larger than anything yet measured (doc 30).

# ================================================================== REPORTING
# Rules about how results are stated, because the numbers were misleading before.
NEVER_QUOTE_CAGR_WITHOUT_DRAWDOWN = True   # Sharpe is flat ~1.9-2.1 across every
#   sizing setting: sizing is a leverage dial, not an edge. CAGR alone describes
#   how hard the dial was turned.
CALMAR_REJECTED = True           # selects 2% risk / 12 positions / -86% drawdown,
#   because CAGR compounds without bound while drawdown caps at 100%.
REQUIRE_RANDOM_CONTROL = True    # no entry is promoted without beating a matched
#   random-entry control. This is the single most valuable diagnostic in the lab.
REQUIRE_BARRIER_TEST = True      # entries are judged exit-free, via P(+k before
#   -k), so a wrong exit geometry cannot disguise a good entry or vice versa.

# ================================================== KNOWN LIMITS, CARRIED FORWARD
OBJECTIVE_FN_WARNING = (
    "Return-per-unit-capital-time is valid for comparing ENTRIES and HOLDING "
    "PERIODS. It is INVALID for stop widths, targets, or anything that changes "
    "position size, because it measures return on notional and assumes constant "
    "size. Following it would have set the stop at 3.0 ATR — the second-worst "
    "setting in the account simulation. Those comparisons go to the portfolio "
    "simulator. (doc 25)"
)
UNIVERSE_WARNING = (
    "Crypto panel is 13 majors + 120 altcoins = ~90% crypto, all of which lived "
    "through the same two bull markets. Pooled crypto figures are close to one "
    "correlated observation repeated. data_wide/ (129 instruments, 10y) is the "
    "survivorship-clean comparison; its 69 single stocks were selected by me "
    "knowing the outcome, so only the 60 ETFs are clean. (docs 27, 28)"
)
OPEN_QUESTIONS = [
    "Long+short combined portfolio is incoherent: worse drawdown than either "
    "book alone, non-monotonic in risk. Not diagnosed. Figures withheld. (doc 28)",
    "Shorts are most profitable in BULL regimes and lose in FLAT. Mechanism "
    "unexplained; the obvious selectivity story fails on the data. (doc 27)",
    "FLAT/choppy is the weak regime on BOTH sides. Unaddressed.",
    "Crypto random-entry control must be re-run under the corrected simulator.",
    "Forward paper testing with a kill criterion agreed IN ADVANCE. Outstanding "
    "since doc 21. The historical holdout is spent.",
]

# ==================================================================== CHANGELOG
CHANGELOG = [
    ("2026-10-14", "doc 25", "STOP_ATR 1.0 -> 1.5 (portfolio sim, not per-trade metric)"),
    ("2026-10-14", "doc 29", "STOP_MIN_ATR floor added after a -148R trade"),
    ("2026-10-14", "doc 29", "MAX_POSITION_PCT added; sizing implied 472% positions"),
    ("2026-10-14", "doc 28", "MARK_TO_MARKET_DAILY made default"),
    ("2026-10-14", "doc 30", "PESSIMISTIC_INTRABAR made default (-0.21R)"),
    ("2026-10-14", "doc 30", "Structural targets tested and REJECTED; "
                             "TARGET_MIN_DISTANCE_VS_STOP screen added instead"),
    ("2026-10-14", "doc 24", "Confirmations split into momentum / mean-reversion; "
                             "volatility filters removed from momentum (-159 to -348pp)"),
    ("2026-10-14", "doc 29", "quarter-high break dropped (harmful)"),
    ("2026-10-14", "doc 21", "RISK_PCT 0.01 -> 0.005, MAX_OPEN 8 -> 4"),
]

_DEPARTURES = []


def departure(what, why):
    """Declare a deliberate divergence from spec. Printed in the run output so it
    cannot leak silently into later work — which is exactly how 1.618 became 3R."""
    _DEPARTURES.append((what, why))
    print(f"  [SPEC DEPARTURE] {what} — {why}")


def banner():
    print("=" * 78)
    print("  SPEC — single source of truth")
    print("=" * 78)
    print(f"  {MANDATE}")
    print(f"  stop {STOP_ATR} ATR (floor {STOP_MIN_ATR}) · risk {RISK_PCT*100:.2f}% · "
          f"max {MAX_OPEN} open · position cap {MAX_POSITION_PCT*100:.0f}%")
    print(f"  engine: mark-to-market={MARK_TO_MARKET_DAILY} "
          f"pessimistic-intrabar={PESSIMISTIC_INTRABAR} "
          f"gap-stops={GAP_THROUGH_STOPS} slippage={SLIPPAGE_BP}bp")
    print(f"  entries kept: {', '.join(ENTRIES_KEPT)}")
    if _DEPARTURES:
        print(f"  DEPARTURES THIS RUN: {len(_DEPARTURES)}")
    print()


if __name__ == "__main__":
    banner()
    print("CHANGELOG")
    for d, src, what in CHANGELOG:
        print(f"  {d}  [{src}]  {what}")
    print("\nOPEN QUESTIONS")
    for q in OPEN_QUESTIONS:
        print(f"  - {q}")
    print(f"\nOBJECTIVE FUNCTION WARNING\n  {OBJECTIVE_FN_WARNING}")
    print(f"\nUNIVERSE WARNING\n  {UNIVERSE_WARNING}")
