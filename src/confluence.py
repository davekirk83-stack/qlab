"""
TIMEFRAME CONFLUENCE: THE LADDER HAS TO AGREE, AND THE FAST END CONFIRMS LAST.

DK: "Wouldn't it make sense to run them forwards - 15s in to 1 hour into
     4 hours into 8s in 12s in 1 days ... confirming as they go?"

This is a different and better construction than the one that just failed.
Averaging a composite across timeframes gave +0.769% in the fit window and
-0.451% held out - a sign reversal between periods, which is not a weak edge,
it is no edge. An average lets a strong disagreeing timeframe be cancelled by
a weak agreeing one and the result is mush.

A conjunction cannot be cancelled. The ladder either agrees or it does not:

  1D   the slowest bar sets the permission. Nothing is taken against it.
  8h   must agree with 1D
  4h   must agree with 8h
  1h   must agree with 4h
  15m  confirms last, and THAT is the entry bar

So the slow bars say whether a trade is allowed and the fast bar says when.
Two things are tested separately, because they are different claims:

  STATE   forward return as a function of HOW MANY rungs agree. If confluence
          is real, return should rise monotonically with the count. A clean
          ladder here is much harder to produce by chance than one good cell.

  EVENT   the moment the fast rung JOINS an already-aligned slow stack. This is
          DK's "confirming as they go" read literally - a transition, not a
          state - and it is the one that gives an entry time.

The score at each rung is the same element set computed natively on that bar,
z-scored within symbol against its own history, sign-flipped by each element's
library IC so positive always means "up". No forward-filling of a slow element
onto a fast bar, so the staleness question does not arise: every rung is read
on its own clock and only the SIGN crosses between rungs.

Control: the identical test with each rung's sign independently shuffled in
time, which preserves how often each rung is positive and destroys only the
alignment between them. If stacked agreement is worth nothing, the real ladder
and the shuffled ladder look the same.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats
import elements as EL
import elements_mktadv as MA
import composite as CP

LADDER = ["1D", "8h", "4h", "1h", "15min"]      # slow -> fast
MINS = {"15min": 15, "1h": 60, "4h": 240, "8h": 480, "1D": 1440}
ENTRY = "1h"            # bar the book acts on
HORIZON = 24            # forward bars on the entry bar = 24h
SPLIT = "2026-05-01"
RNG = np.random.default_rng(7)


def spec_for(tf, pool):
    """Elements worth using ON this bar: positive net IR here, 70% agreement."""
    p = f"/home/claude/qlab/runs/libtf_{tf}.csv"
    A = pd.read_csv(p)
    A = A[(A.agree/A.total >= 0.70) & (A.stable == 1) & A.name.isin(pool)]
    if A.empty: return A
    return A.loc[A.groupby("family").ic.apply(lambda s: s.abs().idxmax())]


def score_frame(d, tf, spec):
    b = CP.bars(d, tf)
    if len(b) < 250: return None
    f = EL.build(b); f.update(MA.build(b))
    w = min(200, max(40, len(b)//3))
    Z = pd.DataFrame(index=b.index)
    for _, r in spec.iterrows():
        n = r["name"]
        if n not in f: continue
        v = pd.Series(f[n], index=b.index)
        Z[n] = ((v - v.rolling(w, min_periods=20).mean())
                / v.rolling(w, min_periods=20).std()) * np.sign(r["ic"])
    if Z.shape[1] == 0: return None
    return Z.clip(-4, 4).mean(axis=1, skipna=True)


def build():
    pool = set(pd.read_csv("/home/claude/qlab/runs/libtf_1h.csv").name)
    specs = {tf: spec_for(tf, pool) for tf in LADDER}
    for tf in LADDER:
        print(f"  {tf:>6}: {len(specs[tf])} elements  "
              f"({', '.join(specs[tf].name.head(6))}{'...' if len(specs[tf])>6 else ''})")
    R = CP.raw()
    rows = []
    for i, (s, d) in enumerate(R.items(), 1):
        ent = CP.bars(d, ENTRY)
        if len(ent) < 600: continue
        sc = {}
        ok = True
        for tf in LADDER:
            z = score_frame(d, tf, specs[tf])
            if z is None: ok = False; break
            if MINS[tf] > MINS[ENTRY]:
                z = z.shift(1)      # a slower bar is known only once it closes
            sc[tf] = z.reindex(ent.index.union(z.index)).ffill().reindex(ent.index)
        if not ok: continue
        X = pd.DataFrame(sc, index=ent.index)
        X["fwd"] = ent.close.shift(-HORIZON)/ent.close - 1
        X["sym"] = s
        X.index.name = "ts"
        rows.append(X.reset_index())
        if i % 12 == 0: print(f"  built {i}/{len(R)}", flush=True)
    T = pd.concat(rows, ignore_index=True).dropna(subset=LADDER + ["fwd"])
    return T


def analyse(T, tag):
    sgn = np.sign(T[LADDER].values)
    T = T.copy()
    T["nup"] = (sgn > 0).sum(axis=1)
    T["ndn"] = (sgn < 0).sum(axis=1)
    T["nagree"] = np.maximum(T["nup"], T["ndn"])
    T["dir"] = np.where(T["nup"] >= T["ndn"], 1, -1)
    T["signed"] = T["fwd"] * T["dir"]
    print(f"\n  {tag}: forward return in the ladder's own direction, by how many rungs agree")
    print(f"    {'rungs':>6}{'n':>9}{'share':>8}{'signed fwd':>13}{'t':>8}{'win%':>7}")
    for k in range(3, 6):
        g = T[T["nagree"] == k]
        if len(g) < 200: continue
        t = g["signed"].mean()/(g["signed"].std(ddof=1)/np.sqrt(len(g)))
        print(f"    {k:>6}{len(g):>9}{len(g)/len(T)*100:>7.1f}%"
              f"{g["signed"].mean()*100:>+12.3f}%{t:>+8.2f}{(g["signed"]>0).mean()*100:>6.1f}%")
    full = T[T["nagree"] == 5]
    part = T[T["nagree"] <= 3]
    if len(full) > 200 and len(part) > 200:
        d = full["signed"].mean() - part["signed"].mean()
        se = np.sqrt(full["signed"].var(ddof=1)/len(full) + part["signed"].var(ddof=1)/len(part))
        print(f"    full stack minus 3-of-5: {d*100:+.3f}%  t={d/se:+.2f}")
    return T


if __name__ == "__main__":
    print("TIMEFRAME CONFLUENCE LADDER  " + "  ->  ".join(LADDER))
    print(f"entry bar {ENTRY}, forward horizon {HORIZON} bars "
          f"({HORIZON*MINS[ENTRY]/1440:.1f} days)\n")
    import os
    CACHE = "/home/claude/qlab/runs/confluence_panel.csv"
    if os.path.exists(CACHE):
        T = pd.read_csv(CACHE, parse_dates=["ts"])
        print("  (reusing cached panel)")
    else:
        T = build(); T.to_csv(CACHE, index=False)
    print(f"\n  {T.sym.nunique()} symbols, {len(T):,} observations")

    A = analyse(T, "ALL PERIODS")
    analyse(T[T["ts"] < SPLIT], f"FIT WINDOW (to {SPLIT})")
    analyse(T[T["ts"] >= SPLIT], f"HELD OUT (from {SPLIT})")

    print(f"\n{'='*96}")
    print("  CONTROL — each rung's sign shuffled in time, independently.")
    print("  This keeps how often each rung is positive and destroys only the")
    print("  alignment between rungs. If confluence is worth nothing, the")
    print("  shuffled ladder reproduces the real one.")
    S = T.copy()
    for tf in LADDER:
        S[tf] = RNG.permutation(S[tf].values)
    analyse(S, "SHUFFLED CONTROL")

    print(f"\n{'='*96}")
    print("  EVENT TEST — the fast rung JOINS an already-aligned slow stack")
    print("  ('confirming as they go': a transition, not a state)")
    T = T.sort_values(["sym", "ts"])
    slow = LADDER[:-1]
    s_sgn = np.sign(T[slow].values)
    T["slow_up"] = (s_sgn > 0).all(axis=1)
    T["slow_dn"] = (s_sgn < 0).all(axis=1)
    f = np.sign(T[LADDER[-1]].values)
    prev_f = T.groupby("sym")[LADDER[-1]].shift(1)
    joins_up = T["slow_up"] & (f > 0) & (np.sign(prev_f) <= 0)
    joins_dn = T["slow_dn"] & (f < 0) & (np.sign(prev_f) >= 0)
    for nm, m, d in (("fast joins an aligned UP stack", joins_up, 1),
                     ("fast joins an aligned DOWN stack", joins_dn, -1)):
        g = T[m.fillna(False)]
        if len(g) < 50: print(f"    {nm:<36}only {len(g)} events"); continue
        sg = g["fwd"] * d
        t = sg.mean()/(sg.std(ddof=1)/np.sqrt(len(sg)))
        base = T[T["slow_up"] if d > 0 else T["slow_dn"]].fwd * d
        print(f"    {nm:<36}n={len(g):>6}  {sg.mean()*100:+.3f}%  t={t:+.2f}  "
              f"win {(sg>0).mean()*100:.0f}%   (stack-aligned baseline "
              f"{base.mean()*100:+.3f}%)")
