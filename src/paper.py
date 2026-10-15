"""
PAPER TRADING ENGINE — forward test with a pre-registered kill criterion.

MANDATE (from SPEC, permanent): research and paper trading only. No live order,
brokerage or exchange account, credential, authentication, or committed capital
of any size, on any signal, under any circumstance. This file places no orders
and holds no credentials. It writes to a JSON journal and nothing else.

WHY THIS EXISTS
---------------
Everything backward-looking is contaminated: the 2025+ holdout is spent, the
lifetime trial ledger is ~9,600 (so a claim needs |t| > ~4 to mean anything),
and four separate artefacts were found in the engine on 14 Oct alone. The only
uncontaminated evidence available is the future.

THE DESIGN CHOICE THAT MATTERS: THE SHADOW BOOK
-----------------------------------------------
A plain paper account answers "did it make money", which in a rising market is
answered by the market. It cannot answer the question this project actually
hangs on, which is whether the ENTRIES add anything.

So two books run in parallel on the same bars, same universe, same management,
same costs:

    LIVE   entries from the scanner (flag, pullback-in-uptrend, month-high break)
    SHADOW entries chosen at RANDOM, frequency-matched to the live book

Regime is then controlled for by construction. If the market rips, both books
rip and the comparison is unaffected. The number that matters is LIVE minus
SHADOW, not LIVE.

PRE-REGISTERED, AND NOT TO BE CHANGED MID-RUN
---------------------------------------------
Changing the rules during a test means nothing is being tested. The criteria
below are fixed at start. Any amendment voids the run and restarts the clock.
"""
import os, json, math, datetime as dt
import numpy as np, pandas as pd
import SPEC

ROOT = "/home/claude/qlab/runs/paper"
JOURNAL = f"{ROOT}/journal.json"
STATE = f"{ROOT}/state.json"

# ======================================================= PRE-REGISTERED CRITERIA
CRITERIA = {
    "registered_on": "2026-10-14",
    "minimum_evidence": {
        "closed_trades_per_book": 150,
        "or_elapsed_months": 12,
        "note": "whichever comes first; no verdict before this point, in either direction",
    },
    "primary_question": (
        "Does the LIVE book's mean R exceed the SHADOW (random-entry) book's "
        "mean R, by more than 2 standard errors of the difference?"
    ),
    "pass": {
        "live_minus_shadow_R": "> 0",
        "t_of_difference": "> 2.0",
        "live_mean_R": "> 0 after costs",
    },
    "fail_and_stop": {
        "live_minus_shadow_R": "<= 0 at n=150 — the entries add nothing, abandon signal research",
    },
    "early_kill": {
        "equity_drawdown": "> 25% — twice the backtested max on the clean ETF book (-11%)",
        "live_mean_R_at_n100": "< -0.10 with t < -2 — losing faster than noise explains",
        "any_engine_defect_found": "pause, fix, RESTART the clock — a patched run is not a continuous one",
    },
    "explicitly_not_evidence": [
        "profit in a rising market (the shadow book controls for this)",
        "any result before the minimum evidence threshold",
        "a good month, a good week, or a single large winner",
    ],
    "amendment_rule": (
        "Any change to universe, entries, management, sizing or costs VOIDS the "
        "run and restarts the clock. Record the reason and begin again."
    ),
}


# ============================================================== book management
def _blank():
    return dict(
        started=str(dt.date.today()),
        criteria=CRITERIA,
        spec=dict(stop_atr=SPEC.STOP_ATR, stop_min_atr=SPEC.STOP_MIN_ATR,
                  risk_pct=SPEC.RISK_PCT, max_open=SPEC.MAX_OPEN,
                  max_heat=SPEC.MAX_HEAT, max_position_pct=SPEC.MAX_POSITION_PCT,
                  be_offset_r=SPEC.BE_OFFSET_R, meat_bars=SPEC.MEAT_BARS,
                  runner_bars=SPEC.RUNNER_BARS, slippage_bp=SPEC.SLIPPAGE_BP,
                  entries=list(SPEC.ENTRIES_KEPT)),
        books={b: dict(equity=1.0, peak=1.0, open=[], closed=[])
               for b in ("LIVE", "SHADOW")},
        log=[],
    )


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(ROOT, exist_ok=True)
    return _blank()


def save(s):
    os.makedirs(ROOT, exist_ok=True)
    json.dump(s, open(STATE, "w"), indent=1, default=str)


# ================================================================== the engine
def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def plan_trade(sym, df, i, setup, equity, cost):
    """Build a fully-specified plan. Returns None if it fails any SPEC screen."""
    a = float(atr(df).iloc[i]); px = float(df.close.iloc[i])
    if not np.isfinite(a) or a <= 0 or px <= 0:
        return None
    swing_lo = float(df.low.rolling(10).min().iloc[i])
    stop = max(px - SPEC.STOP_ATR * a, swing_lo * 0.995)
    stop = min(stop, px - SPEC.STOP_MIN_ATR * a)          # floor (doc 29)
    risk = px - stop
    if risk <= 0 or risk / px < SPEC.STOP_MIN_COST_MULTIPLE * cost:
        return None
    tp1 = px + 1.0 * risk
    tp2 = px + 3.0 * risk
    # SPEC screen: a target nearer than the stop is negative before costs (doc 30)
    if (tp1 - px) / risk < SPEC.TARGET_MIN_DISTANCE_VS_STOP:
        return None
    notional = equity * SPEC.RISK_PCT / (risk / px)
    if notional / equity > SPEC.MAX_POSITION_PCT:
        notional = equity * SPEC.MAX_POSITION_PCT          # size down, don't reject
    return dict(sym=sym, setup=setup, entry_date=str(df.index[i].date()),
                entry=round(px, 6), stop=round(stop, 6), tp1=round(tp1, 6),
                tp2=round(tp2, 6),
                be_stop=round(px + SPEC.BE_OFFSET_R * risk + cost * px, 6),
                risk_frac=round(risk / px, 6),
                notional_frac=round(notional / equity, 4),
                filled=0.0, pnl_r=0.0, bars=0, cost=cost)


