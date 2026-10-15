"""
BUYING / SELLING PROGRAM DATA — taker flow and positioning divergence.

DK: "Can we use 'buying / selling program' data to our advantage?"

In equities, "buy/sell program" indicators infer institutional basket activity
from TICK extremes — an inference, and a crude one. In crypto perps the
exchange publishes the underlying fact directly, every 5 minutes:

    sum_taker_long_short_vol_ratio   aggressive BUY volume / aggressive SELL
                                     volume. Market orders only — the people
                                     who crossed the spread because they had
                                     to. This IS the buying/selling program.
    sum_toptrader_long_short_ratio   position ratio of the largest accounts
    count_long_short_ratio           position ratio of ALL accounts, by count
                                     -> dominated by small accounts

The last two together give the thing retail indicators try to approximate and
cannot: a direct read on whether the big accounts and the crowd are positioned
on OPPOSITE sides.

THREE TESTS
  1. TAKER EXTREME        is heavy aggressive selling exhaustion or continuation?
  2. CROWD DIVERGENCE     top traders long while the crowd is short, and inverse
  3. AS A CASCADE FILTER  does taker flow at the cascade low sharpen the bounce
                          the registered book already trades?

Every test carries a matched random-entry control and the hold-40 / stop-1.5-ATR
exit adopted in doc 44. Results are scored in R.

NOTE ON RESOLUTION: the OI archive is 5-minute. Signals are evaluated on those
bars and outcomes measured in 5-minute bars, so "40 bars" is about 3.3 hours.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
M1 = "/home/claude/qlab/data_1m"
RNG = np.random.default_rng(9090)
HOLD = 40


def load(sym):
    """5-minute positioning, joined to 5-minute OHLC built from 1-minute bars."""
    p = f"{OI}/{sym}.csv"
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d["dt"] = pd.to_datetime(d.create_time, errors="coerce", utc=True).dt.tz_localize(None)
    if d.dt.isna().all():
        d["dt"] = pd.to_datetime(pd.to_numeric(d.create_time, errors="coerce"),
                                 unit="ms")
    d = d.dropna(subset=["dt"]).set_index("dt").sort_index()
    d = d[~d.index.duplicated()]
    mp = f"{M1}/{sym}.csv"
    if not os.path.exists(mp):
        return None
    m = pd.read_csv(mp)
    m["dt"] = pd.to_datetime(m.t, unit="ms")
    m = m.set_index("dt").sort_index()
    m = m[~m.index.duplicated()]
    o = m.resample("5min").agg(open=("open", "first"), high=("high", "max"),
                               low=("low", "min"), close=("close", "last"))
    o = o.dropna()
    j = o.join(d[["sum_taker_long_short_vol_ratio",
                  "sum_toptrader_long_short_ratio",
                  "count_long_short_ratio",
                  "sum_open_interest"]], how="inner")
    return j if len(j) > 2000 else None


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def hold_exit(df, bar, entry, stop, hold=HOLD, short=False):
    H, L, C = df.high.values, df.low.values, df.close.values
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    last = bar + hold
    if last > len(C) - 1:
        return None
    for j in range(bar + 1, last + 1):
        if (not short and L[j] <= stop) or (short and H[j] >= stop):
            return -1.0
    d = (C[last] - entry) if not short else (entry - C[last])
    return float(d / risk)


def dedupe(idx, gap=HOLD):
    out, last = [], -10**9
    for i in idx:
        if i - last >= gap:
            out.append(i); last = i
    return out


def run():
    syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{OI}/*.csv"))]
    rows = []
    for s in syms:
        j = load(s)
        if j is None:
            continue
        a = atr(j).bfill().values
        C = j.close.values
        n = len(C)
        tk = j.sum_taker_long_short_vol_ratio.values
        tp = j.sum_toptrader_long_short_ratio.values
        cr = j.count_long_short_ratio.values

        # percentile ranks within this symbol's own history (trailing)
        def pct(x, win=2016):          # 2016 x 5min = 1 week
            return pd.Series(x).rolling(win, min_periods=500)\
                   .apply(lambda v: (v[-1] > v[:-1]).mean(), raw=True).values
        tkp = pct(tk)
        # divergence: top traders vs the crowd, both z-scored on their own history
        def z(x, win=2016):
            sr = pd.Series(x)
            return ((sr - sr.rolling(win, min_periods=500).mean())
                    / sr.rolling(win, min_periods=500).std()).values
        div = z(tp) - z(cr)

        sets = {
            "taker_sell_extreme": np.flatnonzero(tkp <= 0.02),
            "taker_buy_extreme": np.flatnonzero(tkp >= 0.98),
            "top_long_crowd_short": np.flatnonzero(div >= 2.0),
            "top_short_crowd_long": np.flatnonzero(div <= -2.0),
        }
        for name, idx in sets.items():
            idx = [i for i in idx if 600 < i < n - HOLD - 2 and a[i] > 0]
            short = name in ("taker_buy_extreme", "top_short_crowd_long")
            for i in dedupe(idx):
                stop = C[i] - 1.5 * a[i] if not short else C[i] + 1.5 * a[i]
                r = hold_exit(j, i, C[i], stop, short=short)
                if r is not None:
                    rows.append(dict(sym=s, sig=name, R=r, short=short))
            for _ in range(len(dedupe(idx))):
                q = int(RNG.integers(600, max(601, n - HOLD - 2)))
                if a[q] <= 0:
                    continue
                stop = C[q] - 1.5 * a[q] if not short else C[q] + 1.5 * a[q]
                r = hold_exit(j, q, C[q], stop, short=short)
                if r is not None:
                    rows.append(dict(sym=s, sig=f"CONTROL_{name}", R=r, short=short))

        # --- cascade filter: taker flow at the cascade low ---
        mv = np.full(n, np.nan)
        mv[1:] = C[1:] / C[:-1] - 1          # 5-min bar return
        casc = np.flatnonzero(mv <= -0.03)
        for i in dedupe([k for k in casc if 600 < k < n - HOLD - 2 and a[k] > 0]):
            r = hold_exit(j, i, C[i], C[i] - 1.5 * a[i])
            if r is None:
                continue
            rows.append(dict(sym=s, sig="cascade_all", R=r, short=False,
                             tkp=tkp[i] if np.isfinite(tkp[i]) else np.nan,
                             div=div[i] if np.isfinite(div[i]) else np.nan))
    return pd.DataFrame(rows)


def line(lab, r, base=None, pad=28):
    r = np.asarray(r, dtype=float); r = r[np.isfinite(r)]
    if len(r) < 40:
        print(f"  {lab:{pad}s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"   vs control {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  {r.mean():+6.3f}R  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("TAKER FLOW AND POSITIONING — the crypto 'buy/sell program' data")
    print("5-minute bars, hold 40 (~3.3h), stop 1.5 ATR, matched random controls\n")
    T = run()
    if not len(T):
        print("no data"); raise SystemExit
    print("=" * 88)
    print("  1 & 2 — AS STANDALONE SIGNALS")
    print("=" * 88)
    for name in ("taker_sell_extreme", "taker_buy_extreme",
                 "top_long_crowd_short", "top_short_crowd_long"):
        b = line(f"  control", T[T.sig == f"CONTROL_{name}"].R.values)
        line(name, T[T.sig == name].R.values, b)
        print()
    print("=" * 88)
    print("  3 — AS A FILTER ON THE CASCADE BOUNCE")
    print("=" * 88)
    Cc = T[T.sig == "cascade_all"]
    if len(Cc) >= 40:
        base = line("all cascades", Cc.R.values)
        print("  by taker flow at the low (percentile of aggressive BUY share):")
        for lo, hi, lab in ((0, 0.1, "heaviest selling"), (0.1, 0.5, "selling"),
                            (0.5, 0.9, "buying"), (0.9, 1.01, "heaviest buying")):
            line(f"    {lab}", Cc[(Cc["tkp"] >= lo) & (Cc["tkp"] < hi)].R.values, base)
        print("  by top-trader vs crowd divergence at the low:")
        for lo, hi, lab in ((-99, -1, "crowd long, tops short"),
                            (-1, 1, "aligned"), (1, 99, "tops long, crowd short")):
            line(f"    {lab}", Cc[(Cc["div"] >= lo) & (Cc["div"] < hi)].R.values, base)
