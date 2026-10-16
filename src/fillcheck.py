"""
THE ASSUMPTION THAT FLATTERS EVERYTHING — do the resting orders actually fill?

Doc 114 found a fill rate near 60% at a $150 order, where size moves nothing.
If that is right it is the largest unverified assumption in the record, because
EVERY maker result registered so far - the range book, the intraday book, the
laddering work - assumes a resting bid fills whenever the bar's low trades
through it. That is 100%, and it is free insurance the backtest has been
handing out 28,326 times.

This runs the registered book twice over the SAME trades and prints the gap.

  OPTIMISTIC   a resting bid fills in full the moment the low touches it.
               What every result in the record assumes.
  QUEUED       the bid joins the BACK of the queue at its price. Resting
               depth ahead of it must be consumed by arriving sell flow
               before any of the order fills; it is filled pro rata as the
               queue clears, and if price rallies away first it keeps only
               the partial fill it got.

WHAT A PARTIAL FILL ACTUALLY MEANS, and it is not simply a smaller profit.
It changes the LADDER's shape. The outer rungs sit deepest and fill least
often, so under a real queue the book ends up holding more of its inventory
at the shallow, worse prices and less at the deep, good ones. The average
entry gets worse at the same time as the size gets smaller. Doc 65 could not
see this because it handed every rung a guaranteed fill.

REPORTED
  the fill rate per rung, so it is visible which end of the ladder suffers
  deployment - what share of intended size actually got on
  per-trade return on the capital actually deployed
  and the honest total: return x deployment, which is what the stack earns
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_PCTS = np.array([0.2, 1, 2, 3, 4, 5])
BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
ORDER = 150.0          # $2,000 stack, 40 slots, 3x


def load_depth():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s = os.path.basename(p)[:-4]
        D = pd.read_csv(p)
        D.index = pd.to_datetime(D.ts, utc=True)
        keep = [c for c in BID_COLS if c in D.columns]
        if keep: out[s] = D[keep].apply(pd.to_numeric, errors="coerce")
    return out


def queue_ahead(row, pct):
    xs, ys = [], []
    for p, c in zip(BID_PCTS, BID_COLS):
        if c in row.index and np.isfinite(row[c]): xs.append(p); ys.append(row[c])
    if len(xs) < 2: return np.nan
    xs, ys = np.array(xs), np.array(ys)
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    return float(np.interp(min(max(pct, xs[0]), xs[-1]), xs, ys))


def run(d, allow, ema, lo_b, hi_b, a, Dep, queued):
    C, H, L = d.close.values, d.high.values, d.low.values
    vol = d.volume.values*C
    n = len(C); out = []; inv = []; oi = 0; sold = set()
    rung_tries = np.zeros(len(BID)); rung_fills = np.zeros(len(BID))
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            sz = sum(x for _, x in inv); cost = sum(p*x for p, x in inv)/sz
            out.append(((L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, sz))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    cost = sum(p*x for p, x in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), sell))
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv: sold = set()
        held = sum(x for _, x in inv)
        if held < 1.0:
            drow = None
            if queued and Dep is not None:
                sel = Dep.loc[:d.index[i]]
                if len(sel): drow = sel.iloc[-1]
            for k, (frac, off) in enumerate(BID):
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    rung_tries[k] += 1
                    f = 1.0
                    if queued and drow is not None:
                        pct = abs(p/C[i]-1)*100
                        q = queue_ahead(drow, max(pct, 0.05))
                        # sell flow reaching this level during the bar,
                        # apportioned by how much of the bar's range sat below it
                        rng = max(H[i]-L[i], 1e-12)
                        share = min(max((p-L[i])/rng, 0.0), 1.0)
                        arriving = vol[i]*share
                        f = 0.0 if not np.isfinite(q) else \
                            float(min(max(arriving-q, 0.0)/ORDER, 1.0))
                    if f <= 0.001: continue
                    rung_fills[k] += f
                    inv.append((p, frac*f)); held += frac*f
                    if len(inv) == 1: oi = i
    return out, rung_tries, rung_fills


if __name__ == "__main__":
    depth = load_depth()
    data = RD.load()
    common = sorted([s for s in data if s in depth])
    print(f"{len(common)} symbols with both 15-minute bars and order-book depth.")
    print(f"Order size ${ORDER:.0f} — a $2,000 stack at 40 slots and 3x, so size")
    print(f"itself moves nothing. Any shortfall is pure queue position.\n")

    for queued, lbl in ((False, "OPTIMISTIC — fills whenever the low touches"),
                        (True,  "QUEUED — joins the back of the book")):
        res = []; T = np.zeros(len(BID)); F = np.zeros(len(BID))
        for s in common:
            d = data[s]
            D, ema, lo_b, hi_b, a = RD.detectors(d)
            v = pd.Series(D["contain"])
            al = (v > v.expanding(500).median()).values
            o, t, f = run(d, al, ema, lo_b, hi_b, a, depth.get(s), queued)
            res += o; T += t; F += f
        if not res: continue
        R = pd.DataFrame(res, columns=["ret", "size"])
        dep = float(F.sum()/max(T.sum(), 1))
        tt = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        print(f"{lbl}")
        print(f"  trades {len(R):,}   per trade {R.ret.mean()*100:+.4f}%   "
              f"t {tt:+.2f}   win {(R.ret>0).mean()*100:.0f}%   "
              f"worst {R.ret.min()*100:+.1f}%")
        print(f"  overall fill rate {dep*100:.0f}%   "
              f"total P&L {R.ret.sum()*100:+.0f}%")
        print(f"  fill rate by rung (rung 1 is nearest the band, rung 4 deepest):")
        for k in range(len(BID)):
            fr = F[k]/T[k] if T[k] > 0 else np.nan
            print(f"     rung {k+1}  offset {BID[k][1]:+.2f} ATR   "
                  f"touched {int(T[k]):>6,}   filled {fr*100:>5.1f}%")
        print()
    print("  If the deep rungs fill materially less often than the shallow ones,")
    print("  a real queue does not just shrink the position — it shifts the")
    print("  ladder's weight toward the worse prices, which doc 65 could not see.")
