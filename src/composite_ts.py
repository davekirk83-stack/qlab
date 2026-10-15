"""
THE COMPOSITE REBUILT AS A TIME-SERIES BOOK, WHICH IS HOW THE ELEMENTS WERE
ACTUALLY VALIDATED.

WHAT WENT WRONG, AND IT WAS NOT STALENESS.
The first composite scored -0.282% at t=-5.59, consistently backwards. The
staleness hypothesis was tested and refuted: of the elements slower than the
decision bar only 3 of 11 flipped sign, and of those at or faster than it, 0 of 3.

The diagnostic showed the real thing in its own numbers. Library ICs run -0.26
to +0.24. The CROSS-SECTIONAL ICs of the same elements on the decision bar run
-0.005 to +0.029 - an order of magnitude smaller and mostly noise. Averaging
fourteen near-zero cross-sectional ICs, a majority of them slightly negative,
produces a small reliable negative. That is the whole of the -0.282%.

The cause is a category error in the build, not in the elements:

  the LIBRARY measures, within each symbol, whether this element's value
  predicts THAT symbol's own next move. A time-series question.

  the COMPOSITE ranked symbols against each other at each bar and asked which
  symbol outruns the others. A cross-sectional question.

Nothing in the library was ever validated for the second question. A factor can
time a symbol well and still say nothing about which of 49 symbols leads.

SO THIS BUILD ASKS THE QUESTION THE ELEMENTS ANSWER: for each symbol
separately, does a high composite score predict that symbol's own forward
return? Scores are z-scored within symbol against its own trailing history and
the test is per-symbol, then pooled across symbols with a paired t so one
symbol cannot carry it.

Both books are reported side by side, because the difference between them IS
the finding, and the cross-sectional version stays on the record as the
control rather than being deleted.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
import composite as CP

MINS = CP.MINS
SPLIT = "2026-05-01"


def build(decision, horizon, spec, minlen=250):
    CP.DECISION = decision; CP.HORIZON = horizon
    R = CP.raw()
    sign = {r["name"]: np.sign(r["ic"]) for _, r in spec.iterrows()}
    parts = []
    for s, d in R.items():
        dec = CP.bars(d, decision)
        if len(dec) < minlen: continue
        X = CP.build_symbol(d, spec)
        if X is None: continue
        w = min(200, max(40, len(X) // 3))
        Z = pd.DataFrame(index=X.index)
        for n in spec.name:
            if n not in X.columns: continue
            v = X[n]
            Z[n] = ((v - v.rolling(w, min_periods=20).mean())
                    / v.rolling(w, min_periods=20).std()) * sign[n]
        if Z.shape[1] == 0: continue
        Z = Z.clip(-4, 4)
        parts.append(pd.DataFrame({
            "sym": s, "ts": X.index,
            "score": Z.mean(axis=1, skipna=True),
            "nel": Z.notna().sum(axis=1),
            "raw": X["_fwd"].values}))
    if not parts: return None
    T = pd.concat(parts, ignore_index=True).dropna(subset=["score", "raw"])
    return T[T.nel >= max(3, len(spec) // 2)]


def ts_test(T, tag, nq=5):
    """Per symbol: forward return by the symbol's OWN score quintile."""
    out = []
    for s, g in T.groupby("sym"):
        if len(g) < 200: continue
        q = pd.qcut(g.score.rank(method="first"), nq, labels=False)
        m = g.groupby(q).raw.mean()
        if len(m) < nq: continue
        out.append(dict(sym=s, lo=m.iloc[0], hi=m.iloc[-1], spread=m.iloc[-1]-m.iloc[0],
                        ic=stats.spearmanr(g.score, g.raw).statistic))
    if len(out) < 10:
        print(f"  {tag:<40}too few symbols"); return None
    S = pd.DataFrame(out)
    t = S.spread.mean() / (S.spread.std(ddof=1) / np.sqrt(len(S)))
    tic = S.ic.mean() / (S.ic.std(ddof=1) / np.sqrt(len(S)))
    pos = int((S.spread > 0).sum())
    print(f"  {tag:<40}{len(S):>4} syms  Q1 {S.lo.mean()*100:+.3f}%  "
          f"Q5 {S.hi.mean()*100:+.3f}%  spread {S.spread.mean()*100:+.3f}%  "
          f"t={t:+.2f}  IC {S.ic.mean():+.4f} (t={tic:+.2f})  {pos}/{len(S)} syms +")
    return dict(n=len(S), spread=S.spread.mean(), t=t, ic=S.ic.mean(), pos=pos)


def xs_test(T, tag, nq=5):
    """Cross-sectional control: rank symbols against each other each bar."""
    F = T.pivot_table(index="ts", columns="sym", values="raw")
    F = F.sub(F.mean(axis=1), axis=0).stack().rename("dm").reset_index()
    M = T.merge(F, on=["ts", "sym"], how="inner")
    M["q"] = M.groupby("ts").score.transform(
        lambda v: pd.qcut(v.rank(method="first"), nq, labels=False)
        if v.notna().sum() >= 10 else np.nan)
    M = M.dropna(subset=["q"])
    if len(M) < 500: print(f"  {tag:<40}too few"); return None
    g = M.groupby("q").dm
    sp = g.mean().iloc[-1] - g.mean().iloc[0]
    se = np.sqrt(g.var().iloc[-1]/g.count().iloc[-1] + g.var().iloc[0]/g.count().iloc[0])
    print(f"  {tag:<40}n={len(M):>7}  Q1 {g.mean().iloc[0]*100:+.3f}%  "
          f"Q5 {g.mean().iloc[-1]*100:+.3f}%  spread {sp*100:+.3f}%  t={sp/se:+.2f}")
    return dict(spread=sp, t=sp/se)


if __name__ == "__main__":
    spec = CP.pick()
    print(f"{len(spec)} elements, one per family, each read at its own best timeframe\n")
    for dec, hz in (("4h", 6), ("8h", 6), ("1D", 5)):
        sub = spec[spec.tf.map(MINS) <= MINS[dec]]
        if len(sub) < 4: continue
        T = build(dec, hz, sub, minlen=200 if dec != "1D" else 150)
        if T is None or len(T) < 2000:
            print(f"decision {dec}: insufficient data\n"); continue
        days = hz * MINS[dec] / 1440
        print(f"{'='*112}")
        print(f"DECISION BAR {dec} · horizon {hz} bars ({days:.1f} days) · "
              f"{len(sub)} elements · {T.sym.nunique()} symbols · {len(T):,} obs")
        print("  TIME SERIES — each symbol timed against its own history "
              "(the question the library answers)")
        ts_test(T, "    all periods")
        ts_test(T[T.ts < SPLIT], f"    fit window (to {SPLIT})")
        ts_test(T[T.ts >= SPLIT], f"    HELD OUT (from {SPLIT})")
        print("  CROSS SECTION — symbols ranked against each other "
              "(the control; not what the library measures)")
        xs_test(T, "    all periods")
        print()