def step_position(p, bar):
    """Advance one open position by one bar. Pessimistic intrabar ordering."""
    h, l, o, c = bar["high"], bar["low"], bar["open"], bar["close"]
    px, risk = p["entry"], p["entry"] - p["stop"]
    cur = p.get("cur_stop", p["stop"])
    p["bars"] += 1
    # 1. stop first (conservative), filled at the open if the bar gapped through
    if l <= cur:
        fill = min(cur, o)
        p["pnl_r"] += (1 - p["filled"]) * (fill - px) / risk
        p["exit_reason"] = "stop" if p["filled"] == 0 else "stop after scale-out"
        return True
    # 2. TP1
    if p["filled"] < 0.34 and h >= p["tp1"]:
        p["pnl_r"] += (1 / 3) * (p["tp1"] - px) / risk
        p["filled"] = 1 / 3
        cur = max(cur, p["be_stop"])
        p["cur_stop"] = cur
        if SPEC.PESSIMISTIC_INTRABAR and l <= cur:      # same bar may have reversed
            p["pnl_r"] += (1 - p["filled"]) * (cur - px) / risk
            p["exit_reason"] = "BE stop, same bar as TP1 (pessimistic)"
            return True
    # 3. TP2
    if p["filled"] < 0.67 and h >= p["tp2"]:
        p["pnl_r"] += (1 / 3) * (p["tp2"] - px) / risk
        p["filled"] = 2 / 3
    # 4. time stops
    if p["bars"] >= SPEC.MEAT_BARS and p["filled"] < 0.66:
        close_frac = (2 / 3) - p["filled"]
        if close_frac > 0:
            p["pnl_r"] += close_frac * (c - px) / risk
            p["filled"] = 2 / 3
    if p["bars"] >= SPEC.RUNNER_BARS:
        p["pnl_r"] += (1 - p["filled"]) * (c - px) / risk
        p["exit_reason"] = "runner time stop"
        return True
    p["cur_stop"] = cur
    return False


def mark(p, close):
    """Unrealised R on the unfilled portion."""
    risk = p["entry"] - p["stop"]
    if risk <= 0:
        return 0.0
    return (1 - p["filled"]) * (close - p["entry"]) / risk


# ================================================================== reporting
def stats(closed):
    if not closed:
        return dict(n=0, meanR=0.0, se=0.0, t=0.0, win=0.0)
    r = np.array([c["pnl_r"] - c["cost"] * c["entry"] / (c["entry"] - c["stop"])
                  for c in closed])
    se = r.std(ddof=1) / math.sqrt(len(r)) if len(r) > 1 else 0.0
    return dict(n=len(r), meanR=float(r.mean()), se=float(se),
                t=float(r.mean() / se) if se > 0 else 0.0,
                win=float((r > 0).mean()))


def report(s):
    print("=" * 86)
    print(f"  PAPER TRADING — started {s['started']}, day "
          f"{(dt.date.today() - dt.date.fromisoformat(s['started'])).days}")
    print("=" * 86)
    print(f"  {SPEC.MANDATE}\n")
    L = stats(s["books"]["LIVE"]["closed"])
    S = stats(s["books"]["SHADOW"]["closed"])
    print(f"  {'book':8s} {'closed':>7} {'open':>5} {'equity':>9} {'mean R':>9} "
          f"{'t':>7} {'win%':>7}")
    for b, st in (("LIVE", L), ("SHADOW", S)):
        bk = s["books"][b]
        print(f"  {b:8s} {st['n']:7d} {len(bk['open']):5d} {bk['equity']:9.4f} "
              f"{st['meanR']:+9.3f} {st['t']:+7.2f} {st['win']*100:6.1f}%")
    diff = L["meanR"] - S["meanR"]
    se = math.sqrt(L["se"] ** 2 + S["se"] ** 2)
    t = diff / se if se > 0 else 0.0
    print(f"\n  THE NUMBER THAT MATTERS — LIVE minus SHADOW: {diff:+.3f}R  (t={t:+.2f})")
    need = CRITERIA["minimum_evidence"]["closed_trades_per_book"]
    have = min(L["n"], S["n"])
    print(f"  evidence: {have}/{need} closed trades per book "
          f"({have/need*100:.0f}% of the pre-registered minimum)")
    if have < need:
        print("  -> NO VERDICT. Below the minimum. This is not a result yet.")
    elif diff > 0 and t > 2.0 and L["meanR"] > 0:
        print("  -> PASS on the pre-registered criteria.")
    elif diff <= 0:
        print("  -> FAIL. The entries add nothing. Abandon signal research.")
    else:
        print("  -> INCONCLUSIVE. Continue or stop, but do not claim an edge.")
    dd = s["books"]["LIVE"]["equity"] / s["books"]["LIVE"]["peak"] - 1
    print(f"\n  LIVE drawdown {dd*100:+.1f}%  (early kill at -25%)")
    if dd < -0.25:
        print("  *** EARLY KILL TRIGGERED ***")


def show_criteria():
    print("PRE-REGISTERED CRITERIA — fixed at start, not amendable mid-run\n")
    print(json.dumps(CRITERIA, indent=2))


if __name__ == "__main__":
    import sys
    s = load()
    if len(sys.argv) > 1 and sys.argv[1] == "criteria":
        show_criteria()
    else:
        SPEC.banner()
        report(s)
        save(s)
