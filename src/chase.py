"""
THE CHASE ORDER — does fixing the fill rate cost more than it buys?

Doc 118 found Hyperliquid's CHASE order: a post-only limit that automatically
re-prices to sit one tick inside the best bid and keeps following it until it
fills. Doc 116 found our resting bids fill only 38% of the time. Chase exists
to solve exactly that, so the obvious move is to use it.

The obvious move is not free, and the cost is structural rather than a fee.

A STATIC LADDER gets its edge from WHERE it fills, not whether. Rung 4 sits
0.55 ATR below the band and fills rarely - but when it does, it fills at a
genuinely good price, and doc 116 showed those deep rungs are precisely the
ones a queue denies us. A CHASE order inverts that: it follows the bid down
and fills near the touch, early in the descent, at the SHALLOW end. So it
converts a cheap, rare fill into an expensive, reliable one.

Worse, it is adversely selected by construction. A chase order fills fastest
when price is moving down hard through it - which is the move that does not
come back. The static bid's low fill rate is partly a feature: the trades it
misses are disproportionately the ones that kept going.

SO THE TEST IS NOT "does chase fill more", which is certain, but whether
deployment x price beats the static ladder once both are priced honestly.

  static optimistic   rests at the rung price, always fills            (fantasy)
  static queued       rests at the rung price, queue-limited           (doc 116)
  chase               fills with high probability, at a premium above
                      the rung, swept from 0.05 to 0.40 ATR, and
                      adversely selected: the premium is charged in
                      full on trades that go on to break
  hybrid              chase the first rung only, static ladder beneath -
                      guarantees a position while keeping the deep rungs
                      cheap

Worst-tick break fills and the containment switch throughout.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_PCTS = np.array([0.2, 1, 2, 3, 4, 5])
BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
ORDER = 150.0


def load_depth():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s = os.path.basename(p)[:-4]
        D = pd.read_csv(p)
        D.index = pd.to_datetime(D.ts, utc=True)
        keep = [c for c in BID_COLS if c in D.columns]
        if keep: out[s] = D[keep].apply(pd.to_numeric, errors="coerce")
    return out


def q_ahead(row, pct):
    xs, ys = [], []
    for p, c in zip(BID_PCTS, BID_COLS):
        if c in row.index and np.isfinite(row[c]): xs.append(p); ys.append(row[c])
    if len(xs) < 2: return np.nan
    xs, ys = np.array(xs), np.array(ys)
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    return float(np.interp(min(max(pct, xs[0]), xs[-1]), xs, ys))


def run(d, allow, ema, lo_b, hi_b, a, Dep, mode, prem=0.0):
    """mode: optimistic | queued | chase | hybrid"""
    C, H, L = d.close.values, d.high.values, d.low.values
    vol = d.volume.values*C
    n = len(C); out = []; inv = []; oi = 0; sold = set()
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
            if mode in ("queued", "hybrid") and Dep is not None:
                sel = Dep.loc[:d.index[i]]
                if len(sel): drow = sel.iloc[-1]
            for k, (frac, off) in enumerate(BID):
                p = lo_b[i]+off*a[i]
                if not (L[i] < p and held+frac <= 1.0+1e-9): continue
                # --- how this rung fills, by mode ---
                if mode == "optimistic":
                    f, px = 1.0, p
                elif mode == "queued":
                    f, px = 0.0, p
                    if drow is not None:
                        pct = abs(p/C[i]-1)*100
                        q = q_ahead(drow, max(pct, 0.05))
                        rng = max(H[i]-L[i], 1e-12)
                        arr = vol[i]*min(max((p-L[i])/rng, 0.0), 1.0)
                        f = 0.0 if not np.isfinite(q) else \
                            float(min(max(arr-q, 0.0)/ORDER, 1.0))
                elif mode == "chase":
                    # chases the bid down: fills reliably, but near the touch
                    # and therefore ABOVE the rung it was aiming at
                    f, px = 0.92, p + prem*a[i]
                else:   # hybrid: rung 1 chased, the rest rest statically
                    if k == 0:
                        f, px = 0.92, p + prem*a[i]
                    else:
                        f, px = 0.0, p
                        if drow is not None:
                            pct = abs(p/C[i]-1)*100
                            q = q_ahead(drow, max(pct, 0.05))
                            rng = max(H[i]-L[i], 1e-12)
                            arr = vol[i]*min(max((p-L[i])/rng, 0.0), 1.0)
                            f = 0.0 if not np.isfinite(q) else \
                                float(min(max(arr-q, 0.0)/ORDER, 1.0))
                if f <= 0.001: continue
                inv.append((px, frac*f)); held += frac*f
                if len(inv) == 1: oi = i
    return out


if __name__ == "__main__":
    depth = load_depth()
    data = RD.load()
    common = sorted([s for s in data if s in depth])
    P = {}
    for s in common:
        d = data[s]
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        P[s] = (d, (v > v.expanding(500).median()).values, ema, lo_b, hi_b, a)
    print(f"{len(common)} symbols with depth. ${ORDER:.0f} orders.\n")
    print("Chase fills reliably but near the touch, so it converts a cheap rare")
    print("fill into an expensive reliable one. The premium is what it costs.\n")
    print(f"  {'entry method':<38}{'trades':>8}{'deployed':>10}{'per trade':>12}"
          f"{'t':>8}{'win':>6}{'worst':>9}{'total P&L':>12}")
    CFG = [("optimistic", 0.0, "static ladder, always fills (fantasy)"),
           ("queued",     0.0, "static ladder, real queue (doc 116)")]
    for pr in (0.05, 0.10, 0.20, 0.40):
        CFG.append(("chase", pr, f"chase all rungs, +{pr:.2f} ATR premium"))
    for pr in (0.05, 0.10, 0.20):
        CFG.append(("hybrid", pr, f"chase rung 1 (+{pr:.2f}), ladder beneath"))
    best = None
    for mode, pr, lbl in CFG:
        res = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            res += run(d, al, ema, lo_b, hi_b, a, depth.get(s), mode, pr)
        if len(res) < 200: continue
        R = pd.DataFrame(res, columns=["ret", "size"])
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        print(f"  {lbl:<38}{len(R):>8}{R['size'].mean()*100:>9.0f}%"
              f"{R.ret.mean()*100:>+11.4f}%{t:>+8.2f}{(R.ret>0).mean()*100:>5.0f}%"
              f"{R.ret.min()*100:>+8.1f}%{R.ret.sum()*100:>+11.0f}%")
        if mode != "optimistic" and (best is None or R.ret.sum() > best[1]):
            best = (lbl, R.ret.sum(), R.ret.mean(), len(R))
    print("\n  'deployed' is the average size actually on at exit. The static")
    print("  ladder's low number is its problem; chase fixes that and pays for")
    print("  it in entry price. Total P&L is the column that settles it.")
    if best:
        print(f"\n  BEST REALISTIC: {best[0]} — {best[3]:,} trades, "
              f"{best[2]*100:+.4f}% each, total {best[1]*100:+.0f}%")
