"""
WHY THE MULTI-TIMEFRAME COMPOSITE RAN BACKWARDS.

The composite scored -0.282% spread at t=-5.59 in all periods and in both the
fit and held-out windows. Consistent and strong in the WRONG direction, which
is not noise - it is a mechanism. Flipping the sign to make it positive would
be fitting, so the mechanism gets identified first.

THE HYPOTHESIS: STALENESS. An element measured at 8h was scored against the
return over ITS horizon, 20 x 8h = 160 hours from that bar's close. Forward-
filled onto a 4h decision bar it is read up to 7 bars after it was computed,
by which time much of the move it predicted has already happened. For a
mean-reversion element - and every element here is reversion-signed - a late
read is the worst case: price has already reverted, so the signal now points
the wrong way. The horizon has to travel with the element, not just the value.

THE TESTS
  1. per-element cross-sectional IC on the decision bar, by the element's own
     timeframe. If staleness is the cause, elements FASTER than or equal to the
     decision bar should keep their sign and SLOWER ones should invert.
  2. the same composite with the decision bar set to the SLOWEST element's
     timeframe and the horizon set to 20 of those bars, so nothing is stale.
  3. staleness measured directly: IC as a function of how many decision bars
     have passed since the element's own bar closed.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
import composite as CP
import elements as EL
import elements_mktadv as MA

MINS = CP.MINS


def panel(decision, horizon, spec):
    R = CP.raw()
    CP.DECISION = decision
    CP.HORIZON = horizon
    frames = {}
    for s, d in R.items():
        X = CP.build_symbol(d, spec)
        if X is not None: frames[s] = X
    F = pd.DataFrame({s: X["_fwd"] for s, X in frames.items()})
    F = F.sub(F.mean(axis=1), axis=0)
    return frames, F


def xsec_ic(frames, F, name):
    """Cross-sectional IC: rank elements across symbols at each bar."""
    V = pd.DataFrame({s: X[name] for s, X in frames.items() if name in X.columns})
    if V.shape[1] < 8: return np.nan, 0
    Y = F.reindex(V.index)[V.columns]
    ics = []
    for ts in V.index:
        v = V.loc[ts]; y = Y.loc[ts]
        m = v.notna() & y.notna()
        if m.sum() < 8: continue
        ics.append(stats.spearmanr(v[m], y[m]).statistic)
    ics = np.array([x for x in ics if np.isfinite(x)])
    return (np.nanmean(ics), len(ics)) if len(ics) > 50 else (np.nan, 0)


if __name__ == "__main__":
    spec = CP.pick()
    print("TEST 1 — per-element cross-sectional IC on a 4h decision bar")
    print("If staleness is the cause, elements at or below 4h keep their sign")
    print("and elements above 4h invert.\n")
    frames, F = panel("4h", 6, spec)
    print(f"  {'element':<22}{'own tf':>8}{'lag bars':>10}{'library IC':>12}"
          f"{'xsec IC @4h':>13}{'sign':>8}")
    kept = flipped = 0
    rows = []
    for _, r in spec.iterrows():
        ic, n = xsec_ic(frames, F, r["name"])
        if not np.isfinite(ic): continue
        lag = max(1, MINS[r["tf"]] // MINS["4h"])
        same = np.sign(ic) == np.sign(r["ic"])
        rows.append((r["name"], r["tf"], lag, r["ic"], ic, same))
        if same: kept += 1
        else: flipped += 1
        print(f"  {r['name']:<22}{r['tf']:>8}{lag:>10}{r['ic']:>+12.4f}"
              f"{ic:>+13.4f}{'same' if same else 'FLIP':>8}")
    print(f"\n  kept sign {kept} | flipped {flipped}")
    slow = [x for x in rows if MINS[x[1]] > MINS["4h"]]
    fast = [x for x in rows if MINS[x[1]] <= MINS["4h"]]
    if slow:
        print(f"  elements SLOWER than the decision bar: "
              f"{sum(1 for x in slow if not x[5])}/{len(slow)} flipped")
    if fast:
        print(f"  elements at or FASTER than the decision bar: "
              f"{sum(1 for x in fast if not x[5])}/{len(fast)} flipped")

    print(f"\n{'='*96}")
    print("TEST 2 — the same composite with NOTHING stale")
    print("Decision bar = 1D (the slowest element's own bar), horizon 20 bars.\n")
    for dec, hz in (("1D", 20), ("8h", 20), ("4h", 20)):
        sub = spec[spec.tf.map(MINS) <= MINS[dec]]
        if len(sub) < 4:
            print(f"  decision {dec}: only {len(sub)} elements at or below it, skipped")
            continue
        fr, Ff = panel(dec, hz, sub)
        parts = []
        sign = {r["name"]: np.sign(r["ic"]) for _, r in sub.iterrows()}
        for s, X in fr.items():
            Z = pd.DataFrame(index=X.index)
            for n in sub.name:
                if n not in X.columns: continue
                v = X[n]
                w = min(200, max(40, len(v)//3))
                Z[n] = ((v - v.rolling(w, min_periods=20).mean())
                        / v.rolling(w, min_periods=20).std()) * sign[n]
            Z = Z.clip(-4, 4)
            parts.append(pd.DataFrame({"sym": s, "ts": X.index,
                "score": Z.mean(axis=1, skipna=True),
                "nel": Z.notna().sum(axis=1),
                "fwd": Ff[s].reindex(X.index).values}))
        T = pd.concat(parts, ignore_index=True).dropna(subset=["score", "fwd"])
        T = T[T.nel >= max(3, len(sub)//2)]
        print(f"  decision {dec}, {len(sub)} elements (all at or below {dec}), "
              f"{len(T):,} obs")
        CP.quintiles(T, f"    {dec} composite, all periods")
        CP.quintiles(T[T.ts < CP.SPLIT], f"    {dec} fit window")
        CP.quintiles(T[T.ts >= CP.SPLIT], f"    {dec} HELD OUT")
        print()
