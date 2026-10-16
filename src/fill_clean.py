"""
THE FILL COMPARISON, REBUILT — size-weighted, with the ladder bug removed.

Three attempts at this question produced three wrong answers, and the
diagnostic built into each one caught the next. Worth stating the defects
plainly because they invalidate doc 116's magnitude as well as the chase work:

  1. RETURNS WERE NOT SIZE-WEIGHTED. The per-trade mean counted a trade that
     filled 10% of its intended size exactly as heavily as one that filled in
     full. Deployment was reported in its own column and then ignored by every
     number next to it. Comparing fill regimes on that mean is meaningless,
     because the whole difference between regimes IS size.

  2. THE LADDER REWARDED BAD FILLS. The rung loop kept adding until held size
     reached 100%. With partial fills, more rungs were consumed to get there -
     so a poor fill rate bought a DEEPER, BETTER average entry. That is why
     every attempt to penalise chasing made it look better: the penalty was
     being paid back as a cheaper position. In reality a rung you cannot fill
     is size you never get, not a discount on the size you do.

  3. Consequently the worst-case column never moved. It was a per-unit return
     on an average cost that barely changed, so it could not respond to
     anything. It sat at -11.3% through every setting and said so.

THE REBUILD
  each rung is attempted ONCE per episode, filled or not
  unfilled size is lost, never redistributed to a deeper rung
  every return is weighted by the size actually on
  the headline is RETURN ON INTENDED CAPITAL - what the stack earns, which
  is the only number that compares regimes fairly, since it charges a book
  for the capital it failed to deploy as well as the trades it lost on

REGIMES
  optimistic   every touched rung fills in full          (what the record assumes)
  queued       fills as the resting queue allows         (doc 116, rebuilt)
  chase        high fill, entry 0.05 ATR worse           (Hyperliquid CHASE)
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_PCTS = np.array([0.2, 1, 2, 3, 4, 5])
BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
ORDER, PREM = 150.0, 0.05


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


def run(d, allow, ema, lo_b, hi_b, a, Dep, mode, chase_fill=0.92):
    """Returns one row per EPISODE: (pnl_on_intended_capital, deployed)."""
    C, H, L = d.close.values, d.high.values, d.low.values
    vol = d.volume.values*C
    n = len(C)
    out = []
    inv = []            # (price, size) actually filled
    tried = set()       # rungs already ATTEMPTED this episode — once only
    intended = 0.0      # size we meant to have on
    realised = 0.0      # weighted P&L booked so far this episode
    oi = 0; sold = set()

    def close_episode(px_out, taker):
        nonlocal inv, tried, intended, realised, sold
        if inv:
            sz = sum(x for _, x in inv)
            cost = sum(p*x for p, x in inv)/sz
            out_side = (SLIP+TAKER) if taker else MK
            realised += ((px_out*(1-out_side))/(cost*(1+MK))-1)*sz
        if intended > 0:
            out.append((realised/intended, sum(x for _, x in inv)))
        inv = []; tried = set(); intended = 0.0; realised = 0.0; sold = set()

    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if intended > 0 and (i-oi >= CAP or broke or not ok):
            close_episode(L[i], True); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    cost = sum(p*x for p, x in inv)/sz
                    realised += ((tgt*(1-MK))/(cost*(1+MK))-1)*sell
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv:
                        out.append((realised/intended, 0.0)) if intended > 0 else None
                        tried = set(); intended = 0.0; realised = 0.0; sold = set()
                        break
        drow = None
        if mode == "queued" and Dep is not None:
            sel = Dep.loc[:d.index[i]]
            if len(sel): drow = sel.iloc[-1]
        for k, (frac, off) in enumerate(BID):
            if k in tried: continue                 # ONE attempt per rung
            p = lo_b[i]+off*a[i]
            if L[i] >= p: continue
            tried.add(k)
            intended += frac                        # we meant to have this on
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
            else:
                f, px = chase_fill, p + PREM*a[i]
            if f > 0.001:
                inv.append((px, frac*f))
                if len(inv) == 1: oi = i
            elif len(inv) == 0 and intended == frac:
                oi = i                              # episode opened, nothing on
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
    print(f"{len(common)} symbols, ${ORDER:.0f} orders. Each rung attempted once;")
    print("unfilled size is LOST, not pushed into a deeper rung. Returns are on")
    print("INTENDED capital, so a book is charged for what it failed to deploy.\n")
    print(f"  {'regime':<40}{'episodes':>10}{'deployed':>10}{'per episode':>14}"
          f"{'t':>8}{'win':>6}{'worst':>9}{'total':>11}")
    store = {}
    for mode, lbl in (("optimistic", "every touched rung fills (assumed)"),
                      ("queued",     "resting queue (honest)"),
                      ("chase",      "Hyperliquid CHASE, +0.05 ATR")):
        res = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            res += run(d, al, ema, lo_b, hi_b, a, depth.get(s), mode)
        if len(res) < 100: continue
        R = pd.DataFrame(res, columns=["ret", "dep"])
        R = R[np.isfinite(R.ret)]
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        store[mode] = R
        print(f"  {lbl:<40}{len(R):>10,}{R.dep.mean()*100:>9.0f}%"
              f"{R.ret.mean()*100:>+13.4f}%{t:>+8.2f}{(R.ret>0).mean()*100:>5.0f}%"
              f"{R.ret.min()*100:>+8.1f}%{R.ret.sum()*100:>+10.0f}%")
    if "optimistic" in store and "queued" in store:
        o, q = store["optimistic"].ret.mean(), store["queued"].ret.mean()
        print(f"\n  The fill assumption is worth {(o-q)*100:+.4f}% per episode "
              f"({(1-q/o)*100 if o else 0:.0f}% of the optimistic result).")
    if "chase" in store and "queued" in store:
        c, q = store["chase"].ret.mean(), store["queued"].ret.mean()
        o = store["optimistic"].ret.mean()
        print(f"  CHASE recovers {(c-q)/(o-q)*100 if o != q else 0:.0f}% of that gap, "
              f"at a 0.05 ATR worse entry on every rung.")
    print("\n  Worst-case should now differ between regimes. If it still does not,")
    print("  the accounting is still wrong and nothing here should be registered.")
