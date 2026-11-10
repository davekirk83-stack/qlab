"""Doc 223 — DK 11:34–11:37: "The whole thing is overextended … a major crash like 1928 … an insurance short with tight stop loss every time the
S&P 500 makes a new high … tie some kind of short into a 'topping calculation' like the Buffett index."
S&P 500 daily 1928–2026 (hist_study set-up: next-close execution, IG spread, era funding). Valuation: Shiller CAPE (monthly, to Sep 2023);
'expensive' = CAPE above the 80th percentile of ALL EARLIER months (walk-forward, no hindsight). Rules fixed in advance:
  T1 new 1-year closing high -> short next close, stop 1 ATR (tight), exit after 20 days
  T2 same, stop 2 ATR
  T3 T1 only when CAPE is expensive (walk-forward)
  T4 new ALL-TIME closing high -> short, stop 1 ATR, 20 days
  T5 T4 only when CAPE expensive
  T6 'insurance that pays in crashes': new high + CAPE expensive -> short, stop 1 ATR, hold up to 120 days, trail the stop to 3 ATR above the lowest close
Each by era and the 1929/1987/2000/2007/2020/2022 tops."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hist_study as H
d, C, A, IX, N = H.d, H.C, H.A, H.IX, H.N
sh = pd.read_csv(f"{H.ROOT}/data_hist/shiller_monthly.csv"); sh = sh[pd.to_numeric(sh.Date, errors="coerce").notna()].copy()
sh.index = pd.to_datetime([f"{int(float(x))}-{int(round((float(x) - int(float(x))) * 100)):02d}-01" for x in sh.Date]); cape = pd.to_numeric(sh.CAPE, errors="coerce").dropna()
pct80 = cape.expanding(min_periods=120).quantile(0.80).shift(1)          # 80th percentile of EARLIER months only
exp_m = (cape > pct80); expensive = exp_m.reindex(IX, method="ffill").fillna(False)
hi252 = d.close >= d.close.rolling(252).max(); ath = d.close >= d.close.cummax()
def short_trail(entry, stop=1.0, maxd=20, trail=None):
    E = entry.fillna(False).values; out = []; i = 0
    while i < N - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        j0 = i + 1; e = C[j0]; st = e + stop * A[i]; lo = e; j = j0 + 1; px = None
        while j < N:
            if C[j] >= st: px = C[j]; break
            if trail: lo = min(lo, C[j]); st = min(st, lo + trail * A[i]) if lo < e - trail * A[i] else st
            if (j - j0) >= maxd: px = C[j]; break
            j += 1
        if px is None: break
        days = (IX[j] - IX[j0]).days; fund = (0.025 - H.rate_at(IX[j0])) / 365 * days * e
        out.append((IX[i], (e - px - H.COST * e * 2 - fund) / A[i])); i = j
    return pd.DataFrame(out, columns=["t", "R"])
T = {"T1 new 1-year high, stop 1 ATR, 20 days": short_trail(hi252, 1.0, 20),
     "T2 new 1-year high, stop 2 ATR, 20 days": short_trail(hi252, 2.0, 20),
     "T3 new 1-year high + CAPE expensive, stop 1 ATR": short_trail(hi252 & expensive, 1.0, 20),
     "T4 new all-time high, stop 1 ATR, 20 days": short_trail(ath, 1.0, 20),
     "T5 new all-time high + CAPE expensive, stop 1 ATR": short_trail(ath & expensive, 1.0, 20),
     "T6 new high + CAPE expensive, stop 1 ATR, ride up to 120 days (3 ATR trail)": short_trail(hi252 & expensive, 1.0, 120, trail=3.0)}
TOPS = [("1929", "1929-08-01", "1929-12-31"), ("1937", "1937-02-01", "1937-12-31"), ("1973", "1972-12-01", "1974-06-30"), ("1987", "1987-07-01", "1987-12-31"),
        ("2000", "2000-01-01", "2001-06-30"), ("2007", "2007-07-01", "2008-12-31"), ("2020", "2020-01-15", "2020-04-30"), ("2022", "2021-11-01", "2022-10-31")]
if __name__ == "__main__":
    print(f"CAPE expensive (above the 80th pct of earlier months) on {100 * expensive.mean():.0f}% of days; latest CAPE in the data {cape.iloc[-1]:.1f} ({cape.index[-1]:%Y-%m}), threshold {pct80.iloc[-1]:.1f}")
    for nm, t in T.items():
        tt = t.R.mean() / t.R.std() * np.sqrt(len(t)); win = (t.R > 0).mean()
        tops = " ".join(f"{a}:{t[(t.t >= b) & (t.t <= c)].R.sum():+.1f}" for a, b, c in TOPS)
        y = t.groupby(t.t.dt.year).R.sum()
        print(f"\n{nm}: n{len(t)} ({len(t) / 99:.0f}/yr) mean {t.R.mean():+.3f} ATR t {tt:+.2f} win {100 * win:.0f}% | total {t.R.sum():+.0f} ATR, years + {100 * (y > 0).mean():.0f}%, worst year {y.min():+.0f}\n   {H.era_line(t)}\n   at the big tops: {tops}")
