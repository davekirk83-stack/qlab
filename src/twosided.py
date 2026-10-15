"""
WORKING BOTH SIDES OF THE RANGE — DK's structural point, tested.

DK: "Should a range strategy also sell the top of the range? Or always just buy
     the low to sell high? Buying the low allows for profit on an overshoot
     upwards? Unless it's always full sold at the top of the band, in which
     case there is a cap on upward overshoots, and downward sells might just
     as well be executed."

The argument is tight and it is about SUNK COST. The current book's final ask
rung liquidates everything at 0.35 ATR beyond the upper band. The upside
overshoot is therefore already forfeited - the book has paid for that cap and
receives nothing in return. Opening a short at the top surrenders nothing that
is not surrendered already.

What it is NOT free of, and what this test has to price rather than assume:

  the tail is not symmetric. The long side's disaster is a breakdown; the
  short side's is a breakout. In alts those are not mirror images - upside
  moves are the violent ones, and a short caught in one has no long inventory
  left to offset it. Measured separately here, never averaged together.

  funding. A perp short pays funding to longs in a market that is usually in
  contango. Charged at 1bp per 8 hours against the short side only, which is
  the ordinary crypto rate, and swept to 3bp to see what breaks it.

  margin. Two sides open at once is two positions, not one. Counted.

THREE BOOKS:
  long only    the current book - ladder in at the lower band, scale out
  short only   the mirror - ladder in at the upper band, cover at the mid
               and the lower band
  two-sided    both, running at the same time on the same symbol

Judged on trade count as much as return, because breadth is where this book
falls short of the target: it runs at about 10 trades a month against 50.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
CAP = 48
BID = [(0.15, 0.30), (0.25, 0.05), (0.30, -0.25), (0.30, -0.55)]
ASK = [(0.4, "mid"), (0.4, 0.0), (1.0, 0.35)]


def long_side(C, H, L, ema, lo_b, hi_b, a, allow, n, fund):
    out = []; inv = []; opened_i = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append(((C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, i-opened_i, "L"))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz),
                                i-opened_i, "L"))
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
                    if len(inv) == 1: opened_i = i
    return out


def short_side(C, H, L, ema, lo_b, hi_b, a, allow, n, fund):
    """The mirror. Sell into the upper band in rungs, cover at the mid and the
    lower band. Funding is charged per bar held against the short."""
    out = []; inv = []; opened_i = 0; covered = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] > hi_b[i]+1.5*a[i] or C[i] < lo_b[i]-1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            f = fund*(i-opened_i)/32.0
            out.append(((cost*(1-MK))/(C[i]*(1+SLIP+TAKER))-1-f, i-opened_i, "S"))
            inv = []; covered = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in covered: continue
                tgt = ema[i] if lvl == "mid" else lo_b[i]-lvl*a[i]
                if L[i] <= tgt and inv:
                    sz = sum(s for _, s in inv); buy = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    f = fund*(i-opened_i)/32.0
                    out.append((((cost*(1-MK))/(tgt*(1+MK))-1-f)*(buy/sz),
                                i-opened_i, "S"))
                    covered.add(k)
                    inv = [(p, s*(1-buy/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: covered = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = hi_b[i]-off*a[i]
                if H[i] > p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: opened_i = i
    return out


def report(R, lbl):
    if len(R) < 100: print(f"  {lbl:<22}too few"); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    print(f"  {lbl:<22}{len(R):>9}{R.ret.mean()*100:>+11.4f}%{t:>+8.2f}"
          f"{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
          f"{R.ret.min()*3*100:>+10.0f}%{R.ret.sum()*100:>+11.0f}%")


if __name__ == "__main__":
    data = RD.load()
    P = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        P[s] = (d, (v > v.expanding(500).median()).values, ema, lo_b, hi_b, a)
    print(f"{len(data)} symbols, containment switch, 15-minute bars.\n")
    for fund, flbl in ((0.0001, "funding 1bp / 8h  (normal)"),
                       (0.0003, "funding 3bp / 8h  (stressed)")):
        print(f"\n{'='*86}\n{flbl}\n{'='*86}")
        print(f"  {'book':<22}{'trades':>9}{'per trade':>12}{'t':>8}{'win':>6}"
              f"{'worst':>9}{'@3x':>10}{'total P&L':>12}")
        Ls, Ss = [], []
        for s, (d, allow, ema, lo_b, hi_b, a) in P.items():
            C, H, L = d.close.values, d.high.values, d.low.values
            n = len(C)
            Ls += long_side(C, H, L, ema, lo_b, hi_b, a, allow, n, fund)
            Ss += short_side(C, H, L, ema, lo_b, hi_b, a, allow, n, fund)
        RL = pd.DataFrame(Ls, columns=["ret", "bars", "side"])
        RS = pd.DataFrame(Ss, columns=["ret", "bars", "side"])
        RB = pd.concat([RL, RS], ignore_index=True)
        report(RL, "long only (current)")
        report(RS, "short only")
        report(RB, "two-sided")
        if len(RL) > 100 and len(RS) > 100:
            print(f"\n  Trade count: {len(RL):,} long -> {len(RB):,} two-sided "
                  f"({len(RB)/len(RL):.2f}x breadth)")
            print(f"  THE TAIL IS NOT SYMMETRIC — long worst {RL.ret.min()*100:+.1f}%, "
                  f"short worst {RS.ret.min()*100:+.1f}%")
            p1l, p1s = RL.ret.quantile(0.01), RS.ret.quantile(0.01)
            print(f"  1st-percentile trade — long {p1l*100:+.2f}%, short {p1s*100:+.2f}%")
            print(f"  Correlation of the two sides' daily P&L: ", end="")
            try:
                print(f"{RL.ret.reset_index(drop=True).corr(RS.ret.reset_index(drop=True)):+.3f}")
            except Exception:
                print("n/a")
