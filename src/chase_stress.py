"""
CHASE, STRESS-TESTED THE RIGHT WAY ROUND.

chase_adverse.py got the sign wrong and its own diagnostic caught it. It
proxied "selling pressure" as how far below the rung the bar's low travelled,
and returns IMPROVED as that penalty was tightened. The reason is obvious in
hindsight: inside a 15-minute bar, a deep wick below your level is usually a
wick that recovered. It measures mean reversion, which is the trade this book
exists to take. The model was preferentially filling the WINNERS and calling
it a punishment.

Adverse selection is a statement about what happens AFTER the fill, not
within the bar that caused it. So it cannot be built from a causal proxy -
not honestly, anyway, because any such proxy is a forecast of the future and
if one worked it would be an entry signal in its own right.

SO THIS IS A STRESS TEST, NOT A MODEL, and the distinction matters. It uses
lookahead ON PURPOSE: the fill probability is set by what the trade went on
to do. That is illegal in a backtest and legitimate in a sensitivity analysis,
because the question is not "what would chase have earned" but "how much
adverse selection would it take to make chase not worth using". A result that
survives the harshest setting is safe whatever the truth turns out to be.

    trades that went on to BREAK      fill with probability p_bad
    trades that went on to RECOVER    fill with probability p_good

swept from no bias (both equal, chase.py's assumption) to extreme (breakdowns
fill nearly always, recoveries rarely). The honest reading is the breakeven
point: the degree of adverse selection at which chase stops beating the
static queued ladder. If that point is implausibly severe, chase is worth
using; if it is mild, it is not.
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


def episodes(d, allow, ema, lo_b, hi_b, a, Dep, mode, p_good, p_bad):
    """One pass. `mode` picks the fill rule; for 'chase' the fill probability
    depends on how the episode ENDS, which is deliberate lookahead."""
    C, H, L = d.close.values, d.high.values, d.low.values
    vol = d.volume.values*C
    n = len(C)
    # First pass: find where each episode would end under a full-fill book,
    # so the outcome is known before deciding the fill. Lookahead by design.
    fate = np.zeros(n, dtype=np.int8)      # +1 recovered, -1 broke
    inv = []; oi = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            fate[oi] = -1 if broke else 1
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv: fate[oi] = 1; sold = set()
        held = sum(x for _, x in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: oi = i
    # Second pass: the book, with fills set by that known fate
    out = []; inv = []; oi = 0; sold = set(); cur = 0
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
            if mode == "queued" and Dep is not None:
                sel = Dep.loc[:d.index[i]]
                if len(sel): drow = sel.iloc[-1]
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if not (L[i] < p and held+frac <= 1.0+1e-9): continue
                if mode == "queued":
                    f, px = 0.0, p
                    if drow is not None:
                        pct = abs(p/C[i]-1)*100
                        q = q_ahead(drow, max(pct, 0.05))
                        rng = max(H[i]-L[i], 1e-12)
                        arr = vol[i]*min(max((p-L[i])/rng, 0.0), 1.0)
                        f = 0.0 if not np.isfinite(q) else \
                            float(min(max(arr-q, 0.0)/ORDER, 1.0))
                else:
                    if not inv: cur = i
                    bad = fate[cur] == -1
                    f = p_bad if bad else p_good
                    px = p + PREM*a[i]
                if f <= 0.001: continue
                inv.append((px, frac*f)); held += frac*f
                if len(inv) == 1: oi = i; cur = i
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
    print(f"{len(common)} symbols. Chase premium 0.05 ATR.")
    print("LOOKAHEAD USED ON PURPOSE: the fill rate is set by how the trade ends.")
    print("This is a sensitivity analysis, not a tradeable result.\n")
    print(f"  {'fill bias':<46}{'deployed':>10}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'total P&L':>12}")
    res = []
    for s in common:
        d, al, ema, lo_b, hi_b, a = P[s]
        res += episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), "queued", 0, 0)
    R = pd.DataFrame(res, columns=["ret", "size"])
    base_total = R.ret.sum()
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    print(f"  {'static ladder, real queue — the bar to beat':<46}"
          f"{R['size'].mean()*100:>9.0f}%{R.ret.mean()*100:>+11.4f}%{t:>+8.2f}"
          f"{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
          f"{R.ret.sum()*100:>+11.0f}%")
    rows = []
    for pg, pb, lbl in ((0.92, 0.92, "no bias — recover 92%, break 92%"),
                        (0.80, 0.95, "mild — recover 80%, break 95%"),
                        (0.60, 0.98, "moderate — recover 60%, break 98%"),
                        (0.40, 0.98, "severe — recover 40%, break 98%"),
                        (0.20, 0.98, "extreme — recover 20%, break 98%"),
                        (0.10, 0.98, "absurd — recover 10%, break 98%")):
        res = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            res += episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), "chase", pg, pb)
        if len(res) < 200: continue
        R = pd.DataFrame(res, columns=["ret", "size"])
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        beat = "yes" if R.ret.sum() > base_total else "NO"
        rows.append((lbl, R.ret.sum(), beat))
        print(f"  {lbl:<46}{R['size'].mean()*100:>9.0f}%{R.ret.mean()*100:>+11.4f}%"
              f"{t:>+8.2f}{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
              f"{R.ret.sum()*100:>+11.0f}%   beats static: {beat}")
    print("\n  Now the worst-case column SHOULD deteriorate as the bias tightens.")
    print("  If it still does not, the stress test is broken too.")
    fails = [r for r in rows if r[2] == "NO"]
    if not fails:
        print("\n  Chase beats the static queued ladder even at the absurd setting,")
        print("  where nine in ten good trades are missed and almost every")
        print("  breakdown is caught. That is a robust result.")
    else:
        print(f"\n  Chase stops beating the static ladder at: {fails[0][0]}")
        print("  Judge whether real markets are that adversely selected.")
