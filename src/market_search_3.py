"""Doc 198 — market search 3 (DK 9 Nov 22:31: "go online for more possible trading books to test"). Through THE GATE.
F  OVERNIGHT DRIFT AFTER SELL-OFFS (Boyarchenko, Larsen & Whelan, NY Fed "The Overnight Drift", 2021: S&P futures overnight returns are
   concentrated 00:00-03:00 ET and are strongest after weak closes). Rule fixed in advance: if the US cash session (09:30-16:00 ET) closed
   in the bottom third of its last 60 sessions' returns, buy at 16:15 ET (next bar open) and sell at 03:00 ET. Also the unconditional version.
   US Tech 100, US 500, Wall Street (IG cash indices trade overnight); IG costs; one night's funding charged (~6%/yr, 1/365 of a day).
G  GOLD LONDON BREAKOUT OF THE ASIAN RANGE (MQL5 blog, 3.7 years of tick backtests, PF ~1.37): Asian range 01:00-06:00 UTC; from 06:00 UTC a
   buy-stop above / sell-stop below (first touched wins, one trade a day); stop at the opposite side capped at 0.6% of price; target 2.5R;
   skip days with range < 0.30% or > 1.60% of price; flat at 19:00 UTC. (Breakeven at 1.5R omitted — the gate has one stop.)
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G
from gate_books import load5, NY, sigframe
R = []
def show(r): R.append(r); print(G.line(r) + (f" | by market {r.get('by_market')}" if r.get("by_market") else ""), flush=True)

def ix_prep(f, cost):
    d = load5(f)[["open", "high", "low", "close"]].astype(float); d["cost"] = cost; d["atr"] = G.atr(d).shift(1)
    d["carry"] = d.close * 0.06 / 365 / 200     # spread over ~200 bars a night ~ one night's funding
    lt = d.index.tz_convert(NY); d["tod"] = lt.hour * 60 + lt.minute; d["nyday"] = pd.Series(lt.date, index=d.index).astype(str)
    d["eligible"] = d.tod == 16 * 60 + 10
    return d

def on_signals(d, conditional=True):
    tod = d.tod.values; day = d.nyday.values; C = d.close.values; O = d.open.values
    op = pd.Series(np.where(tod == 570, O, np.nan), index=d.index).groupby(day).transform("max")
    cl = pd.Series(np.where(tod == 955, C, np.nan), index=d.index).groupby(day).transform("max")   # 15:55 bar close = 16:00
    ret = (cl / op - 1)
    daily = ret.groupby(day).first()
    lo3 = daily.rolling(60, min_periods=40).quantile(1 / 3).shift(1)     # threshold from the PRIOR 60 sessions
    thr = pd.Series(day, index=d.index).map(lo3).values
    ix = np.where((tod == 16 * 60 + 10) & np.isfinite(ret.values))[0]   # the 16:10-16:15 bar closes at 16:15 -> buy its next open
    if conditional: ix = ix[np.isfinite(thr[ix]) & (ret.values[ix] <= thr[ix])]
    # hold from 16:15 to 03:00 ET = 10h45 = 129 five-minute bars (IG's daily break makes the count approximate)
    return sigframe(d.index[ix], 1, "market", np.nan, 30 * d.atr.values[ix], np.nan, 129, dist=True)

def gold_signals(d):
    lt = d.index.tz_convert("UTC"); h = lt.hour + lt.minute / 60; day = pd.Series(lt.date, index=d.index).astype(str).values
    H, L, C = d.high.values, d.low.values, d.close.values
    asian = (h >= 1) & (h < 6)
    ahi = pd.Series(np.where(asian, H, np.nan), index=d.index).groupby(day).transform("max").values
    alo = pd.Series(np.where(asian, L, np.nan), index=d.index).groupby(day).transform("min").values
    idx, side, kind, price, stop, tgt = [], [], [], [], [], []
    at6 = np.where((lt.hour == 5) & (lt.minute == 55))[0]                 # the 05:55 bar closes at 06:00: range complete
    for i in at6:
        hi, lo = ahi[i], alo[i]
        if not (np.isfinite(hi) and np.isfinite(lo)): continue
        w = (hi - lo) / C[i]
        if w < 0.003 or w > 0.016: continue
        buf = 0.0002 * C[i]
        for s, p, st in ((1, hi + buf, max(lo, hi * (1 - 0.006))), (-1, lo - buf, min(hi, lo * (1 + 0.006)))):
            risk = abs(p - st); idx.append(d.index[i]); side.append(s); kind.append("stop"); price.append(p); stop.append(st); tgt.append(p + s * 2.5 * risk)
    f = pd.DataFrame({"side": side, "kind": kind, "price": price, "stop": stop, "target": tgt, "max_bars": 156, "valid": 156, "dist": False}, index=pd.DatetimeIndex(idx))
    # one order per bar in the gate: keep the side nearer to price at 06:00 (the gate fills one position at a time anyway)
    out = []
    for t, g in f.groupby(level=0):
        c = d.close.at[t]; out.append(g.iloc[[int(np.argmin(np.abs(g.price.values - c)))]])
    return pd.concat(out) if out else f

if __name__ == "__main__":
    IX = [("US Tech 100", "data_nq_cache/nq_5m.csv", 1.5), ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", 0.8), ("Wall Street", "data_ig_cache/USA30IDXUSD_5m.csv", 3.5)]
    P = {n: ix_prep(f, c) for n, f, c in IX}
    for cond, lab in ((True, "after weak close"), (False, "every night")):
        for n, d in P.items(): show(G.judge(f"OVERNIGHT {lab} {n}", d, lambda x, c=cond: on_signals(x, c)))
        show(G.judge_pool(f"OVERNIGHT {lab} pooled", [(n, d, (lambda x, c=cond: on_signals(x, c)), {}) for n, d in P.items()]))
    gd = load5("data_ig_cache/XAUUSD_5m.csv")[["open", "high", "low", "close"]].astype(float); gd["cost"] = 0.4; gd["atr"] = G.atr(gd).shift(1)
    lt = gd.index.tz_convert("UTC"); gd["session"] = pd.Series(lt.date, index=gd.index).astype(str); gd["eligible"] = (lt.hour >= 6) & (lt.hour < 19)
    show(G.judge("GOLD London breakout of Asian range", gd, gold_signals, flat_at_session_end=True, max_bars_for_random=60))
    open(f"{G.OUT}/search3.txt", "w").write("\n".join(G.line(r) + (f" | by market {r.get('by_market')}" if r.get('by_market') else '') for r in R) + "\n")
