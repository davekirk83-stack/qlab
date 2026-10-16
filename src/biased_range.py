"""
THE RANGE BOOK WITH A DIRECTIONAL BIAS — DK's idea, correctly identified.

DK described two strategies:
  positive  "an early buy in, selling a portion on rips, then buying in again
             lower on dips"
  negative  "the reverse, starting a selling position, taking profits in
             places, then reshorting on relief pumps"

Read as trend following those fail, and trend following has now failed twice -
at 15 minutes (decline.py, t = -82) and at daily horizon (trend_daily.py, where
no configuration beat simply holding the basket). But that is not what DK is
describing. Laddering in, scaling out on the move against you, and re-entering
on the pullback IS THE RANGE BOOK. It is already built and already profitable.
What he is adding is a rule about WHICH SIDE TO TAKE.

That has never been tested. Doc 117 rejected a MARKET-WIDE gate, and doc 123
confirmed the book earns in rising, flat and falling markets alike. Neither
asked the per-symbol question: on a coin that is trending down, should we be
running the long ladder at all?

THE VARIANTS
  both always     the registered book - both sides on every coin  (control)
  biased          long side only when the coin is above its own trend,
                  short side only when below
  contrarian      the opposite - long only when below, short only when above.
                  Included because the range book's whole edge is mean
                  reversion, so the contrarian version may well win, and if
                  it does the "bias" intuition is exactly backwards.
  long only /
  short only      to see which side carries the book

Trend measured per symbol as price against its own 200-bar average, taken
from the PREVIOUS bar so nothing peeks. Chase fills and the registered
configuration throughout, so the only thing changing is side selection.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD

STABLE = {"USDTUSD","USDCUSD","DAIUSD","PYUSDUSD","USDSUSD","RLUSDUSD"}


def load():
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_15m/*USD.csv")):
        s = os.path.basename(f)[:-4]
        if s in STABLE: continue
        d = pd.read_csv(f, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if len(d) > 60000: out[s] = d
    return out


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} coins, 15-minute bars, five years.\n")
    print("Side selection is the ONLY thing that changes between rows.\n")
    P = {}
    for s, d in data.items():
        D, ema, lo, hi, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        allow = (v > v.expanding(500).median()).values
        up = (d.close > d.close.rolling(200).mean()).shift(1).fillna(False).values
        P[s] = (d, allow, ema, lo, hi, a, up)

    print(f"  {'variant':<30}{'episodes':>10}{'per ep':>11}{'t':>8}{'win':>6}"
          f"{'worst':>9}{'CAGR 1x':>10}{'maxDD':>9}{'Sharpe':>8}")
    VAR = [("both sides always (registered)", None),
           ("biased: long up / short down", "with"),
           ("contrarian: long down / short up", "against"),
           ("long side only", "longonly"),
           ("short side only", "shortonly")]
    for lbl, mode in VAR:
        rows = []
        for s, (d, allow, ema, lo, hi, a, up) in P.items():
            for side in ("L", "S"):
                if mode == "longonly" and side != "L": continue
                if mode == "shortonly" and side != "S": continue
                al = allow.copy()
                if mode == "with":
                    al = al & (up if side == "L" else ~up)
                elif mode == "against":
                    al = al & (~up if side == "L" else up)
                rows += CP.episodes(d, al, ema, lo, hi, a, None,
                                    "optimistic", side, s)
        S = pd.DataFrame(rows, columns=["sym","entry","exit","ret","side"])
        S = S[np.isfinite(S.ret)]
        if len(S) < 200:
            print(f"  {lbl:<30}too few"); continue
        t = S.ret.mean()/(S.ret.std(ddof=1)/np.sqrt(len(S)))
        r, _, _ = CP.simulate(S, 40, 1)
        cg = f"{r['cagr']*100:.1f}%" if r else "wiped"
        dd = f"{r['dd']*100:.1f}%" if r else "-"
        sh = f"{r['sharpe']:.2f}" if r else "-"
        print(f"  {lbl:<30}{len(S):>10,}{S.ret.mean()*100:>+10.4f}%{t:>+8.2f}"
              f"{(S.ret>0).mean()*100:>5.0f}%{S.ret.min()*100:>+8.1f}%"
              f"{cg:>10}{dd:>9}{sh:>8}")
    print("\n  If 'biased' wins, DK's directional overlay is right and the book")
    print("  should stop fighting the coin's own trend. If 'contrarian' wins,")
    print("  the intuition is backwards and the book earns precisely by taking")
    print("  the side the trend argues against — which is what mean reversion is.")
