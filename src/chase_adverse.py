"""
CHASE, WITH THE ADVERSE SELECTION IT ACTUALLY SUFFERS.

chase.py let a chase order fill 92% of the time regardless of what the trade
went on to do, and then reported that it recovers 94% of the edge the queue
destroyed. That result is not trustworthy and the tell was in its own output:
the worst-case trade barely moved, -11.2% to -11.5%. A chase order that
really filled more often on breakdowns would have a visibly worse tail. Mine
did not, because the model never let the fill rate depend on the thing that
makes chasing dangerous.

WHY CHASING IS ADVERSELY SELECTED. The order re-prices to sit one tick inside
the best bid and follows it down. It therefore fills FASTEST when the bid is
collapsing - heavy sell pressure sweeping through the level - and SLOWEST when
price drifts down gently and bounces, which is the trade the book wants. So
the fills it adds, relative to a static bid, are not a random sample of the
trades it was missing. They are weighted toward the ones that kept going.

A static resting bid's low fill rate is therefore partly protective: the
trades it fails to catch are disproportionately the ones that would have lost.
Any honest model of chase has to pay that back.

THE MODEL. Fill probability scales with how hard price is pushing through the
level on that bar, measured as the bar's downward travel below the rung in
ATR. A gentle touch fills partially; a violent sweep fills in full.

    push   = (rung price - bar low) / ATR
    p_fill = clip(BASE + SLOPE*push, 0, 0.98)

With BASE low and SLOPE positive, the order fills most reliably exactly when
the move is strongest - which is the behaviour that makes chasing costly, and
is the mechanism chase.py left out. Entry price still carries the premium.

SWEPT because the slope is the whole question: at slope 0 this collapses back
to chase.py's flat assumption, and at a high slope the order is essentially
only filled by sweeps. The honest answer is somewhere in between and the sweep
shows how much it matters.
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


def run(d, allow, ema, lo_b, hi_b, a, Dep, mode, prem, base, slope):
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
                if mode == "queued" or (mode == "hybrid" and k > 0):
                    f, px = 0.0, p
                    if drow is not None:
                        pct = abs(p/C[i]-1)*100
                        q = q_ahead(drow, max(pct, 0.05))
                        rng = max(H[i]-L[i], 1e-12)
                        arr = vol[i]*min(max((p-L[i])/rng, 0.0), 1.0)
                        f = 0.0 if not np.isfinite(q) else \
                            float(min(max(arr-q, 0.0)/ORDER, 1.0))
                else:
                    # ADVERSE SELECTION: fills in proportion to how hard price
                    # is driving through the level on this bar
                    push = max(p-L[i], 0.0)/a[i]
                    f = float(np.clip(base + slope*push, 0.0, 0.98))
                    px = p + prem*a[i]
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
    print(f"{len(common)} symbols with depth. Chase premium fixed at 0.05 ATR —")
    print("one tick inside the best bid, which on a liquid alt is a small")
    print("fraction of an ATR. The SLOPE is what is being tested.\n")
    print(f"  {'fill model':<44}{'deployed':>10}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'total P&L':>12}")
    res = []
    for s in common:
        d, al, ema, lo_b, hi_b, a = P[s]
        res += run(d, al, ema, lo_b, hi_b, a, depth.get(s), "queued", 0, 0, 0)
    R = pd.DataFrame(res, columns=["ret", "size"])
    qt = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    print(f"  {'static ladder, real queue (doc 116)':<44}{R['size'].mean()*100:>9.0f}%"
          f"{R.ret.mean()*100:>+11.4f}%{qt:>+8.2f}{(R.ret>0).mean()*100:>5.0f}%"
          f"{R.ret.min()*100:>+8.1f}%{R.ret.sum()*100:>+11.0f}%")
    qsum = R.ret.sum()
    for base, slope, lbl in ((0.92, 0.00, "chase, flat 92% (chase.py — too kind)"),
                             (0.60, 0.40, "chase, mildly adverse"),
                             (0.35, 0.80, "chase, moderately adverse"),
                             (0.15, 1.20, "chase, strongly adverse"),
                             (0.05, 1.60, "chase, only swept levels fill")):
        res = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            res += run(d, al, ema, lo_b, hi_b, a, depth.get(s), "chase",
                       0.05, base, slope)
        if len(res) < 200: continue
        R = pd.DataFrame(res, columns=["ret", "size"])
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        print(f"  {lbl:<44}{R['size'].mean()*100:>9.0f}%{R.ret.mean()*100:>+11.4f}%"
              f"{t:>+8.2f}{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
              f"{R.ret.sum()*100:>+11.0f}%")
    print("\n  The worst-case column is the diagnostic. If it does not deteriorate")
    print("  as the slope rises, the adverse selection is still not being modelled.")
    print(f"  Static queued total was {qsum*100:+.0f}% — chase has to beat that")
    print("  under the HARSHEST assumption to be worth using, not the kindest.")
