"""
WHERE THE STOP BELONGS — measured, not swept.

DK: "Or set the stop another 5-10% below the ideal oscillator edge maybe? To
     distinguish between a normal fill and the first move of a new dip?"

That is a better question than the one I was about to answer. I had written a
blind sweep of stop distances. DK is describing a CLASSIFIER: there are two
populations of move below the band - the ordinary wick that the ladder is
built to catch, and the first leg of a genuine breakdown - and the stop
belongs at the distance where one stops and the other starts. If those two
populations separate, the number comes out of the data.

THE MEASUREMENT. For every trade the book takes, record the MAXIMUM ADVERSE
EXCURSION: how far below the lower band price actually travelled before the
trade resolved. Then split by what happened:

  RECOVERED  the inventory was sold out at the mid or the upper band - the
             trade the strategy exists to take
  BROKE      the position was liquidated into a breakdown - the trade a stop
             is supposed to prevent

If the recovered trades rarely go beyond some distance and the broken ones
routinely do, that distance is the stop. If the distributions sit on top of
each other, there is no such distance, and a stop can only cut good trades
and bad ones in the same proportion - which is worth knowing before putting
one on.

Excursion is measured three ways because DK's "5-10%" is ambiguous and the
reading changes the answer by an order of magnitude:
  in ATR              the book's native unit
  as % of band width  5-10% here is tight - a tenth of the channel
  as % of price       5-10% here is enormous on 15-minute crypto, several ATR
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48


def excursions(d, allow, ema, lo_b, hi_b, a):
    """Every trade with its worst excursion below the band and its outcome."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    rows = []; inv = []; opened_i = 0; sold = set()
    mae = 0.0; band0 = np.nan; atr0 = np.nan; width0 = np.nan
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        if inv:
            mae = max(mae, (band0-L[i])/atr0)
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            r = (C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1
            rows.append((mae, mae*atr0/width0, mae*atr0/band0, r,
                         "broke" if broke else "timeout"))
            inv = []; sold = set(); mae = 0.0; continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    r = ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz)
                    inv = [(p, s*(1-sell/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    sold.add(k)
                    if not inv:
                        rows.append((mae, mae*atr0/width0, mae*atr0/band0, r,
                                     "recovered"))
                        sold = set(); mae = 0.0
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1:
                        opened_i = i; band0 = lo_b[i]; atr0 = a[i]
                        width0 = hi_b[i]-lo_b[i]; mae = 0.0
    return rows


if __name__ == "__main__":
    data = RD.load()
    rows = []
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        rows += excursions(d, (v > v.expanding(500).median()).values,
                           ema, lo_b, hi_b, a)
    R = pd.DataFrame(rows, columns=["atr", "width", "pct", "ret", "how"])
    R = R[np.isfinite(R.atr) & np.isfinite(R.width) & np.isfinite(R.pct)]
    rec = R[R.how == "recovered"]; brk = R[R.how == "broke"]
    print(f"{len(R):,} trades: {len(rec):,} recovered, {len(brk):,} broke, "
          f"{len(R)-len(rec)-len(brk):,} timed out.\n")

    print("="*80)
    print("HOW FAR BELOW THE BAND DOES PRICE GO?")
    print("="*80)
    for col, unit, scale in (("atr", "in ATR", 1), ("width", "as % of band width", 100),
                             ("pct", "as % of price", 100)):
        print(f"\n  {unit}")
        print(f"  {'':<14}{'median':>10}{'75th':>9}{'90th':>9}{'95th':>9}"
              f"{'99th':>9}{'max':>10}")
        for lbl, g in (("recovered", rec), ("broke", brk)):
            q = g[col].quantile([.5, .75, .9, .95, .99])
            print(f"  {lbl:<14}{q[.5]*scale:>10.2f}{q[.75]*scale:>9.2f}"
                  f"{q[.9]*scale:>9.2f}{q[.95]*scale:>9.2f}{q[.99]*scale:>9.2f}"
                  f"{g[col].max()*scale:>10.1f}")

    print("\n" + "="*80)
    print("DO THE TWO POPULATIONS SEPARATE?")
    print("="*80)
    print("  At each distance: what share of GOOD trades would a stop there kill,")
    print("  and what share of BREAKDOWNS would it catch before they got worse?\n")
    print(f"  {'stop distance':<22}{'% of band width':>17}{'good trades hit':>18}"
          f"{'breakdowns caught':>19}{'ratio':>9}")
    best = None
    for x in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0):
        kill = float((rec.atr > x).mean()); catch = float((brk.atr > x).mean())
        w = float(R[R.atr > 0].width.median()/R[R.atr > 0].atr.median()*x*100)
        ratio = catch/kill if kill > 0 else np.inf
        print(f"  {str(x)+' ATR below band':<22}{w:>16.1f}%{kill*100:>17.1f}%"
              f"{catch*100:>18.1f}%{ratio:>9.2f}")
        if kill > 0 and (best is None or ratio > best[1]): best = (x, ratio, kill, catch)
    print("\n  'ratio' above 1 means the stop catches more breakdowns than it kills")
    print("  good trades. Below 1 it is doing net harm at that distance.")
    if best:
        print(f"\n  BEST RATIO: {best[0]} ATR below the band — kills {best[2]*100:.1f}% "
              f"of good trades, catches {best[3]*100:.1f}% of breakdowns "
              f"({best[1]:.2f}x)")
    ov = float((rec.atr > brk.atr.median()).mean())
    print(f"\n  OVERLAP CHECK: {ov*100:.0f}% of recovered trades travel further than")
    print(f"  the MEDIAN breakdown. High overlap means the two populations are not")
    print(f"  cleanly separable and any stop is a blunt instrument.")
