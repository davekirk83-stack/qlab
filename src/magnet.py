"""
THE LIQUIDITY MAGNET — measured properly.

DK: "It is a firmly held contention that most market moves in bitcoin aim to
target liquidity (resting orders / liquidations of high leverage positions or
stop losses). This may apply to all markets. How can we measure this and then
utilise this knowledge?"

WHAT DOC 59 FOUND, AND WHAT WAS WRONG WITH IT
Four symbols, 45 days: price drifts TOWARD the heavier side of the resting
book over 6-24 hours, then reverses on contact. Consistent sign across all
four symbols and every band. But the forward window was 24h and the sample
45 days, so there were 32 independent observations, not 12,657. The daily
block bootstrap put the 95% CI at [-0.512,+0.009]: the right sign, no
significance. Doc 33's lesson (overlapping windows inflated t tenfold)
applied to our own new result.

WHAT THE INDEPENDENCE CHECK FOUND (doc 58's lesson, applied)
At 5-minute resolution the magnet looked like a 58% restatement of elements
we already have. At the honest daily resolution it is not: residualised on
range position it retains 88% of its IC (-0.253 of -0.288). The 5-minute
figure was an artefact of autocorrelation, not evidence of redundancy. The
largest correlation with anything already measured is +0.380, with total
book depth -- which is a scale term, not a direction term.

So the constraint was never redundancy. It was sample. This module runs the
same measurement over 20 symbols and a year, which is ~7,300 independent
symbol-days rather than 32.

THE MEASURE
    skew_b = (resting notional within b% BELOW) - (within b% ABOVE)
             -------------------------------------------------------
                      (total within b% either side)

Positive = more resting size below. The magnet hypothesis says price falls
toward it. The support hypothesis says that size holds price up. They are
opposite signs on the same number, which is why this is testable at all.

HONESTY MACHINERY, all of it forced
  daily blocks      one observation per symbol-day, never overlapping
  per-symbol IC     computed within instrument, then averaged
  demeaned returns  cross-sectional mean removed per bar, so a market-wide
                    move cannot masquerade as a book effect
  block bootstrap   resample whole days, 2000 draws, CI reported
  partial IC        residualised on the elements already in the library
  split by half     first six months vs second
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats

DEPTH = "/home/claude/qlab/data_depth_full"
M1 = "/home/claude/qlab/data_1m"
OI = "/home/claude/qlab/data_oi"
BANDS = ["0.2", "1", "2", "3", "4", "5"]
RNG = np.random.default_rng(5915)


def load(sym):
    p = f"{DEPTH}/{sym}.csv"
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, parse_dates=["ts"]).set_index("ts").sort_index()
    m = f"{M1}/{sym}.csv"
    if not os.path.exists(m):
        return None
    k = pd.read_csv(m)
    k["dt"] = pd.to_datetime(k.t, unit="ms")
    k = k.set_index("dt").sort_index()
    k = k[~k.index.duplicated()]
    px = k.resample("5min").agg(close=("close", "last"), high=("high", "max"),
                                low=("low", "min")).dropna()
    j = d.join(px, how="inner")
    return j if len(j) > 2000 else None


def skew(j, band):
    """Net resting notional below minus above, within `band` percent."""
    lim = float(band)
    lo = sum(j[c].values for c in j.columns
             if c.startswith("d-") and float(c[2:]) <= lim + 1e-9)
    hi = sum(j[c].values for c in j.columns
             if c.startswith("d+") and float(c[2:]) <= lim + 1e-9)
    t = lo + hi
    return np.where(t > 0, (lo - hi) / t, np.nan)


def daily_panel(horizon_bars=288):
    """One observation per symbol per day: skew at the open of the window,
    and the forward return over it. Non-overlapping by construction."""
    rows = []
    for f in sorted(glob.glob(f"{DEPTH}/*.csv")):
        s = os.path.basename(f)[:-4]
        j = load(s)
        if j is None:
            continue
        C = j.close.values
        n = len(C)
        fwd = np.full(n, np.nan)
        fwd[:-horizon_bars] = C[horizon_bars:] / C[:-horizon_bars] - 1
        sk = {b: skew(j, b) for b in BANDS}
        tot = sum(j[c].values for c in j.columns if c.startswith("d"))
        lo = pd.Series(j.low.values).rolling(576).min().values
        hi = pd.Series(j.high.values).rolling(576).max().values
        rp = (C - lo) / np.where(hi > lo, hi - lo, np.nan)
        for i in range(576, n - horizon_bars, horizon_bars):
            if not np.isfinite(fwd[i]):
                continue
            r = dict(sym=s, ts=j.index[i], fwd=fwd[i],
                     depth=np.log(tot[i]) if tot[i] > 0 else np.nan,
                     range_pos=rp[i])
            for b in BANDS:
                r[f"skew_{b}"] = sk[b][i]
            rows.append(r)
    P = pd.DataFrame(rows)
    # demean forward returns per timestamp across the panel: a market-wide
    # move cannot be attributed to any one book
    P["fwd_dm"] = P.fwd - P.groupby(P.ts.dt.floor("1D")).fwd.transform("mean")
    return P


def ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    return stats.spearmanr(x[m], y[m]).correlation if m.sum() > 50 else np.nan


def per_symbol_ic(P, col, ycol="fwd_dm"):
    v = [ic(g[col].values, g[ycol].values) for _, g in P.groupby("sym")]
    v = [x for x in v if np.isfinite(x)]
    return np.mean(v), v


def boot(P, col, ycol="fwd_dm", draws=2000):
    days = P.ts.dt.floor("1D").values
    uniq = np.unique(days)
    idx = {d: np.flatnonzero(days == d) for d in uniq}
    x, y = P[col].values, P[ycol].values
    out = []
    for _ in range(draws):
        pick = RNG.choice(uniq, len(uniq), replace=True)
        m = np.concatenate([idx[d] for d in pick])
        out.append(ic(x[m], y[m]))
    out = np.array(out)
    out = out[np.isfinite(out)]
    return np.mean(out), np.percentile(out, 2.5), np.percentile(out, 97.5)


def partial(P, col, controls, ycol="fwd_dm"):
    m = np.isfinite(P[col]) & np.isfinite(P[ycol])
    for c in controls:
        m &= np.isfinite(P[c])
    if m.sum() < 200:
        return np.nan
    rz = lambda v: (stats.rankdata(v) - stats.rankdata(v).mean()) / stats.rankdata(v).std()
    A = np.column_stack([np.ones(m.sum())] + [rz(P.loc[m, c].values) for c in controls])
    b, *_ = np.linalg.lstsq(A, rz(P.loc[m, col].values), rcond=None)
    return ic(rz(P.loc[m, col].values) - A @ b, P.loc[m, ycol].values)


if __name__ == "__main__":
    print("THE LIQUIDITY MAGNET — 20 symbols, one year, non-overlapping daily blocks\n")
    P = daily_panel()
    print(f"  {P.sym.nunique()} symbols   {len(P)} symbol-days   "
          f"{P.ts.dt.floor('1D').nunique()} distinct days")
    print(f"  {P.ts.min().date()} -> {P.ts.max().date()}\n")

    print("=" * 86)
    print("  IC of book skew vs the NEXT 24 HOURS (demeaned across the panel)")
    print("=" * 86)
    print(f"  {'band':>8}{'IC':>9}{'95% CI':>22}{'syms +ve':>11}{'verdict':>16}")
    for b in BANDS:
        c = f"skew_{b}"
        mu, v = per_symbol_ic(P, c)
        bm, lo, hi = boot(P, c)
        neg = sum(1 for x in v if x < 0)
        sig = "MAGNET" if hi < 0 else ("SUPPORT" if lo > 0 else "not significant")
        print(f"  {b+'%':>8}{mu:>+9.3f}   [{lo:+.3f},{hi:+.3f}]"
              f"{neg:>8}/{len(v)}{sig:>16}")

    print("\n" + "=" * 86)
    print("  IS IT NEW? partial IC after the elements we already have")
    print("=" * 86)
    ctr = ["range_pos", "depth"]
    for b in ("0.2", "1", "2"):
        c = f"skew_{b}"
        raw, _ = per_symbol_ic(P, c)
        pa = partial(P, c, ctr)
        print(f"  skew_{b+'%':<6} raw {raw:+.3f}   partial {pa:+.3f}   "
              f"{pa/raw*100 if raw else float('nan'):5.0f}% retained")
    rp, _ = per_symbol_ic(P, "range_pos")
    print(f"  (range_pos on its own: {rp:+.3f})")

    print("\n" + "=" * 86)
    print("  STABILITY — first half vs second")
    print("=" * 86)
    cut = P.ts.quantile(0.5)
    for lab, S in (("first half", P[P.ts <= cut]), ("second half", P[P.ts > cut])):
        mu, _ = per_symbol_ic(S, "skew_1")
        print(f"  {lab:14s} n={len(S):6d}   IC {mu:+.3f}")
