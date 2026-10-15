"""
DK: "we could use them separately as different individual trading indicators
     to increase scope for trading different timeframes."

The elements are not in doubt - each passed its own screen (positive net IR at
its best timeframe, >=70% symbol agreement, sign-stable across halves). What
failed was combining them. So this tests the other use: one INDEPENDENT book
per timeframe, each trading only the elements native to it, with no cross-
timeframe interaction at all.

Why this is the better answer to the frequency mandate than trading faster:
five books on five clocks give five streams of trades without shortening any
holding period, so the cost floor from finding 92 is untouched. Breadth across
TIME rather than breadth across instruments.

Each book: equal-weight z-score of its own native elements, long the top
quintile of its own history per symbol, short the bottom, horizon 20 bars on
its own bar. Fit window and held-out window reported separately, because that
split is what has killed everything else today.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
import composite as CP, confluence as CF

SPLIT = "2026-05-01"
TFS = ["15min", "1h", "4h", "8h", "1D"]
HZ = 20

def run_tf(tf, pool):
    spec = CF.spec_for(tf, pool)
    if len(spec) < 3: return None
    R = CP.raw(); rows = []
    for s, d in R.items():
        b = CP.bars(d, tf)
        if len(b) < 300: continue
        z = CF.score_frame(d, tf, spec)
        if z is None: continue
        fwd = b.close.shift(-HZ) / b.close - 1
        rows.append(pd.DataFrame({"sym": s, "ts": b.index, "score": z.values,
                                  "fwd": fwd.values}))
    if not rows: return None
    T = pd.concat(rows, ignore_index=True).dropna()
    return spec, T

def book(T, tag):
    out = []
    for s, g in T.groupby("sym"):
        if len(g) < 150: continue
        q = pd.qcut(g.score.rank(method="first"), 5, labels=False, duplicates="drop")
        if q.nunique() < 5: continue
        m = g.groupby(q).fwd.mean()
        out.append(m.iloc[-1] - m.iloc[0])
    if len(out) < 10: return None
    a = np.array(out)
    t = a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))
    print(f"    {tag:<28}{len(a):>4} syms  long-short {a.mean()*100:+.3f}%  "
          f"t={t:+.2f}  {int((a>0).sum())}/{len(a)} syms positive")
    return dict(spread=a.mean(), t=t, pos=int((a > 0).sum()), n=len(a))

if __name__ == "__main__":
    pool = set(pd.read_csv("/home/claude/qlab/runs/libtf_1h.csv").name)
    print("ONE INDEPENDENT BOOK PER TIMEFRAME — no cross-timeframe interaction\n")
    summary = []
    for tf in TFS:
        r = run_tf(tf, pool)
        if r is None:
            print(f"  {tf}: insufficient\n"); continue
        spec, T = r
        hold_h = HZ * CF.MINS[tf] / 60
        print(f"  {tf}  ({len(spec)} native elements, hold {HZ} bars = "
              f"{hold_h:.0f}h, {T.sym.nunique()} symbols, {len(T):,} obs)")
        a = book(T, "all periods")
        f = book(T[T.ts < SPLIT], "fit window")
        o = book(T[T.ts >= SPLIT], "HELD OUT")
        if f and o:
            same = np.sign(f["spread"]) == np.sign(o["spread"])
            print(f"    {'sign across the split':<28}{'HOLDS' if same else 'FLIPS'}")
            summary.append((tf, f, o, same))
        print()
    print("="*84)
    print("WHICH BOOKS KEEP THEIR SIGN ACROSS THE SPLIT — the only ones worth having")
    for tf, f, o, same in summary:
        print(f"  {tf:>7}  fit {f['spread']*100:+.3f}% (t={f['t']:+.2f})   "
              f"oos {o['spread']*100:+.3f}% (t={o['t']:+.2f})   "
              f"{'HOLDS' if same else 'flips'}")
    keep = [s for s in summary if s[3] and s[2]["t"] > 1.5]
    print(f"\n  books holding sign with held-out t>1.5: {len(keep)} of {len(summary)}")
    for tf, f, o, _ in keep:
        print(f"    {tf}: held-out {o['spread']*100:+.3f}%/trade, "
              f"{o['pos']}/{o['n']} symbols positive")
