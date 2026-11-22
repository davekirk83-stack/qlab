"""DK 22 Nov ("Yes do all of those on your list"): the LIQ book (estimated liquidation clusters, doc 225) given DK's way of trading:
 - DK's scale-in: 4 resting bids at the cluster, -1%, -2%, -3% sized 10/20/30/40% (vs LIQ's 50/50 at 0 / -1%)
 - DK's exits: take profit at +3% / +4% above the average (vs LIQ's farthest short cluster), stop 4% under the cluster
 - DK's flush filter for bear regimes: below the 200-day, only clusters reached by a flush (price fell >= 6% in the 72h before the tap)
Revolut X costs (maker 0% on bids/targets, taker 0.09% + 0.05% slippage on stops/time exits). 15-min BTC 2021-26. R = % on the full ladder."""
import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
import liq_book as LB
H, L, C, O, N, IX, BULL = LB.H, LB.L, LB.C, LB.O, LB.N, LB.IX, LB.BULL
TAKER, SLIP = 0.0009, 0.0005
E = LB.events(cpi=True)
hi72 = pd.Series(H).rolling(288, min_periods=50).max().values
def trade(j, lvl, rungs, weights, tp, stop_f=0.04, hold=96*7, tgt_abs=None):
    stop = lvl*(1-stop_f); end = min(N-1, j+hold); qty = cost = 0.0; filled = [False]*len(rungs)
    for k in range(j, end+1):
        for r, (f, w) in enumerate(zip(rungs, weights)):
            if not filled[r] and L[k] <= lvl*f and k <= j + 96*2: filled[r] = True; qty += w; cost += w*lvl*f
        if qty == 0:
            if k > j + 96*2: return None
            continue
        avg = cost/qty; tgt = tgt_abs if tgt_abs else avg*(1+tp)
        if L[k] <= stop: return qty*((stop*(1-SLIP)*(1-TAKER))/avg - 1)*100
        if k > j and H[k] >= tgt: return qty*(tgt/avg - 1)*100
    avg = cost/qty; return qty*((C[end]*(1-SLIP)*(1-TAKER))/avg - 1)*100
LIQ = ([1.0, 0.99], [0.5, 0.5]); DK = ([1.0, 0.99, 0.98, 0.97], [0.1, 0.2, 0.3, 0.4])
def run(name, ladder, tp, regime, tgt_mode=None):
    rows = []; busy = -1
    for j, lvl, tgt, near in E.values:
        j = int(j)
        if j <= busy: continue
        bull = BULL[j]; flush = C[j] <= hi72[j]*0.94
        if regime == "bull" and not bull: continue
        if regime == "bull+flush-in-bear" and not (bull or flush): continue
        if regime == "bear-flush-only" and (bull or not flush): continue
        r = trade(j, lvl, ladder[0], ladder[1], tp, tgt_abs=(tgt if tgt_mode == "farthest" else None))
        if r is None: continue
        rows.append((IX[j], r)); busy = j + 96   # one ladder per day
    R = pd.Series([x for _, x in rows], index=[t for t, _ in rows])
    if not len(R): return f"  {name:58} n0"
    y = R.groupby(R.index.year).sum(); hf = len(R)//2
    return f"  {name:58} n{len(R):4} mean {R.mean():+.3f}% win {(R>0).mean():.0%} total {R.sum():+.0f}% | halves {R.iloc[:hf].mean():+.3f}/{R.iloc[hf:].mean():+.3f} | years+ {(y>0).sum()}/{len(y)}: " + " ".join(f"{k}:{v:+.0f}" for k, v in y.items())
out = []
for regime in ("all", "bull", "bull+flush-in-bear", "bear-flush-only"):
    out.append(f"== regime: {regime}")
    out.append(run("LIQ as built (50/50 bids, target = farthest short cluster)", LIQ, None, regime, "farthest"))
    for tp in (0.03, 0.04):
        out.append(run(f"LIQ bids, DK take-profit +{tp:.0%}", LIQ, tp, regime))
        out.append(run(f"DK scale-in (10/20/30/40 to -3%), take-profit +{tp:.0%}", DK, tp, regime))
    out.append(run("DK scale-in, target = farthest short cluster", DK, None, regime, "farthest"))
open("runs/research/liq_book_dk.txt", "w").write("\n".join(out)); print("\n".join(out))
