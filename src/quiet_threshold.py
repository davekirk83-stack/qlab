"""
WHERE EXACTLY IS THE LINE? — the operating threshold, which was never set.

DK: "Did we also find a system for establishing the right 'quiet' conditions
     to run this book?"

Partly, and the missing half is this. Doc 105 chose the INSTRUMENT - containment
beat eight alternatives - by splitting every detector at its own median. That
was the right way to rank nine instruments fairly against each other, because
any other split would have flattered whichever one it suited.

But it left the book declaring a range 50% OF THE TIME BY CONSTRUCTION. The
median is a property of the test, not a property of the market. Nobody has
asked whether the top third, the top quartile or the top tenth of containment
is where this book should actually be trading.

THE SWEEP. Containment at its 50th, 60th, 70th, 80th and 90th percentile,
each measured against the symbol's own expanding history so it is causal and
comparable across coins. Then the same thresholds with the two confirmations
from doc 106 - efficiency and ADX, the instruments that separate a range that
PAYS from one that merely exists.

WHAT DECIDES IT. Not per-trade return, which rises automatically as the
threshold tightens and the book cherry-picks. Three things together:

  total P&L     a threshold that doubles the average by refusing nine trades
                in ten has made the book worse, not better
  worst trade   the tail is what leverage turns into an account event
  time in       the share of bars the book is willing to trade. Below ~10%
                the strategy is barely running and breadth collapses, which
                doc 112 showed is the thing that actually drives Sharpe

Worst-tick break fills throughout, per doc 107.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48


def book(d, allow, ema, lo_b, hi_b, a):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); out = []; inv = []; oi = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            sz = sum(x for _, x in inv); cost = sum(p*x for p, x in inv)/sz
            out.append((L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1)
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    cost = sum(p*x for p, x in inv)/sz
                    out.append(((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz))
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv: sold = set()
        held = sum(x for _, x in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: oi = i
    return out


if __name__ == "__main__":
    data = RD.load()
    P = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        P[s] = (d, D, ema, lo_b, hi_b, a)
    print(f"{len(data)} symbols, 15-minute bars, worst-tick break fills.\n")
    print("Doc 105 split every detector at its MEDIAN so nine instruments could be")
    print("ranked fairly. That left the book calling a range 50% of the time by")
    print("construction. This asks where the line actually belongs.\n")

    print("="*100)
    print("CONTAINMENT ALONE, BY THRESHOLD")
    print("="*100)
    print(f"  {'threshold':<22}{'time in':>9}{'trades':>9}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'total P&L':>12}")
    rows = []
    for q in (0.50, 0.60, 0.70, 0.80, 0.90):
        res = []; tin = []
        for s, (d, D, ema, lo_b, hi_b, a) in P.items():
            v = pd.Series(D["contain"])
            thr = v.expanding(500).quantile(q)
            al = (v > thr).values
            tin.append(float(np.nanmean(al)))
            res += book(d, al, ema, lo_b, hi_b, a)
        if len(res) < 200: continue
        r = np.array(res); t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
        rows.append((f"contain > p{int(q*100)}", np.mean(tin), len(r), r.mean(),
                     t, r.min(), r.sum()))
        print(f"  {'contain > p'+str(int(q*100)):<22}{np.mean(tin)*100:>8.0f}%"
              f"{len(r):>9}{r.mean()*100:>+11.4f}%{t:>+8.2f}{(r>0).mean()*100:>5.0f}%"
              f"{r.min()*100:>+8.1f}%{r.sum()*100:>+11.0f}%")

    print("\n" + "="*100)
    print("WITH THE TWO CONFIRMATIONS (efficiency and ADX, doc 106)")
    print("="*100)
    print(f"  {'rule':<34}{'time in':>9}{'trades':>9}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'total P&L':>12}")
    for cq in (0.50, 0.60, 0.70):
        for xq, xlbl in ((0.50, "p50"), (0.60, "p60")):
            lbl = f"contain>p{int(cq*100)} + eff,adx>{xlbl}"
            res = []; tin = []
            for s, (d, D, ema, lo_b, hi_b, a) in P.items():
                cv = pd.Series(D["contain"]); ev = pd.Series(D["eff"])
                av = pd.Series(D["adx"])
                al = ((cv > cv.expanding(500).quantile(cq)) &
                      (ev > ev.expanding(500).quantile(xq)) &
                      (av > av.expanding(500).quantile(xq))).values
                tin.append(float(np.nanmean(al)))
                res += book(d, al, ema, lo_b, hi_b, a)
            if len(res) < 200: continue
            r = np.array(res); t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
            rows.append((lbl, np.mean(tin), len(r), r.mean(), t, r.min(), r.sum()))
            print(f"  {lbl:<34}{np.mean(tin)*100:>8.0f}%{len(r):>9}"
                  f"{r.mean()*100:>+11.4f}%{t:>+8.2f}{(r>0).mean()*100:>5.0f}%"
                  f"{r.min()*100:>+8.1f}%{r.sum()*100:>+11.0f}%")

    print("\n  Per-trade return rises automatically as the threshold tightens —")
    print("  that is cherry-picking, not improvement. The columns that decide are")
    print("  TOTAL P&L (did the pot grow?), WORST (what leverage turns into an")
    print("  account event) and TIME IN (below ~10% the book is barely running).")
    if rows:
        bt = max(rows, key=lambda z: z[6])
        bw = max(rows, key=lambda z: z[5])
        print(f"\n  MOST TOTAL P&L : {bt[0]} — in {bt[1]*100:.0f}% of the time, "
              f"{bt[2]:,} trades, {bt[3]*100:+.4f}% each, worst {bt[5]*100:+.1f}%")
        print(f"  TAMEST TAIL    : {bw[0]} — in {bw[1]*100:.0f}% of the time, "
              f"{bw[2]:,} trades, {bw[3]*100:+.4f}% each, worst {bw[5]*100:+.1f}%")
