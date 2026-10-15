"""
STOP LOSSES ON THE RANGE BOOK — the thing we never specified.

DK: "I don't think we've talked about setting stop losses in this scenario."

We have not, and what the book has instead is weaker than a stop in two ways.
Its break exit tests the 15-MINUTE CLOSE against a level 1.5 ATR beyond the
band, so a move that spikes down and recovers inside the bar is invisible to
it; and when it does fire it sells at market, wherever that is. A stop is a
resting order at a known price, hit on any tick.

THE TENSION, stated before the numbers so the result cannot be dressed up
afterwards: this book buys the bottom of a range on purpose. A stop sits in
the same place the ladder is deliberately bidding. Too tight and it pays to
be taken out at precisely the price the strategy wanted filled, converting
the book's best entries into its losses. Too loose and it never fires. There
is no reason to assume a useful distance exists - that is what the sweep is
for.

WHERE TO PUT IT - four anchors, because for a laddered position "the stop" is
ambiguous in a way it never is for a single entry:
  cost    X ATR below the volume-weighted average cost of inventory held.
          Moves down as lower rungs fill, so a deeper ladder earns more room.
  rung    X ATR below the LOWEST rung price, filled or not. Fixed when the
          trade is planned and known in advance - the stop a human would set.
  band    X ATR below the lower Keltner band. Moves with the range itself.
  margin  a straight loss limit on posted margin at 3x: the account-level
          answer, ignoring where price is.

Triggered intrabar on the low, filled at the stop price plus slippage, which
is generous - a real stop in a fast market fills below. The break exit and
the 48-bar cap stay in place underneath, so the stop can only ever fire
EARLIER than the current book would have exited.

Judged on per-trade return, worst single trade, total P&L, and how often the
stop fires - because a stop that triggers on a third of trades in a strategy
whose whole premise is that price comes back is not insurance, it is a
different strategy.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
LEV = 3.0


def run(d, allow, ema, lo_b, hi_b, a, anchor, dist):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    out = []; inv = []; opened_i = 0; sold = set(); lowest = np.nan
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        # ---- stop check first: it is a resting order, it has priority ----
        if inv and anchor != "none":
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            if anchor == "cost":     stop = cost - dist*a[i]
            elif anchor == "rung":   stop = lowest - dist*a[i]
            elif anchor == "band":   stop = lo_b[i] - dist*a[i]
            else:                    stop = cost*(1 - dist/LEV)
            if L[i] <= stop:
                out.append(((stop*(1-SLIP-TAKER))/(cost*(1+MK))-1, "stop"))
                inv = []; sold = set(); continue
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append(((C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1,
                        "break" if broke else "exit"))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), "sold"))
                    sold.add(k)
                    inv = [(p, s*(1-sell/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: sold = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1:
                        opened_i = i
                        lowest = lo_b[i] + min(o for _, o in BID)*a[i]
    return out


if __name__ == "__main__":
    data = RD.load()
    P = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        P[s] = (d, (v > v.expanding(500).median()).values, ema, lo_b, hi_b, a)
    print(f"{len(data)} symbols, containment switch, 48-bar cap, 3x assumed.\n")
    print(f"  {'stop':<34}{'trades':>8}{'per trade':>12}{'t':>8}{'win':>6}"
          f"{'worst':>9}{'stopped':>9}{'total P&L':>12}{'worst @3x':>11}")
    base = None
    CONFIGS = [("none", 0, "no stop  (current book)")]
    for x in (0.5, 1.0, 1.5, 2.0, 3.0):
        CONFIGS.append(("cost", x, f"{x} ATR below average cost"))
    for x in (0.5, 1.0, 2.0):
        CONFIGS.append(("rung", x, f"{x} ATR below lowest rung"))
    for x in (1.0, 2.0, 3.0):
        CONFIGS.append(("band", x, f"{x} ATR below the band"))
    for x in (0.15, 0.25, 0.40):
        CONFIGS.append(("margin", x, f"{x*100:.0f}% of posted margin"))
    for anchor, dist, lbl in CONFIGS:
        res = []
        for s, (d, allow, ema, lo_b, hi_b, a) in P.items():
            res += run(d, allow, ema, lo_b, hi_b, a, anchor, dist)
        if len(res) < 200: continue
        R = pd.DataFrame(res, columns=["ret", "how"])
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        st = (R.how == "stop").mean()
        print(f"  {lbl:<34}{len(R):>8}{R.ret.mean()*100:>+11.4f}%{t:>+8.2f}"
              f"{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
              f"{st*100:>8.0f}%{R.ret.sum()*100:>+11.0f}%"
              f"{R.ret.min()*LEV*100:>+10.0f}%")
        if anchor == "none": base = R
    if base is not None:
        print(f"\n  Baseline: {base.ret.mean()*100:+.4f}% per trade, "
              f"worst {base.ret.min()*100:+.1f}% "
              f"({base.ret.min()*LEV*100:+.0f}% of margin at 3x).")
        print("  A stop earns its place by cutting that last number more than it")
        print("  cuts total P&L. 'stopped' above 20% means the stop is firing on")
        print("  ordinary range behaviour, not on disasters.")
