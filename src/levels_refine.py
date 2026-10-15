"""
DOES THE CASCADE LOW LANDING ON A LEVEL IMPROVE THE BOUNCE?

DK has raised these three times and they are the last untested ideas on his list:
trend lines, fib levels, liquidation levels, major supports.

The minute-scale cascade bounce (doc 35) currently buys the first green minute
with NO reference to where price actually is. If DK's levels matter, a cascade
that bottoms ON a level should bounce better than one that bottoms in open air.
That is a clean, falsifiable split of the SAME trades — no new strategy, no new
degrees of freedom beyond the level definition itself.

LEVELS TESTED (all computed from data available BEFORE the cascade):
  fib            retracements 0.382 / 0.5 / 0.618 / 0.786 of the prior hourly swing
  trend line     least-squares line through the last 3 hourly swing lows, projected
  liquidation    leverage-band prices (10x/25x/50x/100x) below a recent reference,
                 i.e. where crowded longs get force-closed
  prior support  prior day low, prior week low, recent hourly swing lows
  round number   psychological levels scaled to price magnitude

METHOD NOTES
  - Levels use HOURLY bars up to the hour BEFORE the cascade. No lookahead.
  - "On a level" = the cascade low came within a tolerance band of one, where the
    band is scaled to the instrument's own volatility, not a fixed percent.
  - One trade per episode (standing rule).
  - The honest comparison is ON-LEVEL vs OFF-LEVEL within the same trade set.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
H1 = "/home/claude/qlab/data_1h_33"
DROP, WIN = 0.03, 5
TP, SL, MAXMIN, SLIP = 0.015, 0.020, 60, 0.0004


def load_pair(sym):
    m = pd.read_csv(f"{M1}/{sym}.csv")
    m["dt"] = pd.to_datetime(m.t, unit="ms")
    m = m.set_index("dt").sort_index()
    m = m[~m.index.duplicated()]
    hp = f"{H1}/{sym}.csv"
    if not os.path.exists(hp):
        return None, None
    h = pd.read_csv(hp, parse_dates=["date"]).set_index("date").sort_index()
    h = h[~h.index.duplicated()]
    return m, h


def swing_lows(h, n=3):
    lo = h.low
    piv = (lo == lo.rolling(2 * n + 1, center=True).min())
    return piv.fillna(False)


def levels_at(h, hi_idx, px):
    """Every candidate level visible at hourly bar hi_idx, as a flat list of
    (price, kind). Uses only bars up to and including hi_idx."""
    w = h.iloc[max(0, hi_idx - 400):hi_idx + 1]
    if len(w) < 60:
        return []
    out = []
    H, L, C = w.high.values, w.low.values, w.close.values

    # --- fib retracement of the most recent significant swing ---
    lo_i = int(np.argmin(L[-240:])) + max(0, len(L) - 240)
    hi_i = int(np.argmax(H[-240:])) + max(0, len(H) - 240)
    if hi_i > lo_i:
        a, b = L[lo_i], H[hi_i]
        if b > a:
            for f in (0.382, 0.5, 0.618, 0.786):
                out.append((b - (b - a) * f, "fib"))

    # --- trend line through the last 3 swing lows, projected to now ---
    piv = swing_lows(w)
    pidx = np.flatnonzero(piv.values)
    if len(pidx) >= 3:
        p = pidx[-3:]
        y = L[p]
        A = np.polyfit(p, y, 1)
        proj = A[0] * (len(w) - 1) + A[1]
        if proj > 0:
            out.append((proj, "trendline"))

    # --- prior supports ---
    if len(pidx) >= 1:
        for j in pidx[-4:]:
            out.append((L[j], "prior_swing"))
    # prior day / prior week low
    if len(w) >= 24:
        out.append((L[-24:].min(), "prior_day_low"))
    if len(w) >= 168:
        out.append((L[-168:].min(), "prior_week_low"))

    # --- liquidation bands: where leveraged longs entered recently get closed ---
    # reference = volume-weighted-ish recent price; longs at Nx liquidate ~1/N below
    ref = float(np.mean(C[-48:])) if len(C) >= 48 else float(C[-1])
    for lev in (10, 25, 50, 100):
        out.append((ref * (1 - 1.0 / lev), f"liq_{lev}x"))

    # --- round numbers ---
    if px > 0:
        mag = 10 ** np.floor(np.log10(px))
        for mult in (0.25, 0.5, 1.0):
            step = mag * mult
            if step > 0:
                out.append((np.floor(px / step) * step, "round"))
    return [(p, k) for p, k in out if np.isfinite(p) and p > 0]


def run(sym):
    m, h = load_pair(sym)
    if m is None:
        return []
    C = m.close.values; L = m.low.values; Hh = m.high.values; O = m.open.values
    mv = C / pd.Series(C).shift(WIN).values - 1
    sig = np.flatnonzero(mv < -DROP)
    hidx = h.index
    out, last = [], -10**9
    # trailing 1-min vol for the tolerance band
    v1 = pd.Series(C).pct_change().rolling(1440).std().values
    for i in sig:
        if i <= last or i + MAXMIN + 5 >= len(C):
            continue
        e = None
        for j in range(i, min(i + 30, len(C) - 1)):
            if L[j] > L[j - 1]:
                e = j; break
        if e is None:
            continue
        low = L[i:e + 1].min()
        ts = m.index[i]
        # hourly bar strictly BEFORE the cascade
        hi = hidx.searchsorted(ts) - 1
        if hi < 60:
            continue
        lv = levels_at(h, hi, C[i])
        if not lv:
            continue
        tol = max((v1[i] if np.isfinite(v1[i]) else 0.002) * 8, 0.002)
        near = [(abs(low / p - 1), k) for p, k in lv]
        best_d, best_k = min(near, key=lambda x: x[0])
        on = best_d <= tol
        kinds = {k for d, k in near if d <= tol}
        px = O[e + 1] * (1 + SLIP); T = px * (1 + TP); S = px * (1 - SL)
        ret, ex = None, None
        for k in range(e + 1, min(e + 1 + MAXMIN, len(C))):
            if L[k] <= S:
                ret = (S * (1 - SLIP)) / px - 1; ex = k; break
            if Hh[k] >= T:
                ret = (T * (1 - SLIP)) / px - 1; ex = k; break
        if ex is None:
            k = min(e + MAXMIN, len(C) - 1)
            ret = (C[k] * (1 - SLIP)) / px - 1; ex = k
        out.append(dict(sym=sym, date=m.index[e], ret=ret, bars=ex - e,
                        on_level=on, dist=best_d, nearest=best_k, kinds=kinds))
        last = ex
    return out


def rep(lab, t, pad=28):
    if len(t) < 20:
        print(f"  {lab:{pad}s} n={len(t):4d}  too few"); return
    r = t.ret.values if hasattr(t, "ret") else np.array([x["ret"] for x in t])
    se = r.std(ddof=1) / np.sqrt(len(r))
    print(f"  {lab:{pad}s} n={len(r):4d} {r.mean()*100:+8.3f}% "
          f"win {float((r>0).mean())*100:5.1f}%  t={r.mean()/se:+5.2f}")


def main():
    syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{M1}/*.csv"))]
    syms = [s for s in syms if os.path.exists(f"{H1}/{s}.csv")]
    print("DO DK's LEVELS IMPROVE THE CASCADE BOUNCE?\n")
    print(f"  {len(syms)} symbols with both 1-min and hourly data")
    print(f"  same trade as doc 35 (3% in 5m, TP 1.5%, SL 2.0%), split by whether")
    print(f"  the cascade LOW landed on a level visible beforehand\n")
    rows = []
    for s in syms:
        rows += run(s)
    T = pd.DataFrame(rows)
    if not len(T):
        print("  no trades"); return
    print("=" * 76)
    rep("ALL trades", T)
    rep("  cascade low ON a level", T[T.on_level])
    rep("  cascade low in open air", T[~T.on_level])
    print()
    print("=" * 76)
    print("  BY LEVEL TYPE (low landed within tolerance of this kind)")
    print("=" * 76)
    kinds = set()
    for k in T.kinds:
        kinds |= k
    for k in sorted(kinds):
        sub = T[[k in s for s in T.kinds]]
        rep(f"  {k}", sub)
    print()
    print("=" * 76)
    print("  HOW CLOSE? (distance from the cascade low to the nearest level)")
    print("=" * 76)
    for lo, hi, lab in ((0, 0.002, "<0.2%"), (0.002, 0.005, "0.2-0.5%"),
                        (0.005, 0.01, "0.5-1%"), (0.01, 0.02, "1-2%"),
                        (0.02, 9, ">2%")):
        rep(f"  {lab}", T[(T.dist >= lo) & (T.dist < hi)])
    print()
    T.to_pickle("/home/claude/qlab/runs/levels_refine.pkl")


if __name__ == "__main__":
    main()
