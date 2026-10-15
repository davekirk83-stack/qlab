"""
DOES THE CASCADE RESCUE THE CANDLE, THE WAY IT RESCUED THE LEVEL?

Levels fail as a general tool but work as a cascade filter (doc 37). Candles and
patterns fail as general tools (this run). The obvious question is whether the
same reconciliation applies: a hammer means nothing on a quiet Tuesday, but a
hammer at the bottom of a forced-liquidation flush is a visible record of
sellers being absorbed.

TEST: the same minute-scale cascade trade as doc 35, split by the SHAPE of the
bar at the cascade low. No new strategy, no new exits, one extra degree of
freedom (the shape test), same trade set.

    hammer_low      the cascade's lowest minute closed in the top of its range
                    with a long lower wick — absorption
    weak_low        closed in the bottom of its range — still falling
    rest            everything else
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
DROP, WIN = 0.03, 5
TP, SL, MAXMIN, SLIP = 0.015, 0.020, 60, 0.0004


def run(sym):
    m = pd.read_csv(f"{M1}/{sym}.csv")
    m["dt"] = pd.to_datetime(m.t, unit="ms")
    m = m.set_index("dt").sort_index()
    m = m[~m.index.duplicated()]
    C, L, H, O = m.close.values, m.low.values, m.high.values, m.open.values
    mv = C / pd.Series(C).shift(WIN).values - 1
    sig = np.flatnonzero(mv < -DROP)
    out, last = [], -10**9
    for i in sig:
        if i <= last or i + MAXMIN + 5 >= len(C):
            continue
        e = None
        for j in range(i, min(i + 30, len(C) - 1)):
            if L[j] > L[j - 1]:
                e = j; break
        if e is None:
            continue
        seg = slice(i, e + 1)
        k = i + int(np.argmin(L[seg]))          # the lowest minute of the flush
        rng = H[k] - L[k]
        if rng <= 0:
            continue
        pos = (C[k] - L[k]) / rng               # where it closed in its range
        body = abs(C[k] - O[k])
        lower = min(C[k], O[k]) - L[k]
        hammer = pos > 0.6 and lower > 1.5 * body
        weak = pos < 0.3
        shape = "hammer_low" if hammer else ("weak_low" if weak else "rest")
        px = O[e + 1] * (1 + SLIP); T = px * (1 + TP); S = px * (1 - SL)
        ret, ex = None, None
        for j in range(e + 1, min(e + 1 + MAXMIN, len(C))):
            if L[j] <= S:
                ret = (S * (1 - SLIP)) / px - 1; ex = j; break
            if H[j] >= T:
                ret = (T * (1 - SLIP)) / px - 1; ex = j; break
        if ex is None:
            j = min(e + MAXMIN, len(C) - 1)
            ret = (C[j] * (1 - SLIP)) / px - 1; ex = j
        out.append(dict(sym=sym, ret=ret, shape=shape, pos=pos))
        last = ex
    return out


def rep(lab, t, pad=22):
    if len(t) < 20:
        print(f"  {lab:{pad}s} n={len(t):4d}  too few"); return
    r = t.ret.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    print(f"  {lab:{pad}s} n={len(r):4d} {r.mean()*100:+7.3f}%  "
          f"win {float((r>0).mean())*100:5.1f}%  t={r.mean()/se:+5.2f}")


if __name__ == "__main__":
    syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{M1}/*.csv"))]
    rows = []
    for s in syms:
        rows += run(s)
    T = pd.DataFrame(rows)
    print("THE SHAPE OF THE CASCADE LOW — does the candle matter HERE?\n")
    print("=" * 70)
    rep("ALL cascade trades", T)
    print()
    for sh in ("hammer_low", "rest", "weak_low"):
        rep(f"  {sh}", T[T["shape"] == sh])
    print()
    print("  by close position within the low bar's range:")
    for lo, hi in ((0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        rep(f"    pos {lo:.1f}-{hi:.1f}", T[(T.pos >= lo) & (T.pos < hi)])
