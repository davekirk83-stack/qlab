"""DK 22 Nov 09:35 "make improvements": the flush-bid ladder (doc 248). Cleaner simulator + a grid chosen on 2021-23 and judged on 2024-26:
drop size that arms it, rung spacing, stop, take-profit, and SMARTER adds (add on the reclaim + MACD turn, but move the ladder's stop to
break-even at the same time, so the add is paid for by risk taken off)."""
import sys, itertools; sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from flush_book import bars
COST = 0.0004
d = bars(); H, L, C = d.h.values, d.l.values, d.c.values; hn = d.h4_new.values; h4c = d.h4_close.values; hh = d.h4_hist.values; hp = d.h4_hist_prev.values
def setups(drop):
    i = 72; out = []
    while i < len(d) - 24*8:
        if C[i] <= H[i-72:i].max()*(1-drop):
            lvl = L[i-72:i-6].min()
            if C[i] > lvl*0.995: out.append((i, lvl)); i += 72; continue
        i += 1
    return out
SP = {"tight": [0.995, 0.985, 0.97, 0.955], "wide": [0.99, 0.97, 0.95, 0.93]}; W = [0.1, 0.2, 0.3, 0.4]
def ladder(i, lvl, rungs, stopf, tp, adds, life=48, hold=24*7):
    stop = lvl*stopf; filled = [False]*4; qty = 0.0; cost = 0.0; pnl = 0.0; added = False; low = np.inf
    unit = sum(w*(lvl*f - stop) for f, w in zip(rungs, W))
    for j in range(i+1, min(i+hold, len(C))):
        low = min(low, L[j])
        if j < i+life:
            for r, (f, w) in enumerate(zip(rungs, W)):
                if not filled[r] and L[j] <= lvl*f: filled[r] = True; qty += w; cost += w*lvl*f
        if qty == 0:
            if j >= i+life: return None
            continue
        avg = cost/qty
        if adds and not added and hn[j] and h4c[j] > lvl and hh[j] > hp[j] and low < lvl:
            stop = max(stop, avg)                       # ladder stop to break-even, then add half a unit at the close
            qty += 0.5; cost += 0.5*C[j]; added = True; avg = cost/qty
        if L[j] <= stop: return (qty*(stop - avg) - COST*2*cost)/unit
        if H[j] >= avg*(1+tp): return (qty*avg*tp - COST*2*cost)/unit
    j = min(i+hold, len(C)-1); avg = cost/qty if qty else 0
    return (qty*(C[j]-avg) - COST*2*cost)/unit if qty else None
rows = []
for drop, sp, stopf, tp, adds in itertools.product((0.06, 0.08), ("tight", "wide"), (0.94, 0.92), (0.03, 0.05), (False, True)):
    if stopf >= SP[sp][-1]: continue
    S = setups(drop); r = [(d.index[i], x) for i, lvl in S for x in [ladder(i, lvl, SP[sp], stopf, tp, adds)] if x is not None]
    R = pd.Series([x for _, x in r], index=[t for t, _ in r])
    a, b = R[R.index.year <= 2023], R[R.index.year >= 2024]; cum = R.cumsum(); dd = (cum.cummax()-cum).max()
    rows.append(dict(drop=drop, spacing=sp, stop=stopf, tp=tp, adds=adds, n=len(R), mean=R.mean(), win=(R>0).mean(), total=R.sum(), maxdd=dd,
                     first=a.mean(), second=b.mean(), yrs_pos=int((R.groupby(R.index.year).sum() > 0).sum())))
G = pd.DataFrame(rows).sort_values("first", ascending=False)
pd.set_option("display.width", 220)
out = ["Grid (sorted by the 2021-23 result; 2024-26 is the out-of-sample check):", G.round(3).to_string(index=False)]
best = G.iloc[0]; out.append(f"\nChosen on 2021-23: drop {best.drop}, {best.spacing}, stop {best.stop}, tp {best.tp}, adds {best.adds} -> 2024-26 {best.second:+.3f}R per setup (2021-23 {best['first']:+.3f})")
base = G[(G.drop == 0.06) & (G.spacing == "tight") & (G.stop == 0.94) & (G.tp == 0.03)]
G["adds"] = G.adds.astype(bool); key = ["drop", "spacing", "stop", "tp"]
M = G[~G.adds].set_index(key)[["mean", "maxdd", "win"]].join(G[G.adds].set_index(key)[["mean", "maxdd", "win"]], rsuffix="_adds")
out.append("\nSmart adds (stop to break-even when adding) vs no adds:\n" + M.round(3).to_string())
open("runs/research/flush_book_improve.txt", "w").write("\n".join(out)); print("\n".join(out))

# Bigger flushes only (doc 229: after 10%+ drops the median bounce was +9% within 3 days): arm at 10%/12% under the 7-day high.
def setups7(drop):
    i = 168; out = []
    while i < len(d) - 24*8:
        if C[i] <= H[i-168:i].max()*(1-drop):
            lvl = L[i-168:i-6].min()
            if C[i] > lvl*0.99: out.append((i, lvl)); i += 24*5; continue
        i += 1
    return out
out4 = ["\n== Big flushes (7-day high -> drop), ladder under the 7-day low"]
for drop in (0.10, 0.12):
    for sp, stopf, tp, adds in (("tight", 0.94, 0.03, False), ("tight", 0.94, 0.05, False), ("wide", 0.92, 0.05, False), ("wide", 0.92, 0.08, False), ("tight", 0.94, 0.05, True)):
        S = setups7(drop); r = [(d.index[i], x) for i, lvl in S for x in [ladder(i, lvl, SP[sp], stopf, tp, adds, life=72, hold=24*10)] if x is not None]
        R = pd.Series([x for _, x in r], index=[t for t, _ in r]); a, b = R[R.index.year <= 2023], R[R.index.year >= 2024]
        cum = R.cumsum(); dd = (cum.cummax()-cum).max()
        out4.append(f"  drop {drop:.0%} {sp} stop {stopf} tp {tp:.0%} adds {adds}: n{len(R)} mean {R.mean():+.3f}R win {(R>0).mean():.0%} total {R.sum():+.1f}R maxDD {dd:.1f} | 21-23 {a.mean():+.3f} 24-26 {b.mean():+.3f}")
open("runs/research/flush_book_improve.txt", "a").write("\n".join(out4)); print("\n".join(out4))
