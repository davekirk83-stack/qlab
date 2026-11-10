"""Doc 216 — reviewer 2's strategy families at THEIR exact rules (DK 10:43: "are you killing off the other AI's suggestions needlessly?").
All decided at the close, traded at the next open (entries and exits); stops on every bar; costs per market x1, funding 6%/yr x1.4.
Markets: 7 indices + gold + silver, oil, copper, nat gas, 5 FX, US 10-year (as the reviewer asked: genuinely different assets).
Judged alone AND by what each adds to the existing daily books (monthly-return correlation with RSI(4)+TPS+TOM, and the combined result)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF
ALL = [k for k in F.D if k not in ("VIX", "BTC", "ETH")]
def run_side(k, entry, side, exit_=None, maxd=60, stop=2.0, trail=None):
    """next-open in/out, side +1/-1; optional trailing stop of `trail` ATR from the best close."""
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = entry.reindex(d.index).fillna(False).values; X = exit_.reindex(d.index).fillna(False).values if exit_ is not None else np.zeros(len(d), bool)
    cost = F.COST.get(k, .0005); fy = 0.06 / 365 * 1.4; out = []; i = 0; n = len(C)
    while i < n - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        s = side; j0 = i + 1; e = O[j0]; st = e - s * stop * A[i]; best = e; j = j0; px = None
        while j < n:
            if (s == 1 and L[j] <= st) or (s == -1 and H[j] >= st): px = (min(st, O[j]) if s == 1 else max(st, O[j])) if j > j0 else st; break
            if trail: best = max(best, C[j]) if s == 1 else min(best, C[j]); st = max(st, best - trail * A[i]) if s == 1 else min(st, best + trail * A[i])
            if (X[j] or (j - j0 + 1) >= maxd) and j + 1 < n: px = O[j + 1]; j += 1; break
            j += 1
        if px is None: break
        out.append((d.index[i], (s * (px - e) - cost * e * 2 - fy * e * max(j - j0, 0)) / A[i], k)); i = j
    return out
def rep(name, rows):
    t = pd.DataFrame(rows, columns=["t", "R", "m"]); r = t.R; c = t.groupby(t.t.dt.normalize()).R.sum(); y = t.groupby(t.t.dt.year).R.sum(); y = y[y.index < 2026]
    print(f"{name:58s} n{len(t):5d} ({len(t) / 26:.0f}/yr) mean {r.mean():+.3f} t {r.mean() / r.std() * np.sqrt(len(r)):+.2f} clustered t {c.mean() / c.std() * np.sqrt(len(c)):+.2f} | "
          f"full yrs + {(y > 0).sum()}/{len(y)} | last5y {r[t.t.dt.year >= 2022].mean():+.3f}", flush=True); return t
up = lambda d: d.close > d.close.rolling(200).mean(); dn = lambda d: d.close < d.close.rolling(200).mean()
hi = lambda d, n: d.close > d.high.rolling(n).max().shift(1); lo = lambda d, n: d.close < d.low.rolling(n).min().shift(1)
ema = lambda c, n: c.ewm(span=n, adjust=False).mean()
def bbw(d): m = d.close.rolling(20).mean(); s = d.close.rolling(20).std(); return (4 * s / m), m + 2 * s, m - 2 * s
if __name__ == "__main__":
    B = {}
    B["A1 Donchian 55-day breakout LONG, above 200d, exit 20-day low, 2 ATR stop"] = sum([run_side(k, hi(F.D[k], 55) & up(F.D[k]), 1, lo(F.D[k], 20), 250, 2.0) for k in ALL], [])
    B["A2 Donchian 55-day breakout SHORT, below 200d, exit 20-day high"] = sum([run_side(k, lo(F.D[k], 55) & dn(F.D[k]), -1, hi(F.D[k], 20), 250, 2.0) for k in ALL], [])
    B["A3 Donchian 20-day LONG, above 200d, exit 10-day low"] = sum([run_side(k, hi(F.D[k], 20) & up(F.D[k]), 1, lo(F.D[k], 10), 250, 2.0) for k in ALL], [])
    def sq(k, side):
        d = F.D[k]; w, ub, lb = bbw(d); low = w < w.rolling(100).quantile(0.10); pre = low.rolling(5).max().astype(bool)
        e = pre & ((d.close > ub) if side == 1 else (d.close < lb)) & (up(d) if side == 1 else dn(d))
        return run_side(k, e, side, None, 60, 2.0, trail=3.0)
    B["B1 Bollinger squeeze (width < 10th pct of 100d) breakout UP + trend, 3 ATR trail"] = sum([sq(k, 1) for k in ALL], [])
    B["B2 Bollinger squeeze breakout DOWN + trend"] = sum([sq(k, -1) for k in ALL], [])
    def mare(k):
        d = F.D[k]; e20, e50, e200 = ema(d.close, 20), ema(d.close, 50), ema(d.close, 200)
        touched = (d.low <= e20).rolling(3).max().astype(bool); e = (d.close > e200) & (e20 > e50) & touched & (d.close > e20) & (d.close.shift(1) <= e20.shift(1))
        return run_side(k, e, 1, d.close < e50, 60, 2.0)
    B["D  MA re-entry: >200EMA, 20>50EMA, pullback to 20EMA, close back above"] = sum([mare(k) for k in ALL], [])
    T = {nm: rep(nm, rows) for nm, rows in B.items()}
    # E: relative strength rotation, monthly, top 3 by 6-month return among markets above their 200d, equal risk (vol-scaled), next-open
    px = pd.DataFrame({k: F.D[k].close for k in ALL}).ffill(); op = pd.DataFrame({k: F.D[k].open for k in ALL}).ffill()
    me = px.resample("BME").last(); mom = me.pct_change(6); above = me > px.rolling(200).mean().resample("BME").last(); vol = px.pct_change().rolling(60).std().resample("BME").last()
    mr = op.resample("BMS").first().shift(-1).pct_change().shift(-1)   # first open after month-end -> first open after the next month-end
    rows = []
    for t in me.index[7:-1]:
        sc = mom.loc[t].where(above.loc[t]).dropna().sort_values(ascending=False).head(3)
        for k in sc.index:
            nxt = op.index[op.index > t]
            if len(nxt) < 2: continue
            i0 = op.index.get_loc(nxt[0]); i1 = op.index.searchsorted(me.index[me.index > t][0], side="right") if (me.index > t).any() else None
            if i1 is None or i1 >= len(op): continue
            r = op[k].iloc[i1] / op[k].iloc[i0] - 1 - 2 * F.COST.get(k, .0005) - 0.06 / 12 * 1.4 / 1.4
            rows.append((t, r / (vol.loc[t, k] * np.sqrt(21)), k))
    T["E relative strength: top 3 by 6-month return (above 200d), monthly"] = rep("E relative strength: top 3 by 6-month return (above 200d), monthly", rows)
    # portfolio value: monthly correlation with the existing core (RSI4 + TPS + TOM), and combined risk-balanced result
    up4 = lambda d: (up(d) & (F.rsi(d.close, 4) < 25), F.rsi(d.close, 4) > 55)
    core = pd.DataFrame([(t, R) for k in F.IXG for (t, R) in RF.run_o(k, *up4(F.D[k]), 10, 3.0)] + [(t, R) for k in RF.TR6 for (t, R) in F.run(k, __import__("review_ideas_test").tom(F.D[k]), 1, None, 3, stop=5.0)], columns=["t", "R"])
    cm = core.groupby(core.t.dt.to_period("M")).R.sum(); print("\ncore (RSI4 + TOM) monthly ATR sum: mean %.2f, worst 12 months %.1f" % (cm.mean(), cm.rolling(12).sum().min()))
    for nm, t in T.items():
        m = t.groupby(t.t.dt.to_period("M")).R.sum().reindex(cm.index, fill_value=0); sc = cm.std() / m.std() if m.std() > 0 else 0
        comb = cm + m * sc; worst = lambda x: x.rolling(12).sum().min()
        print(f"  + {nm[:56]:56s} corr {cm.corr(m):+.2f} | combined mean/month {comb.mean():+.2f} vs core {cm.mean():+.2f} | worst 12m {worst(comb):+.1f} vs core {worst(cm):+.1f} | "
              f"core's 10 worst months: this book {m[cm.nsmallest(10).index].sum() * sc:+.1f}")
