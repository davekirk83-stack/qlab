"""
THE SQUEEZE AS A FORECAST OF A MOVE — not as an entry.

DK: "bollinger band squeezing is useful to identify an approaching squeeze or move."

That is a different claim from the one bb.py tested, and testing the wrong one is how
a real effect gets thrown away. bb.py asked "does buying the break of a squeeze make
money" and got -27.6% annualised. But a squeeze says nothing about DIRECTION. It is a
statement about VOLATILITY: the band width has compressed, and compression is expected
to be followed by expansion.

So the falsifiable claims are:

  1. EXPANSION. After a squeeze, is forward realised volatility HIGHER than baseline?
     (If volatility simply persists, a squeeze predicts more quiet, and the idea dies.)

  2. MAGNITUDE. After a squeeze, is the largest move over the next N days bigger than
     baseline? This is the practical form: is it worth putting the name on a watchlist?

  3. TIMING. How long until the move arrives? A forecast with no horizon is unusable.

  4. DIRECTION. Does the first break out of the squeeze pick the right way? bb.py says
     no; this re-checks it on the resolution rather than the entry bar.

  5. DEPTH. Does a tighter squeeze give a bigger subsequent move? If the effect is real
     it should be monotonic in compression, which is hard to produce by chance.

Measured per instrument then pooled, so one wild altcoin cannot carry the result.
Baseline is every other bar in the same instrument, so each name is its own control.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
from run10 import load_universe, atr

PANEL = load_universe()
HOR = [1, 3, 5, 10, 20]


def prep(df, n=20, k=2.0):
    c = df.close
    ma, sd = c.rolling(n).mean(), c.rolling(n).std()
    bw = ((ma + k * sd) - (ma - k * sd)) / ma.replace(0, np.nan)
    r = c.pct_change()
    rv = r.rolling(20).std()                       # realised vol, trailing
    out = pd.DataFrame(index=df.index)
    out["bw"] = bw
    out["bwpct"] = bw.rolling(252).rank(pct=True)  # where bw sits in its own year
    out["rv"] = rv
    for h in HOR:
        # forward realised vol over the next h bars
        out[f"fv{h}"] = r.shift(-1).rolling(h).std().shift(-(h - 1))
        # largest absolute excursion from the close over the next h bars
        fh = df.high.shift(-1).rolling(h).max().shift(-(h - 1))
        fl = df.low.shift(-1).rolling(h).min().shift(-(h - 1))
        out[f"mv{h}"] = np.maximum((fh / c - 1).abs(), (fl / c - 1).abs())
        out[f"ret{h}"] = c.shift(-h) / c - 1
    return out


def main():
    print("THE SQUEEZE AS A FORECAST OF A MOVE")
    print(f"  {len(PANEL)} instruments, daily. Each name is its own control.\n")

    rows = []
    for s, df in PANEL.items():
        if len(df) < 400:
            continue
        p = prep(df).dropna(subset=["bwpct"])
        if len(p) < 300:
            continue
        sq = p.bwpct <= 0.10          # squeeze = bottom decile of its own year
        wide = p.bwpct >= 0.90
        if sq.sum() < 30:
            continue
        rec = dict(sym=s, n_sq=int(sq.sum()))
        for h in HOR:
            a, b = p.loc[sq], p.loc[~sq]
            rec[f"fv{h}_sq"] = a[f"fv{h}"].mean()
            rec[f"fv{h}_bl"] = b[f"fv{h}"].mean()
            rec[f"mv{h}_sq"] = a[f"mv{h}"].mean()
            rec[f"mv{h}_bl"] = b[f"mv{h}"].mean()
            rec[f"mv{h}_wd"] = p.loc[wide, f"mv{h}"].mean()
            rec[f"rv_sq"] = a["rv"].mean()
        rows.append(rec)
    R = pd.DataFrame(rows)
    print(f"  {len(R)} instruments with enough squeezes "
          f"({int(R.n_sq.sum()):,} squeeze bars in total)\n")

    print("=" * 92)
    print("1-2.  DOES A SQUEEZE PRECEDE A BIGGER MOVE?")
    print("=" * 92)
    print(f"  {'horizon':10s} {'fwd vol: squeeze':>18} {'baseline':>10} {'ratio':>8}"
          f"   {'max move: sq':>13} {'baseline':>10} {'ratio':>8}  {'names up':>9}")
    for h in HOR:
        fs, fb = R[f"fv{h}_sq"].mean(), R[f"fv{h}_bl"].mean()
        ms, mb = R[f"mv{h}_sq"].mean(), R[f"mv{h}_bl"].mean()
        share = float((R[f"mv{h}_sq"] > R[f"mv{h}_bl"]).mean())
        print(f"  {h:3d} bars   {fs*100:17.3f}% {fb*100:9.3f}% {fs/fb:8.2f}x"
              f"   {ms*100:12.2f}% {mb*100:9.2f}% {ms/mb:8.2f}x  {share*100:8.0f}%")
    print("\n  ratio > 1.00 = the squeeze is followed by MORE movement than normal")
    print("  'names up' = share of instruments where it held individually")

    # 5. monotonic in depth?
    print()
    print("=" * 92)
    print("5.  IS IT MONOTONIC IN COMPRESSION?  (10-bar max move by bandwidth decile)")
    print("=" * 92)
    buckets = {d: [] for d in range(10)}
    for s, df in PANEL.items():
        if len(df) < 400:
            continue
        p = prep(df).dropna(subset=["bwpct", "mv10"])
        if len(p) < 300:
            continue
        dec = (p.bwpct * 10).clip(0, 9.999).astype(int)
        g = p.groupby(dec).mv10.mean()
        for d, v in g.items():
            buckets[int(d)].append(v)
    print(f"  {'bandwidth decile':22s} {'mean 10-bar max move':>22} {'n names':>9}")
    for d in range(10):
        v = buckets[d]
        if not v:
            continue
        tag = " <- tightest (squeeze)" if d == 0 else (" <- widest" if d == 9 else "")
        print(f"  decile {d} {'':13s} {np.mean(v)*100:21.2f}% {len(v):9d}{tag}")

    # 4. direction
    print()
    print("=" * 92)
    print("4.  DIRECTION — does the squeeze tell you WHICH WAY?")
    print("=" * 92)
    up, mag = [], []
    for s, df in PANEL.items():
        if len(df) < 400:
            continue
        p = prep(df).dropna(subset=["bwpct", "ret10"])
        sq = p.bwpct <= 0.10
        if sq.sum() < 30:
            continue
        up.append(float((p.loc[sq, "ret10"] > 0).mean()))
        mag.append(float(p.loc[sq, "ret10"].mean()))
    print(f"  P(10-bar return positive after a squeeze)  {np.mean(up)*100:5.1f}%  "
          f"across {len(up)} names")
    print(f"  mean 10-bar return after a squeeze         {np.mean(mag)*100:+5.2f}%")
    print("\n  Near 50% = the squeeze is directionally blind, as expected.")
    print("  That is not a failure: it means it is a TIMING tool, and direction")
    print("  has to come from somewhere else.")

    C.ledger_bump(len(HOR) * 2 + 3, "squeeze as volatility forecast")
    R.to_csv("/home/claude/qlab/runs/squeeze.csv", index=False)


if __name__ == "__main__":
    main()
