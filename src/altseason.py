"""
ALT SEASON: IS IT REAL, AND CAN WE PICK THE RUNNERS?

DK: "in tandem with each BTC bull run there tends to be an 'alt season'. Lots
     of previously quite promising coins look like dogshit right now but are
     starting to warm up. Do we have a method for assessing their potential in
     the next 3-6-9-12-24 months?"

THE HONEST ANSWER TO "DO WE HAVE A METHOD" IS NO - everything in the library
is measured at a 20-bar horizon. 3 to 24 months is 90 to 730 days. We have
essentially no evidence out there. This builds the first.

THE SURVIVORSHIP PROBLEM IS MUCH WORSE HERE THAN FOR THE REVERSION BOOK, and
it has to be stated before any number is read. That book holds 16 days; this
would hold a year. Checking the files: all 300 products have a bar dated
today, so there are ZERO deaths in the sample - it is a pure survivor set and
the death rate cannot be measured internally at all. External estimates put
~52% of tokens launched since 2021 as dead, though that is dominated by
memecoins and Coinbase-listed products are far more filtered. EVERY forward
return here is therefore an UPPER BOUND, and the bias grows with the horizon.

WHAT IS MEASURED
  1. Is alt season a real, datable phenomenon? Monthly: median alt return
     minus BTC return. If it is real it should cluster, not scatter.
  2. At each month-end, do any characteristics predict the next 3/6/12/24
     months? Candidates, all computed causally:
        dd_ath      drawdown from its own all-time high (how dogshit)
        rs_90       return vs BTC over the last 90 days (is it warming up)
        rs_30       the same over 30 days
        above_200   price above its own 200-day mean
        age_days    how long it has been listed
        prior_peak  how big its last cycle run was (was it ever promising)
        vol_60      realised volatility
        liquidity   30-day median dollar volume
  3. DK'S SPECIFIC HYPOTHESIS, tested as a conjunction rather than
     separately: deeply drawn down AND starting to warm up. If the pair beats
     each leg alone, that is the finding.
  4. Everything split by whether the market gate was on, because the
     reversion book has already shown that regime decides.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats

HORIZONS = {"3m": 90, "6m": 180, "12m": 365, "24m": 730}


def load():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        d = pd.read_csv(p)
        if len(d) < 400: continue
        d.index = pd.to_datetime(d.t, unit="ms")
        out[os.path.basename(p)[:-4]] = d[["open", "high", "low", "close", "volume"]].sort_index()
    return out


def panel(data):
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    V = pd.DataFrame({s: d.close*d.volume for s, d in data.items()}).reindex(C.index)
    return C, V


def alt_season_series(C):
    """Monthly: median alt return minus BTC return."""
    btc = C["BTCUSD"] if "BTCUSD" in C else C.iloc[:, 0]
    m = C.resample("ME").last()
    r = m.pct_change()
    b = btc.resample("ME").last().pct_change()
    alt = r.drop(columns=["BTCUSD"], errors="ignore").median(axis=1)
    return pd.DataFrame({"alt": alt, "btc": b, "excess": alt - b}).dropna()


def build_features(C, V):
    feats = {}
    btc = C["BTCUSD"] if "BTCUSD" in C else C.iloc[:, 0]
    ath = C.cummax()
    feats["dd_ath"] = C/ath - 1
    for w, nm in ((30, "rs_30"), (90, "rs_90")):
        feats[nm] = C.pct_change(w).sub(btc.pct_change(w), axis=0)
    feats["above_200"] = (C > C.rolling(200).mean()).astype(float)
    feats["age_days"] = C.notna().cumsum()
    # biggest run in the previous 2 years, ending 1 year ago (was it ever promising)
    feats["prior_peak"] = (C.shift(365).rolling(365).max()
                           / C.shift(730).rolling(365).min() - 1)
    feats["vol_60"] = C.pct_change().rolling(60).std()
    feats["liquidity"] = np.log10(V.rolling(30).median().clip(lower=1))
    feats["dist_200"] = C/C.rolling(200).mean() - 1
    return feats


def ic_table(C, feats, dates, hz, gate=None):
    rows = []
    for name, F in feats.items():
        ics = []; ns = []
        for dt in dates:
            if dt not in C.index: continue
            fwd_dt = dt + pd.Timedelta(days=hz)
            if fwd_dt > C.index[-1]: continue
            if gate is not None and not gate.get(dt, False): continue
            x = F.loc[dt]
            p0 = C.loc[dt]
            p1 = C.reindex(C.index[C.index.get_indexer([fwd_dt], method="nearest")]).iloc[0]
            y = p1/p0 - 1
            m = x.notna() & y.notna() & (p0 > 0)
            if m.sum() < 25: continue
            ics.append(stats.spearmanr(x[m], y[m]).statistic)
            ns.append(int(m.sum()))
        if len(ics) < 6: continue
        a = np.array(ics, float)
        rows.append(dict(feature=name, ic=np.nanmean(a),
                         t=np.nanmean(a)/(np.nanstd(a, ddof=1)/np.sqrt(len(a))),
                         months=len(a), avg_n=int(np.mean(ns))))
    return pd.DataFrame(rows).sort_values("ic", key=abs, ascending=False)


if __name__ == "__main__":
    data = load()
    C, V = panel(data)
    print(f"{C.shape[1]} products, {C.index[0].date()} -> {C.index[-1].date()}")
    print("ALL ARE STILL LISTED: zero deaths in sample. Every number below is")
    print("an UPPER BOUND and the bias grows with the horizon.\n")

    A = alt_season_series(C)
    print("=" * 94)
    print("1. IS ALT SEASON REAL? monthly median-alt return minus BTC return")
    hot = A[A.excess > 0.10]
    print(f"  {len(A)} months. Median excess {A.excess.median()*100:+.1f}%, "
          f"positive in {(A.excess>0).mean()*100:.0f}% of months.")
    print(f"  months where alts beat BTC by >10%: {len(hot)} "
          f"({len(hot)/len(A)*100:.0f}%)")
    run = (A.excess > 0).astype(int)
    streaks = (run != run.shift()).cumsum()
    pos = [len(g) for k, g in run.groupby(streaks) if g.iloc[0] == 1]
    print(f"  consecutive positive months: longest {max(pos) if pos else 0}, "
          f"median run {int(np.median(pos)) if pos else 0}")
    print(f"  (random coin-flips would give a longest run near "
          f"{int(np.log2(len(A)))}, so clustering above that is the 'season')")
    print("\n  the hot months:")
    for dt, r in hot.iterrows():
        print(f"    {dt.date()}  alts {r.alt*100:+6.1f}%  BTC {r.btc*100:+6.1f}%  "
              f"excess {r.excess*100:+6.1f}%")

    feats = build_features(C, V)
    dates = C.resample("ME").last().index
    dates = [d for d in C.index if d in set(C.index[C.index.isin(dates)])] or \
            list(C.resample("ME").last().index.intersection(C.index))
    dates = list(pd.DatetimeIndex(sorted(set(dates))))

    btc = C["BTCUSD"] if "BTCUSD" in C else C.iloc[:, 0]
    idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
    gate = (idx > idx.rolling(200).mean()).shift(1).fillna(False).to_dict()

    print("\n" + "=" * 94)
    print("2. WHAT PREDICTS THE NEXT 3 / 6 / 12 / 24 MONTHS?")
    print("   (rank correlation between the characteristic and the forward return,")
    print("    averaged over month-ends; t is across months)")
    for lbl, hz in HORIZONS.items():
        T = ic_table(C, feats, dates, hz)
        if T.empty: continue
        print(f"\n  --- {lbl} ({hz} days) --- {T.months.iloc[0]} month-ends, "
              f"~{T.avg_n.iloc[0]} coins each")
        print(f"  {'characteristic':<14}{'IC':>9}{'t':>8}")
        for _, r in T.iterrows():
            flag = "  <<<" if abs(r.t) > 2.5 else ""
            print(f"  {r.feature:<14}{r.ic:>+9.3f}{r.t:>+8.2f}{flag}")
