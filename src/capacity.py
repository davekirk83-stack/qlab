"""
THE CAPACITY CEILING — how big can this book get before the market stops
absorbing it?

Doc 113 produced a 283,053% CAGR at 3x, turning $2,000 into $9.5m in about a
year. That is not an edge, it is a missing constraint. At $2,000 each position
is a $50 resting order and entirely realistic. At $9.5m each position is a
$237,000 limit order resting on the bid of a small altcoin, and the simulator
never asks whether anything like that much liquidity exists. Every result in
the record above a few thousand dollars is therefore unbounded above by
nothing at all.

This closes it using data_depth_full - 20 symbols, cumulative resting depth at
0.2/1/2/3/4/5% either side of mid, five-minute sampling, one year - which has
been sitting unused since the queue model was abandoned.

TWO SEPARATE LIMITS, because they bite at different sizes and the smaller one
governs:

  1. QUEUE POSITION. A resting bid joins the back of the queue at its price.
     Depth AHEAD of it must be eaten by sellers before any of it fills. The
     bigger the order, the longer the queue takes to clear past it, and the
     more often price rallies away leaving a partial fill or nothing. This
     degrades the FILL RATE.

  2. MARKET-IMPACT ON EXIT. The break exit sells at market into whatever is
     bid. A $50 market sell takes the touch. A $237,000 market sell walks the
     book down through several percent. This degrades the EXIT PRICE, and it
     does so precisely on the trades that were already the losers.

THE SWEEP. Stack from $2,000 to $10,000,000, 40 slots, 3x. For each, the
order size is equity/40 x 3, and both penalties are applied to the registered
two-sided book. Reported as the per-trade return after capacity, so the point
where the curve rolls over is the real ceiling on this strategy - and the
number that should govern every CAGR quoted from here on.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_PCTS = np.array([0.2, 1, 2, 3, 4, 5])
BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
SLOTS, LEV = 40, 3.0


def load_depth():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s = os.path.basename(p)[:-4]
        D = pd.read_csv(p)
        D.index = pd.to_datetime(D.ts, utc=True)
        # median depth profile per symbol: robust, and the book rests orders
        # across the whole year rather than at one moment
        prof = {}
        for c in BID_COLS:
            if c in D.columns:
                v = pd.to_numeric(D[c], errors="coerce").dropna()
                prof[c] = float(v.median()) if len(v) else np.nan
        if any(np.isfinite(list(prof.values()))):
            out[s] = prof
    return out


def depth_at(prof, pct):
    """Cumulative resting bid dollars between mid and pct% below it."""
    xs, ys = [], []
    for p, c in zip(BID_PCTS, BID_COLS):
        v = prof.get(c, np.nan)
        if np.isfinite(v): xs.append(p); ys.append(v)
    if len(xs) < 2: return np.nan
    xs, ys = np.array(xs), np.array(ys)
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    return float(np.interp(min(max(pct, xs[0]), xs[-1]), xs, ys))


def fill_fraction(order_usd, queue_usd, turnover_usd):
    """Share of the order that fills. The order sits behind `queue_usd` of
    resting bids; `turnover_usd` of selling arrives while the level is live.
    Conservative: back of the queue, no speed advantage."""
    if not np.isfinite(queue_usd) or order_usd <= 0: return 1.0
    avail = max(turnover_usd - queue_usd, 0.0)
    return float(min(avail/order_usd, 1.0))


def impact_bp(order_usd, prof, mid_ref=1.0):
    """How far a market sell of this size walks the book down, in basis
    points, read straight off the cumulative depth curve."""
    for p, c in zip(BID_PCTS, BID_COLS):
        d = prof.get(c, np.nan)
        if np.isfinite(d) and d >= order_usd:
            return float(p*100.0)          # percent -> bp
    return 500.0                            # beyond the deepest level measured


if __name__ == "__main__":
    depth = load_depth()
    data = RD.load()
    common = [s for s in data if s in depth]
    print(f"{len(depth)} symbols with order-book depth, {len(common)} of them "
          f"also in the range-book panel.\n")

    # typical depth, to show what the constraint actually is
    print("TYPICAL RESTING BID DEPTH (median over the year, dollars)")
    print(f"  {'symbol':<12}{'within 0.2%':>14}{'within 1%':>13}{'within 2%':>13}"
          f"{'within 5%':>13}")
    for s in sorted(common)[:8]:
        p = depth[s]
        print(f"  {s:<12}{p.get('d-0.2',float('nan')):>14,.0f}"
              f"{p.get('d-1',float('nan')):>13,.0f}{p.get('d-2',float('nan')):>13,.0f}"
              f"{p.get('d-5',float('nan')):>13,.0f}")

    # build the trade set once, on the symbols that have depth
    trades = []
    for s in common:
        d = data[s]
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        allow = (v > v.expanding(500).median()).values
        C, H, L = d.close.values, d.high.values, d.low.values
        vol = d.volume.values * C
        n = len(C); inv = []; oi = 0; sold = set()
        for i in range(250, n-1):
            if not np.isfinite(a[i]) or a[i] <= 0: continue
            ok = bool(allow[i]) if np.isfinite(allow[i]) else False
            broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
            if inv and (i-oi >= CAP or broke or not ok):
                sz = sum(x for _, x in inv); cost = sum(p*x for p, x in inv)/sz
                trades.append((s, cost, L[i], True,
                               float(np.nanmean(vol[max(i-12,0):i+1]))))
                inv = []; sold = set(); continue
            if not ok: continue
            if inv:
                for k, (frac, lvl) in enumerate(ASK):
                    if k in sold: continue
                    tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                    if H[i] >= tgt and inv:
                        sz = sum(x for _, x in inv)
                        cost = sum(p*x for p, x in inv)/sz
                        trades.append((s, cost, tgt, False,
                                       float(np.nanmean(vol[max(i-12,0):i+1]))))
                        sold.add(k)
                        inv = [(p, x*(1-frac)) for p, x in inv]
                        inv = [(p, x) for p, x in inv if x > 1e-9]
                        if not inv: sold = set()
            held = sum(x for _, x in inv)
            if held < 1.0:
                for frac, off in BID:
                    p = lo_b[i]+off*a[i]
                    if L[i] < p and held+frac <= 1.0+1e-9:
                        inv.append((p, frac)); held += frac
                        if len(inv) == 1: oi = i
    T = pd.DataFrame(trades, columns=["sym", "cost", "exit", "is_break", "turnover"])
    T = T[np.isfinite(T.cost) & np.isfinite(T.exit) & (T.cost > 0)]
    print(f"\n{len(T):,} exits on the depth-covered symbols.\n")

    print("="*96)
    print("CAPACITY SWEEP — 40 slots, 3x. Order size = equity / 40 x 3.")
    print("="*96)
    print(f"  {'stack':>12}{'order size':>13}{'fill rate':>11}{'exit impact':>13}"
          f"{'per trade':>12}{'vs tiny':>10}")
    base = None
    for stack in (2_000, 10_000, 50_000, 250_000, 1_000_000, 5_000_000, 10_000_000):
        order = stack/SLOTS*LEV
        fills, rets = [], []
        for _, r in T.iterrows():
            prof = depth[r["sym"]]
            q = depth_at(prof, 0.5)                 # queue ahead at the band
            f = fill_fraction(order, q, r["turnover"])
            if f <= 0.01: fills.append(0.0); continue
            fills.append(f)
            imp = impact_bp(order, prof)/10000.0 if r["is_break"] else 0.0
            px = r["exit"]*(1-imp)
            cost_side = MK
            out_side = (SLIP+TAKER) if r["is_break"] else MK
            rets.append(((px*(1-out_side))/(r["cost"]*(1+cost_side))-1)*f)
        if not rets: continue
        m = float(np.mean(rets)); fr = float(np.mean(fills))
        imps = [impact_bp(order, depth[s])for s in T.sym.unique()]
        if base is None: base = m
        print(f"  ${stack:>11,}{order:>13,.0f}{fr*100:>10.0f}%"
              f"{np.mean(imps):>12.0f}bp{m*100:>+11.4f}%{m/base*100:>9.0f}%")
    print("\n  'fill rate' is the share of each resting order that actually gets")
    print("  filled once it has to wait behind the existing queue. 'exit impact'")
    print("  is how far a market sell of that size walks the book down. The point")
    print("  where 'vs tiny' rolls over is the real ceiling on this strategy.")
