"""DK flush-bid book (DK 21 Nov 14:56-14:58): resting bid ladders under a broken support after a flush, built in small pieces, then adds
on confirmation (reclaim of the level + 4h MACD histogram turning up), each piece with its own stop. Compared with all-in at the first
level, bids only, and the 4h trigger alone (sweep wick + MACD turn + reclaim). BTCUSDT 1h bars from Binance 15m, 2021-2026.
Returns per setup in R (loss at the full stop of the ladder = -1R). Costs 0.04% per side (maker bids could be 0 on Revolut X)."""
import sys; sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
COST = 0.0004
def bars():
    d = load().resample("1h").agg(dict(o="first", h="max", l="min", c="last", v="sum")).dropna()
    c4 = d.c.resample("4h").last(); m = c4.ewm(span=12, adjust=False).mean() - c4.ewm(span=26, adjust=False).mean(); hist = m - m.ewm(span=9, adjust=False).mean()
    d["h4_close"] = c4.reindex(d.index, method="ffill"); d["h4_hist"] = hist.reindex(d.index, method="ffill"); d["h4_hist_prev"] = hist.shift(1).reindex(d.index, method="ffill")
    d["h4_new"] = d.index.isin(c4.index + pd.Timedelta(hours=3))   # last 1h bar of each 4h candle (its close is the 4h close)
    return d
RUNGS = [(0.995, .10), (0.985, .20), (0.97, .30), (0.955, .40)]
STOP, TP, LIFE, HOLD, DROP = 0.94, 1.04, 48, 24*7, 0.06
def setups(d):
    H, L, C = d.h.values, d.l.values, d.c.values; i = 72; out = []
    while i < len(d) - HOLD - LIFE:
        hi72 = H[i-72:i].max()
        if C[i] <= hi72*(1-DROP):
            lvl = L[i-72:i-6].min()          # prior support: the lowest low of the 3 days before the last 6h
            if C[i] > lvl*0.995: out.append((i, lvl)); i += 24*3; continue
        i += 1
    return out
def run(d, i, lvl, mode):
    H, L, C = d.h.values, d.l.values, d.c.values; hn = d.h4_new.values; h4c = d.h4_close.values; hh = d.h4_hist.values; hp = d.h4_hist_prev.values
    stop = lvl*STOP; risk_unit = sum(w*(lvl*f - stop) for f, w in RUNGS)        # $ lost per 1 unit of ladder at the stop (per BTC-unit)
    fills = []; flush_low = np.inf; added = False; end = i + HOLD
    if mode == "trigger":
        for j in range(i+1, i+LIFE+24):
            flush_low = min(flush_low, L[j])
            if flush_low < lvl and hn[j] and h4c[j] > lvl and hh[j] > hp[j]:
                st = flush_low*0.995; e = C[j]; rr = (e - st)
                for k in range(j+1, min(j+HOLD, len(C))):
                    if L[k] <= st: return ((st-e) - COST*2*e)/rr, 1
                    if H[k] >= e*TP: return ((e*TP-e) - COST*2*e)/rr, 1
                k = min(j+HOLD, len(C)-1); return ((C[k]-e) - COST*2*e)/rr, 1
        return None, 0
    if mode == "allin":
        for j in range(i+1, i+LIFE):
            if L[j] <= lvl*RUNGS[0][0]:
                e = lvl*RUNGS[0][0]; rr = e - stop
                for k in range(j, min(j+HOLD, len(C))):
                    if L[k] <= stop: return ((stop-e) - COST*2*e)/rr, 1
                    if H[k] >= e*TP: return ((e*TP-e) - COST*2*e)/rr, 1
                k = min(j+HOLD, len(C)-1); return ((C[k]-e) - COST*2*e)/rr, 1
        return None, 0
    # ladder (+ optional confirmation adds)
    pnl = 0.0; open_ = []
    for j in range(i+1, min(end, len(C))):
        if j < i+LIFE:
            for f, w in RUNGS:
                px = lvl*f
                if L[j] <= px and (f, w) not in [(a, b) for a, b, *_ in open_ + fills]:
                    open_.append((f, w, px, stop)); flush_low = min(flush_low, L[j])
        flush_low = min(flush_low, L[j]) if open_ else flush_low
        if mode == "adds" and open_ and not added and hn[j] and h4c[j] > lvl and hh[j] > hp[j] and flush_low < lvl:
            open_.append(("add", 0.5, C[j], flush_low*0.995)); added = True
        still = []
        for f, w, px, st in open_:
            if L[j] <= st: pnl += w*((st-px) - COST*2*px); fills.append((f, w, px, st))
            elif H[j] >= px*TP if f == "add" else H[j] >= (np.mean([p for _, _, p, _ in open_])*TP): pnl += w*((px*TP if f=="add" else np.mean([p for _, _, p, _ in open_])*TP) - px - COST*2*px); fills.append((f, w, px, st))
            else: still.append((f, w, px, st))
        open_ = still
        if not open_ and (fills and j >= i+1) and all(x[0] != "pending" for x in fills) and j > i+LIFE: break
    for f, w, px, st in open_: pnl += w*((C[min(end, len(C)-1)] - px) - COST*2*px)
    if not fills and not open_: return None, 0
    return pnl/risk_unit, 1
if __name__ == "__main__":
    d = bars(); S = setups(d); out = [f"BTC flush setups (1h close {DROP:.0%} under the 72h high, close still above prior support): {len(S)} since 2021"]
    res = {}
    for mode in ("allin", "ladder", "adds", "trigger"):
        r = [(d.index[i], x) for i, lvl in S for x, f in [run(d, i, lvl, mode)] if x is not None]
        R = pd.Series([x for _, x in r], index=[t for t, _ in r]); res[mode] = R
        half = len(R)//2; cum = R.cumsum(); dd = (cum.cummax() - cum).max()
        out.append(f"  {mode:8} n{len(R):3} mean {R.mean():+.3f}R win {(R>0).mean():.0%} total {R.sum():+.1f}R maxDD {dd:.1f}R | halves {R.iloc[:half].mean():+.3f}/{R.iloc[half:].mean():+.3f} | by year " +
                   ", ".join(f"{y} {g.sum():+.1f}" for y, g in R.groupby(R.index.year)))
    open("runs/research/flush_book.txt", "w").write("\n".join(out)); print("\n".join(out))
    pd.concat(res, axis=1).to_csv("runs/research/flush_book_trades.csv")
