"""
A MULTI-TIMEFRAME COMPOSITE: EVERY ELEMENT READ AT ITS OWN BEST CLOCK.

DK: "you must use them in the most effective way possible."

Finding 91 says 84 of 90 elements are strongest at a timeframe other than the
hourly bar every book has used. Every composite we have ever built sampled all
its elements at ONE bar size, which means most of them were read off the wrong
clock. This is the direct fix: each element is computed on the timeframe where
its net IR is highest, then forward-filled onto a common decision bar.

CONSTRUCTION
  1. pick survivors   net IR > 0 at their best timeframe, >=70% symbol
                      agreement, and SIGN-STABLE across the two halves. The
                      stability screen matters more than the IR: an element
                      that flips sign between halves is a regime, not a factor.
  2. de-duplicate     within a family, elements are near-copies of each other
                      (rsi_14 / rsi_50 / range_pos_50 are one idea three ways).
                      Keep the best-IR element per family, so the composite is
                      a vote of INDEPENDENT ideas rather than one idea counted
                      nine times. Doc 57's point, applied properly.
  3. read each one    on its own best timeframe
  4. align            forward-fill onto the DECISION bar with a strict shift,
                      so a daily element only becomes visible on the decision
                      bar AFTER that daily bar has closed. This is the only
                      place lookahead can enter a multi-timeframe build and it
                      is where doc 25 went wrong before.
  5. combine          z-score each element within symbol, flip by the sign of
                      its IC so every element points the same way, average.
  6. test             forward return by composite quintile, in sample and in
                      a held-out time period, plus the single-timeframe
                      composite as the control so the multi-timeframe claim
                      has something to beat.

The control is the point. If reading each element on its own clock is not
better than reading all of them on one clock, the whole exercise bought
nothing and should be said so.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, json
import numpy as np, pandas as pd
from scipy import stats
import elements as EL
import elements_mktadv as MA

ORDER = ["15min", "30min", "1h", "2h", "4h", "8h", "1D"]
MINS = dict(zip(ORDER, [15, 30, 60, 120, 240, 480, 1440]))
DECISION = "4h"          # bar on which positions are taken
HORIZON = 6              # forward bars on the decision bar = 24h
SPLIT = "2026-05-01"     # everything before = fit window, after = held out


def pick():
    """Survivors, de-duplicated to one element per family."""
    fr = []
    for tf in ORDER:
        p = f"/home/claude/qlab/runs/libtf_{tf}.csv"
        if os.path.exists(p): fr.append(pd.read_csv(p))
    A = pd.concat(fr, ignore_index=True)
    A["trips"] = 365.25*1440/(A.tf.map(MINS)*HORIZON*0+A.tf.map(MINS)*20)
    A["irg"] = A.ic.abs()*np.sqrt(A.trips*A.nsym)
    vol = 0.60*np.sqrt((A.tf.map(MINS)*20/60)/(365.25*24))
    A["irn"] = A.irg - ((6/10000)/vol)*np.sqrt(A.trips*A.nsym)
    A = A[(A.agree/A.total >= 0.70) & (A.stable == 1)]
    best = A.loc[A.groupby("name").irn.idxmax()]
    best = best[best.irn > 0]
    # one element per family: the highest net IR
    keep = best.loc[best.groupby("family").irn.idxmax()]
    return keep[["name", "family", "tf", "ic", "irn", "agree", "total"]] \
        .sort_values("irn", ascending=False).reset_index(drop=True)


_RAW = {}
def raw():
    if not _RAW:
        for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
            for f in sorted(glob.glob(f"{folder}/*.csv")):
                s = os.path.basename(f)[:-4]
                if s in _RAW: continue
                d = pd.read_csv(f)
                d.index = pd.to_datetime(d.t, unit="ms", utc=True)
                _RAW[s] = d[["open", "high", "low", "close", "volume"]]
    return _RAW


def bars(d, tf):
    return d.resample(tf).agg(open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), volume=("volume", "sum")).dropna()


def build_symbol(d, spec):
    """Each element on its own timeframe, aligned to the decision bar."""
    dec = bars(d, DECISION)
    if len(dec) < 400: return None
    cache = {}
    cols = {}
    for _, r in spec.iterrows():
        tf = r["tf"]
        if tf not in cache:
            b = bars(d, tf)
            f = EL.build(b); f.update(MA.build(b))
            cache[tf] = (b, f)
        b, f = cache[tf]
        if r["name"] not in f: continue
        s = pd.Series(f[r["name"]], index=b.index)
        if MINS[tf] > MINS[DECISION]:
            # a slower bar is only known AFTER it closes: shift one slow bar,
            # then forward-fill onto the decision bar. This is the lookahead seam.
            s = s.shift(1)
        s = s.reindex(dec.index.union(s.index)).ffill().reindex(dec.index)
        cols[r["name"]] = s
    if not cols: return None
    X = pd.DataFrame(cols, index=dec.index)
    X["_fwd"] = dec.close.shift(-HORIZON)/dec.close - 1
    return X


def run():
    spec = pick()
    print("SURVIVING ELEMENTS — one per family, each at its own best timeframe")
    print(f"  {'element':<22}{'family':<16}{'tf':>7}{'IC':>9}{'netIR':>8}{'agree':>8}")
    for _, r in spec.iterrows():
        print(f"  {r['name']:<22}{r['family']:<16}{r['tf']:>7}{r['ic']:>+9.4f}"
              f"{r['irn']:>8.2f}{int(r['agree'])}/{int(r['total']):<4}")
    print(f"\n  decision bar {DECISION}, forward horizon {HORIZON} bars "
          f"({HORIZON*MINS[DECISION]/24/60:.1f} days)")

    R = raw()
    frames = {}
    for i, (s, d) in enumerate(R.items(), 1):
        X = build_symbol(d, spec)
        if X is not None: frames[s] = X
        if i % 12 == 0: print(f"  built {i}/{len(R)}", flush=True)
    print(f"  {len(frames)} symbols\n")

    # panel-demean the forward return, z-score each element within symbol
    F = pd.DataFrame({s: X["_fwd"] for s, X in frames.items()})
    F = F.sub(F.mean(axis=1), axis=0)
    names = [n for n in spec.name if any(n in X.columns for X in frames.values())]
    sign = {r["name"]: np.sign(r["ic"]) for _, r in spec.iterrows()}

    parts = []
    for s, X in frames.items():
        Z = pd.DataFrame(index=X.index)
        for n in names:
            if n not in X.columns: continue
            v = X[n]
            Z[n] = ((v - v.rolling(200, min_periods=60).mean())
                    / v.rolling(200, min_periods=60).std()) * sign[n]
        Z = Z.clip(-4, 4)
        out = pd.DataFrame({"sym": s, "ts": X.index,
                            "score": Z.mean(axis=1, skipna=True),
                            "nel": Z.notna().sum(axis=1),
                            "fwd": F[s].reindex(X.index).values})
        parts.append(out)
    T = pd.concat(parts, ignore_index=True).dropna(subset=["score", "fwd"])
    T = T[T.nel >= max(3, len(names)//2)]
    print(f"  {len(T):,} observations, median {T.nel.median():.0f} elements live\n")
    return T, spec, names, frames, F


def quintiles(T, tag):
    T = T.copy()
    T["q"] = T.groupby("ts").score.transform(
        lambda v: pd.qcut(v.rank(method="first"), 5, labels=False) if v.notna().sum() >= 10 else np.nan)
    T = T.dropna(subset=["q"])
    if len(T) < 200: print(f"  {tag}: too few"); return None
    g = T.groupby("q").fwd
    lo, hi = g.mean().iloc[0], g.mean().iloc[-1]
    spread = hi - lo
    se = np.sqrt(g.var().iloc[-1]/g.count().iloc[-1] + g.var().iloc[0]/g.count().iloc[0])
    ic = stats.spearmanr(T.score, T.fwd).statistic
    print(f"  {tag:<34}n={len(T):>7}  Q1 {lo*100:+.3f}%  Q5 {hi*100:+.3f}%  "
          f"spread {spread*100:+.3f}%  t={spread/se:+.2f}  IC={ic:+.4f}")
    return dict(n=len(T), spread=spread, t=spread/se, ic=ic)


if __name__ == "__main__":
    T, spec, names, frames, F = run()
    print("=" * 100)
    print("MULTI-TIMEFRAME COMPOSITE — forward return by score quintile")
    quintiles(T, "all periods")
    quintiles(T[T.ts < SPLIT], f"fit window (to {SPLIT})")
    quintiles(T[T.ts >= SPLIT], f"HELD OUT (from {SPLIT})")
    T.to_parquet("/home/claude/qlab/runs/composite_mtf.parquet")
    json.dump({"names": list(names), "decision": DECISION, "horizon": HORIZON,
               "spec": spec.to_dict("records")},
              open("/home/claude/qlab/runs/composite_spec.json", "w"), default=str)
    print("\n  -> runs/composite_mtf.parquet, runs/composite_spec.json")
    print("  next: composite_control.py runs the same elements all on one bar")
