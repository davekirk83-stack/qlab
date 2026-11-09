"""Doc 195 — 'solve, don't kill' for the Range v3 ladder under honest pricing (orders fixed from the previous closed bar).
Variants: rung depth multiplier m (distance below the EMA = (2 - off) x ATR x m) and exit (mid = EMA, or EMA - 0.5 ATR, quicker).
Crypto 15-min, last 12 months, Revolut X costs, pool 10% / 10 open; judged on both halves."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paperbook6 as P, paperbook14 as B
P.MK, P.TAKER, P.SLIP = 0.0, 0.0009, 0.0010; STOP = P.MARGIN_STOP / P.LEV
def run(d, sym, start, m, exit_off):
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym); O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; idx = d.index
    out = []; p = None; cool = None; s0 = max(251, idx.searchsorted(start))
    for i in range(s0, len(C)):
        j = i - 1
        if not (np.isfinite(a[j]) and a[j] > 0): continue
        tgt = ema[j] - exit_off * a[j]
        if p and p["u"] > 0 and H[i] > tgt:
            p["cash"] += p["u"] * max(tgt, O[i]); out.append((sym, p["o"], idx[i], p["cash"], "mid")); p = None; cool = idx[i]; continue
        if allow[j] and (cool is None or idx[i] >= cool + pd.Timedelta(hours=P.COOLDOWN_H)):
            for k, (frac, off) in enumerate(P.BID):
                if p and k in p["tried"]: continue
                price = ema[j] - (2 - off) * a[j] * m
                if price > 0 and L[i] < price:
                    fill = min(price, O[i])
                    if p is None: p = {"o": idx[i], "u": 0.0, "cash": 0.0, "tried": [], "i0": i, "spent": 0.0}
                    p["tried"].append(k); p["u"] += frac / fill; p["cash"] -= frac; p["spent"] += frac
        if p and p["u"] > 0:
            avg = p["spent"] / p["u"]
            why = ("stop" if L[i] <= avg * (1 - STOP) else "break" if (C[i] < lo_b[i] - 1.5 * a[i] * m or C[i] > hi_b[i] + 1.5 * a[i])
                   else "cap" if i - p["i0"] >= P.CAP_BARS else "regime" if not allow[i] else None)
            if why:
                px = (min(avg * (1 - STOP), O[i]) if why == "stop" else C[i]) * (1 - P.SLIP - P.TAKER); p["cash"] += p["u"] * px
                out.append((sym, p["o"], idx[i], p["cash"], why)); p = None; cool = idx[i]
    return out
U = [s for s in json.load(open("runs/range_universe.json"))["registered_universe"] if s != "ZECUSD"]
D = {}
for s in U:
    f = f"/home/claude/qlab/data_15m/{s}.csv"
    if not os.path.exists(f): continue
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); D[s] = d[["open", "high", "low", "close"]].astype(float)
end = min(d.index.max() for d in D.values()); start = end - pd.Timedelta(days=365); mid = end - pd.Timedelta(days=182)
for m in (1.0, 1.25, 1.5, 2.0):
    for xo in (0.0, 0.5):
        E = []
        for s, d in D.items(): E += run(d[d.index >= start - pd.Timedelta(days=20)], s, start, m, xo)
        r = np.array([e[3] for e in E]); t = np.array([e[1] for e in E])
        h1, h2 = r[t < mid], r[t >= mid]
        eq, mdd, _ = B.pool(E)
        print(f"depth x{m:<4} exit EMA-{xo}ATR: n{len(r):5d} mean {100*r.mean():+.3f}% | H1 {100*h1.mean():+.3f}% H2 {100*h2.mean():+.3f}% | pool £500 -> £{eq:,.0f} maxDD {100*mdd:.0f}%", flush=True)

# Variant B — "reclaim": the look-ahead quietly favoured bars that dipped through the band and CLOSED back up. Trade that openly:
# bar i's low pierced the lower band (as known at bar i-1) and bar i closed back above it -> buy at bar i's close (taker), 100% of the budget;
# exit at the EMA (resting), stop below bar i's low by 0.25 ATR, cap 48 bars, regime off -> out.
def reclaim(d, sym, start):
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym); O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; idx = d.index
    out = []; p = None; cool = None; s0 = max(251, idx.searchsorted(start)); c = (1 + P.SLIP + P.TAKER)
    for i in range(s0, len(C) - 1):
        j = i - 1
        if p:
            k = i
            if L[k] <= p["stop"]: r = min(p["stop"], O[k]) * (1 - P.SLIP - P.TAKER) / p["e"] - 1; out.append((sym, p["o"], idx[k], r, "stop")); p = None; cool = idx[k]; continue
            if H[k] > ema[k - 1]: r = max(ema[k - 1], O[k]) / p["e"] - 1; out.append((sym, p["o"], idx[k], r, "mid")); p = None; cool = idx[k]; continue
            if k - p["i0"] >= P.CAP_BARS or not allow[k]: r = C[k] * (1 - P.SLIP - P.TAKER) / p["e"] - 1; out.append((sym, p["o"], idx[k], r, "cap/regime")); p = None; cool = idx[k]; continue
            continue
        if not (np.isfinite(a[j]) and a[j] > 0 and allow[j]) or (cool is not None and idx[i] < cool + pd.Timedelta(hours=P.COOLDOWN_H)): continue
        if L[i] < lo_b[j] and C[i] > lo_b[j] and C[i] < ema[i]:
            p = {"o": idx[i], "e": C[i] * c, "stop": L[i] - 0.25 * a[i], "i0": i}
    return out
for nm, fn in (("reclaim", reclaim),):
    E = []
    for s, d in D.items(): E += fn(d[d.index >= start - pd.Timedelta(days=20)], s, start)
    r = np.array([e[3] for e in E]); t = np.array([e[1] for e in E]); h1, h2 = r[t < mid], r[t >= mid]; eq, mdd, _ = B.pool(E)
    print(f"{nm}: n{len(r)} mean {100*r.mean():+.3f}% win {100*(r>0).mean():.0f}% | H1 {100*h1.mean():+.3f}% H2 {100*h2.mean():+.3f}% | pool £500 -> £{eq:,.0f} maxDD {100*mdd:.0f}%", flush=True)
