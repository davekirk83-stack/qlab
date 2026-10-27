"""
THE PAPER BOOK v10 — "AO saucer trend v9.1: 10 coins + daily filter, 3h". Registered 27 Oct 2026 (doc 145d, DK: "Yes why not").
Runs BESIDE book 9; book 9 is unchanged. Identical engine, two pre-registered differences (doc 145d):
  universe   BTC ETH SOL XRP DOGE ADA LINK AVAX LTC DOT
  daily      entries (real AND shadow) only while the last COMPLETED daily close is above the daily Alligator jaw
             (SMMA13 of the daily median price, shifted 8). Exits are unaffected.
Sealed-holdout backtest (1 Apr 2025 on, 10 coins): n403, PF 1.22, beats random entries 99%.
Below is book 9's description, which applies in full except for the two differences above.

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading only. No live order, brokerage or
exchange account, credential, authentication, or committed capital of any size, on any signal, under any
circumstance. This script opens nothing, holds no key, and talks to one public read-only market-data endpoint.

WHAT IT TESTS (doc 145c). Bill Williams' Awesome Oscillator saucer used as he designed it, inside a trend system
(rules as published in Skyrexio's TradingView "MultiLayer AO Saucer Strategy"). Backtest 2021-2026, 3h bars, 0.15%
per side: BTC 227 trades, 36% win, PF 1.48; ETH 218 trades, 36% win, PF 1.52; saucer timing beat random entries
under the same filter and exit in all six period slices (76-90% of 200 draws).

THE REGISTERED CONFIGURATION
  bars       3-hour, built from the 15-minute cache; BTCUSD and ETHUSD only; LONG ONLY
  trend      close > EMA100 AND Alligator/fractal trend UP: the last up-fractal break (close above the latest confirmed
             up fractal, that fractal above the Alligator teeth = SMMA8 of the median price shifted 5) came after the last
             down-fractal break below the teeth
  saucer     AO (SMA5 - SMA34 of median price): three bars all > 0 with a1 > a2 < a3; the third bar is the signal bar
  entry      buy stop at the signal bar's high; while AO keeps rising and price has not triggered it, the stop moves down
             to each lower bar high; cancelled if AO turns down; fill at max(stop, previous close) + 0.15%
  size       10% of book equity per entry; up to 5 entries (pyramiding on further saucers) per coin
  exit       ALL entries on a coin close at the bar close when its trend flips DOWN (close below the latest down fractal
             while that fractal is below the teeth); 0.15% cost out. No stop, no target.
  SHADOW     per coin, at every eligible bar (trend up, close > EMA100, fewer than 5 shadow entries) a deterministic
             pseudo-random draw enters with probability 0.041 (the backtest's saucer entry rate per eligible bar);
             identical exit. The measured quantity is REAL minus SHADOW.
  KILL       flatten=1 or 2 closes everything at the close and blocks entries (it is a long book)
  PASS/FAIL  minimum 60 closed entries or 6 months; PASS if mean > 0 net of costs AND real beats shadow; early kill if
             any 20-entry block averages worse than -3%
  Any change to the above voids the run and restarts the clock.

Emits SQL to runs/paper10_<date>.sql (tables pb10_equity, pb10_trades).
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, hashlib
import numpy as np, pandas as pd
import paperbook2 as PB

RUNS = PB.RUNS
STATE = f"{RUNS}/paper10_state.json"
COST, FRAC, MAXN, START, P_SHADOW = 0.0015, 0.10, 5, 2000.0, 0.041
SYMS = ["BTCUSD","ETHUSD","SOLUSD","XRPUSD","DOGEUSD","ADAUSD","LINKUSD","AVAXUSD","LTCUSD","DOTUSD"]


def bars3h(d):
    return d.resample("3h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def build(d):
    mp = (d.high + d.low) / 2
    ao = (mp.rolling(5).mean() - mp.rolling(34).mean()).values
    teeth = mp.ewm(alpha=1/8, adjust=False).mean().shift(5).values
    ema = d.close.ewm(span=100, adjust=False).mean().values
    H, L, C = d.high.values, d.low.values, d.close.values; n = len(C)
    upf = np.full(n, np.nan); dnf = np.full(n, np.nan); lu = ld = np.nan
    for i in range(4, n):          # fractal at i-2 is confirmed at bar i
        k = i - 2
        if H[k] == max(H[k-2:k+3]): lu = H[k]
        if L[k] == min(L[k-2:k+3]): ld = L[k]
        upf[i] = lu; dnf[i] = ld
    state = np.zeros(n, int); s = 0
    for i in range(1, n):
        if np.isfinite(upf[i-1]) and C[i] > upf[i-1] and upf[i-1] > teeth[i]: s = 1
        elif np.isfinite(dnf[i-1]) and C[i] < dnf[i-1] and dnf[i-1] < teeth[i]: s = -1
        state[i] = s
    return ao, ema, state, H, L, C


def daily_ok(sym, d15, idx3):
    """True at each 3h bar if the previous completed UTC day closed above the daily jaw. Daily bars from data_daily/
    (rebuilt by STEP 1 from Coinbase); falls back to resampling the 15-minute cache."""
    f = f"/home/claude/qlab/data_daily/{sym}.csv"
    dy = None
    if os.path.exists(f):
        try:
            dy = pd.read_csv(f); dy["t"] = pd.to_datetime(dy.t, unit="ms", utc=True)
            dy = dy.set_index("t").sort_index()[["high", "low", "close"]].astype(float)
        except Exception:
            dy = None
    if dy is None or len(dy) < 60:
        dy = d15.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    mp = (dy.high + dy.low) / 2; jaw = mp.ewm(alpha=1/13, adjust=False).mean().shift(8)
    ok = (dy.close > jaw).shift(1)
    return ok.reindex(idx3.floor("1D")).fillna(False).values.astype(bool)


def draw(key):
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 10**6 / 10**6


if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H_ = PB.halted(); flatten = H_.get("flatten", 1) if H_ else 0
    st = {"equity": START, "shadow_equity": START, "sym": {}, "closed": 0, "closed_shadow": 0, "started": today,
          "spec": "AO saucer trend v9.1, 10 coins + daily filter, 3h (doc 145d)"}
    if os.path.exists(STATE):
        st = json.load(open(STATE))
    print(f"paper book v10 (AO saucer trend v9.1, 10 coins + daily) — {today} — equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}", flush=True)
    if H_: print(f"  *** HALT: {H_.get('reason')} (flatten={flatten}) ***", flush=True)
    closed, closed_sh = [], []
    for s in SYMS:
        d = PB.refresh(s)
        if d is None or len(d) < 600: print(f"  {s}: no data"); continue
        d3 = bars3h(d); ao, ema, state, H, L, C = build(d3); idx = d3.index; dok = daily_ok(s, d, idx)
        rec = st["sym"].setdefault(s, {"since": None, "pos": [], "shadow": [], "pend": None})
        if rec["since"] is None:
            rec["since"] = str(idx[-2]); print(f"  {s}: first run — watermark {idx[-2]}, nothing traded"); continue
        start = max(int(np.searchsorted(idx, pd.Timestamp(rec["since"]), side="right")), 40)
        for i in range(start, len(C) - 1):      # the last bar is still forming: process completed bars only
            t = str(idx[i])
            if (state[i] == -1 or flatten in (1, 2)) and (rec["pos"] or rec["shadow"]):
                how = "halt" if flatten in (1, 2) else "trend_flip"
                for p in rec["pos"]: closed.append((s, p["opened"], t, (C[i]*(1-COST))/p["entry"] - 1, how, False))
                for p in rec["shadow"]: closed_sh.append((s, p["opened"], t, (C[i]*(1-COST))/p["entry"] - 1, how, True))
                rec["pos"], rec["shadow"], rec["pend"] = [], [], None
            if flatten in (1, 2): continue
            pd_ = rec["pend"]
            if pd_ is not None and state[i] == 1:
                if H[i] > pd_ and len(rec["pos"]) < MAXN:
                    rec["pos"].append({"opened": t, "entry": max(pd_, C[i-1]) * (1 + COST)}); rec["pend"] = None
                elif ao[i] < ao[i-1]: rec["pend"] = None
                elif H[i] < pd_: rec["pend"] = float(H[i])
            if state[i] != 1 or C[i] <= ema[i] or not dok[i]: continue
            if ao[i] > 0 and ao[i-1] > 0 and ao[i-2] > 0 and ao[i-2] > ao[i-1] and ao[i] > ao[i-1]:
                rec["pend"] = float(H[i])
            if len(rec["shadow"]) < MAXN and draw(f"{s}|{t}|v10") < P_SHADOW:
                rec["shadow"].append({"opened": t, "entry": C[i] * (1 + COST)})
        rec["since"] = str(idx[len(C) - 2])
        print(f"  {s}: bars to {idx[-2]}, trend {'UP' if state[-2] == 1 else 'DOWN' if state[-2] == -1 else 'none'}, "
              f"{len(rec['pos'])} open / {len(rec['shadow'])} shadow open, pending stop {rec['pend']}", flush=True)
    for c in closed: st["equity"] += st["equity"] * FRAC * c[3]
    for c in closed_sh: st["shadow_equity"] += st["shadow_equity"] * FRAC * c[3]
    st["closed"] += len(closed); st["closed_shadow"] += len(closed_sh)
    open_n = sum(len(v["pos"]) for v in st["sym"].values())
    print(f"  closed {len(closed)} real / {len(closed_sh)} shadow, {open_n} open, equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)
    lines = ["CREATE TABLE IF NOT EXISTS pb10_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);",
             "CREATE TABLE IF NOT EXISTS pb10_trades (d TEXT, sym TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT, shadow INTEGER);",
             f"INSERT OR REPLACE INTO pb10_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) "
             f"VALUES ('{today}', {st['equity']:.4f}, {st['shadow_equity']:.4f}, {open_n}, {st['closed']}, {st['closed_shadow']});"]
    for c in closed + closed_sh:
        lines.append("INSERT INTO pb10_trades (d, sym, opened, closed, ret, how, shadow) "
                     f"VALUES ('{today}', '{c[0]}', '{c[1]}', '{c[2]}', {c[3]:.6f}, '{c[4]}', {1 if c[5] else 0});")
    out = f"{RUNS}/paper10_{today}.sql"; open(out, "w").write("\n".join(lines))
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
