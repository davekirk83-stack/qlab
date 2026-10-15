"""
WHAT THE BREAK ACTUALLY COSTS — DK's objection, priced.

DK: "The most profitable ones during volatility probably don't factor in that
     they would cost the most money from potential stop outs."

He is right that the test could not see this. The range book has no stop in
the usual sense, but it has a break exit: if price closes beyond the band by
1.5 ATR, remaining inventory is liquidated at market. I price that liquidation
at the CLOSE OF THE 15-MINUTE BAR. Price can travel a long way inside fifteen
minutes, and the distance it travels is largest precisely in the volatile
windows I just credited with the better returns. So the error is not random -
it is biased in favour of exactly the conclusion I drew.

Two things compound it. The ladder is heaviest just before a break, because
the lower rungs fill on the way down; the bad exit is taken at full size. And
under leverage a loss is a multiple of posted margin, so the tail is not a
worse average, it is an account event.

FOUR FILL ASSUMPTIONS for the break exit, from generous to brutal:
  close     the bar's close                    - what the book assumes now
  mid       halfway between close and the low  - a partial fill walking down
  low       the lowest price the bar traded    - filled at the worst tick
  next      the next bar's low                 - a stop that triggers late and
                                                 chases the market down

Normal maker exits are untouched: a resting offer that gets hit is filled at
its own price, and that was never in question.

THEN the comparison that matters: the same four assumptions, split by the
volatility at entry. If the loud-window advantage survives being filled at
the worst tick, it is real. If it inverts, DK has killed it and the quiet
filter earns its place back on grounds I never tested.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48


def run(d, allow, ema, lo_b, hi_b, a, rvpct, fill):
    """Returns (ret, was_break, vol_percentile_at_entry)."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    out = []; inv = []; opened_i = 0; sold = set(); vol0 = np.nan
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            if fill == "close":  px = C[i]
            elif fill == "mid":  px = (C[i]+L[i])/2
            elif fill == "low":  px = L[i]
            else:                px = min(L[i], L[i+1]) if i+1 < n else L[i]
            out.append(((px*(1-SLIP-TAKER))/(cost*(1+MK))-1, 1, vol0))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), 0, vol0))
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
                    if len(inv) == 1: opened_i = i; vol0 = rvpct[i]
    return out


if __name__ == "__main__":
    data = RD.load()
    P = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        allow = (v > v.expanding(500).median()).values
        # realised volatility as a percentile of the symbol's own history,
        # recorded at the moment the first rung fills
        rv = pd.Series(d.close.values).pct_change().rolling(60).std()
        P[s] = (d, allow, ema, lo_b, hi_b, a, rv.rank(pct=True).values)
    print(f"{len(data)} symbols. Containment switch, 48-bar cap.\n")
    print("HOW THE BREAK EXIT IS FILLED\n")
    print(f"  {'fill assumption':<34}{'per trade':>12}{'t':>8}{'worst':>9}"
          f"{'break mean':>12}{'total P&L':>12}")
    store = {}
    for fill, lbl in (("close", "bar close  (what I assumed)"),
                      ("mid",   "halfway to the low"),
                      ("low",   "the worst tick in the bar"),
                      ("next",  "next bar's low (late stop)")):
        res = []
        for s, (d, allow, ema, lo_b, hi_b, a, rvp) in P.items():
            res += run(d, allow, ema, lo_b, hi_b, a, rvp, fill)
        R = pd.DataFrame(res, columns=["ret", "brk", "vol"])
        store[fill] = R
        br = R[R.brk == 1]
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        print(f"  {lbl:<34}{R.ret.mean()*100:>+11.4f}%{t:>+8.2f}"
              f"{R.ret.min()*100:>+8.1f}%{br.ret.mean()*100:>+11.3f}%"
              f"{R.ret.sum()*100:>+11.0f}%")
    print(f"\n  {len(store['close'][store['close'].brk==1])/len(store['close'])*100:.0f}% "
          f"of exits are breaks; the rest are resting offers filled at their own price.")

    print("\n" + "="*84)
    print("DOES THE LOUD-WINDOW ADVANTAGE SURVIVE A BRUTAL FILL?")
    print("="*84)
    print("  Volatility at entry, in thirds of each symbol's own history.\n")
    print(f"  {'fill assumption':<30}{'QUIET':>22}{'MIDDLE':>22}{'LOUD':>22}")
    print(f"  {'':<30}{'per trade / worst':>22}{'per trade / worst':>22}"
          f"{'per trade / worst':>22}")
    for fill, lbl in (("close", "bar close"), ("mid", "halfway to the low"),
                      ("low", "worst tick in the bar"), ("next", "next bar's low")):
        R = store[fill].dropna(subset=["vol"])
        cells = []
        for lo, hi in ((0, 1/3), (1/3, 2/3), (2/3, 1.01)):
            g = R[(R.vol >= lo) & (R.vol < hi)]
            cells.append(f"{g.ret.mean()*100:+.3f}% / {g.ret.min()*100:+.1f}%"
                         if len(g) > 100 else "  -")
        print(f"  {lbl:<30}{cells[0]:>22}{cells[1]:>22}{cells[2]:>22}")
    print("\n  AT 3x LEVERAGE, the worst trade as a share of posted margin:")
    for fill, lbl in (("close", "bar close"), ("low", "worst tick in the bar"),
                      ("next", "next bar's low")):
        R = store[fill].dropna(subset=["vol"])
        g = R[R.vol >= 2/3]
        print(f"  {lbl:<30}loud windows: {g.ret.min()*3*100:>+7.0f}% of margin")
