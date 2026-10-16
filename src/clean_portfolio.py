"""
THE PORTFOLIO, REBUILT ON HONEST ACCOUNTING — what a small edge is worth.

DK: "Regular small gains are absolutely fine."

That is the right bar, and it changes what this test is for. The question is
no longer whether the book produces a large number - doc 119 established it
does not - but whether a small, real edge, compounded across 40 slots turning
over regularly, amounts to anything at a $2,000 stack.

THE BUG THIS FIXES. Doc 113 reported Sharpe 13.80 for the two-sided book.
It was built by treating EACH PARTIAL SALE as its own position consuming its
own slot - which is precisely the defect identified weeks ago in
rm_portfolio.py, where it produced a Sharpe of 14.88. The fix was never
carried into the new code and the bug came back in a new file. Here, one
EPISODE is one position: it opens when the first rung fills, holds whatever
inventory the ladder accumulated, books its scale-outs internally, and
releases its slot once flat.

ALSO FIXED, per doc 119: returns are weighted by size actually filled, each
rung is attempted once, and unfilled size is lost rather than redistributed
into a deeper, cheaper rung.

RUN UNDER BOTH FILL REGIMES, because doc 119 showed the choice of order type
is now the difference between a loss and a gain:
  optimistic   every touched rung fills            - the old assumption
  queued       resting bids wait their turn        - the pessimistic extreme
  chase        Hyperliquid CHASE, 0.05 ATR worse   - the realistic plan

and both sides, since doc 110 found shorts carry their own edge.

REPORTED AT $2,000, the actual stack, with CAGR, max drawdown, Sharpe and -
the number that matters for a small edge - how much $2,000 becomes.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_PCTS = np.array([0.2, 1, 2, 3, 4, 5])
BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
ORDER, PREM, START = 150.0, 0.05, 2000.0


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


def fill_of(mode, p, i, C, H, L, vol, a, drow):
    if mode == "optimistic": return 1.0, p
    if mode == "chase":      return 0.92, p + PREM*a[i]
    f = 0.0
    if drow is not None:
        pct = abs(p/C[i]-1)*100
        q = q_ahead(drow, max(pct, 0.05))
        rng = max(H[i]-L[i], 1e-12)
        arr = vol[i]*min(max((p-L[i])/rng, 0.0), 1.0)
        f = 0.0 if not np.isfinite(q) else float(min(max(arr-q, 0.0)/ORDER, 1.0))
    return f, p


def episodes(d, allow, ema, lo_b, hi_b, a, Dep, mode, side, sym):
    """ONE ROW PER EPISODE: (sym, entry_ts, exit_ts, pnl_on_intended, side)."""
    C, H, L = d.close.values, d.high.values, d.low.values
    vol = d.volume.values*C
    n = len(C); out = []
    inv = []; tried = set(); intended = 0.0; realised = 0.0
    oi = None; sold = set()
    sgn = 1.0 if side == "L" else -1.0

    def shut(i, px_out, taker):
        nonlocal inv, tried, intended, realised, oi, sold
        if inv:
            sz = sum(x for _, x in inv)
            cost = sum(p*x for p, x in inv)/sz
            o_side = (SLIP+TAKER) if taker else MK
            r = ((px_out*(1-o_side))/(cost*(1+MK))-1) if side == "L" \
                else ((cost*(1-MK))/(px_out*(1+o_side))-1)
            realised += r*sz
        if intended > 0 and oi is not None:
            out.append((sym, d.index[oi], d.index[i], realised/intended, side))
        inv = []; tried = set(); intended = 0.0; realised = 0.0
        oi = None; sold = set()

    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = (C[i] < lo_b[i]-1.5*a[i]) or (C[i] > hi_b[i]+1.5*a[i])
        if oi is not None and (i-oi >= CAP or broke or not ok):
            shut(i, L[i] if side == "L" else H[i], True); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                if side == "L":
                    tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                    hit = H[i] >= tgt
                else:
                    tgt = ema[i] if lvl == "mid" else lo_b[i]-lvl*a[i]
                    hit = L[i] <= tgt
                if hit and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    cost = sum(p*x for p, x in inv)/sz
                    r = ((tgt*(1-MK))/(cost*(1+MK))-1) if side == "L" \
                        else ((cost*(1-MK))/(tgt*(1+MK))-1)
                    realised += r*sell
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv:
                        out.append((sym, d.index[oi], d.index[i],
                                    realised/intended, side))
                        tried = set(); intended = 0.0; realised = 0.0
                        oi = None; sold = set()
                        break
        drow = None
        if mode == "queued" and Dep is not None:
            sel = Dep.loc[:d.index[i]]
            if len(sel): drow = sel.iloc[-1]
        for k, (frac, off) in enumerate(BID):
            if k in tried: continue
            p = (lo_b[i]+off*a[i]) if side == "L" else (hi_b[i]-off*a[i])
            touched = (L[i] < p) if side == "L" else (H[i] > p)
            if not touched: continue
            tried.add(k); intended += frac
            if oi is None: oi = i
            f, px = fill_of(mode, p, i, C, H, L, vol, a, drow)
            if f > 0.001: inv.append((px, frac*f))
    return out


def simulate(S, slots, lev):
    """One position per episode. Slot held from first fill to flat."""
    S = S.sort_values("entry").reset_index(drop=True)
    eq = START; openp = []; curve = []; ei = 0; taken = 0; skipped = 0
    for t in sorted(set(S.entry) | set(S.exit)):
        still = []
        for p in openp:
            if p["exit"] <= t: eq += p["margin"]*p["ret"]*lev
            else: still.append(p)
        openp = still
        if eq <= 0: return None, taken, skipped
        while ei < len(S) and S.entry.iloc[ei] <= t:
            r = S.iloc[ei]; ei += 1
            if len(openp) >= slots: skipped += 1; continue
            openp.append({"exit": r["exit"], "ret": r["ret"], "margin": eq/slots})
            taken += 1
        curve.append((t, eq))
    if not curve: return None, taken, skipped
    E = pd.Series([c[1] for c in curve], index=[c[0] for c in curve])
    E = E[~E.index.duplicated(keep="last")]
    yrs = (E.index[-1]-E.index[0]).days/365.25
    if yrs <= 0 or E.iloc[-1] <= 0: return None, taken, skipped
    dly = E.resample("1D").last().ffill().pct_change().dropna()
    return {"cagr": (E.iloc[-1]/START)**(1/yrs)-1, "dd": (E/E.cummax()-1).min(),
            "sharpe": dly.mean()/dly.std()*np.sqrt(365) if dly.std() > 0 else np.nan,
            "final": E.iloc[-1], "yrs": yrs, "worst": dly.min()}, taken, skipped


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
    print(f"{len(common)} symbols (those with depth data). One position per")
    print(f"EPISODE, size-weighted, ${START:,.0f} stack, 40 slots.\n")
    print(f"  {'book':<40}{'taken':>8}{'skipped':>9}{'per ep':>10}{'CAGR':>9}"
          f"{'maxDD':>9}{'Sharpe':>8}{'final':>11}")
    for mode in ("optimistic", "queued", "chase"):
        rows = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            rows += episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), mode, "L", s)
            rows += episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), mode, "S", s)
        S = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"])
        S = S[np.isfinite(S.ret)]
        if len(S) < 100: continue
        for lev, tag in ((1, "1x"), (3, "3x")):
            r, tk, sk = simulate(S, 40, lev)
            lbl = f"{mode}, both sides, {tag}"
            if r is None:
                print(f"  {lbl:<40}{tk:>8,}{sk:>9,}  WIPED OUT"); continue
            print(f"  {lbl:<40}{tk:>8,}{sk:>9,}{S.ret.mean()*100:>+9.4f}%"
                  f"{r['cagr']*100:>8.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}"
                  f"{r['final']:>10,.0f}")
        # trades per month, the breadth number against DK's 50 target
        mths = (S.entry.max()-S.entry.min()).days/30.44
        print(f"       {len(S):,} episodes over {mths:.0f} months "
              f"= {len(S)/mths:.0f}/month of signal, {tk/mths:.0f}/month taken\n")
    print("  DK: 'regular small gains are absolutely fine.' The question is not")
    print("  whether these numbers are large but whether they are REAL and")
    print("  whether the drawdown is survivable at a $2,000 stack.")
