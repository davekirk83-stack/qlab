"""Time-series trend (managed-futures style) on 20 years of ETFs — the 'crisis alpha' candidate for downside exposure (25 Oct 2026).
Each ETF on its own: long if the trailing 12-month (or 3-month) return is positive, short if negative; rebalance monthly; equal risk
(position scaled to 10% annualised vol per instrument, capped at 2x). Costs 0.04% per turnover. Short side: IG allows shorting indices.
Reported overall, by year, and specifically in the worst months for the S&P 500 (SPY) and in 2008 / 2020 / 2022."""
import glob, os, numpy as np, pandas as pd
P = {}
for f in glob.glob("/home/claude/qlab/data_etf20/*.csv"):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True).normalize(); P[os.path.basename(f)[:-4]] = d.close
P = pd.DataFrame(P).sort_index(); M = P.resample("ME").last(); R = M.pct_change()
dvol = P.pct_change().rolling(60).std().resample("ME").last()*np.sqrt(252)
def book(look, names=None, long_only=False, short_only=False):
    cols = names or list(M.columns)
    sig = np.sign(M[cols]/M[cols].shift(look) - 1)
    if long_only: sig = sig.clip(lower=0)
    if short_only: sig = sig.clip(upper=0)
    w = (sig*(0.10/dvol[cols]).clip(upper=2.0)).shift(1)          # decided at last month-end, held this month
    gross = (w*R[cols]).mean(axis=1, skipna=True)
    turn = (w.fillna(0).diff().abs()).mean(axis=1)*0.0004
    return (gross - turn).dropna()
spy = R["SPY"].dropna()
worst = spy.nsmallest(int(len(spy)*0.1)).index
eq = [c for c in ["SPY", "QQQ", "IWM", "EFA", "EEM", "DIA"] if c in M.columns]
for label, kw in (("12m all ETFs", dict(look=12)), ("3m all ETFs", dict(look=3)), ("12m equity ETFs only", dict(look=12, names=eq)),
                  ("12m equity, SHORT side only", dict(look=12, names=eq, short_only=True))):
    b = book(**kw); b = b[b.index >= "2003-01-01"]; h = len(b)//2
    t = b.mean()/b.std()*np.sqrt(len(b)); ann = b.mean()*12*100
    cw = b.reindex(worst).dropna()
    yrs = b.groupby(b.index.year).sum()*100
    print(f"{label:30s} {ann:+.1f}%/yr  t {t:+.1f}  H1 {b.iloc[:h].mean()*1200:+.1f} H2 {b.iloc[h:].mean()*1200:+.1f}  "
          f"| in SPY's worst 10% months: {cw.mean()*100:+.2f}%/mo (SPY {spy.reindex(cw.index).mean()*100:+.2f}%)  "
          f"| 2008 {yrs.get(2008, np.nan):+.1f}% 2020 {yrs.get(2020, np.nan):+.1f}% 2022 {yrs.get(2022, np.nan):+.1f}%  corr w/ SPY {b.corr(spy.reindex(b.index)):+.2f}")
print("SPY itself by year: 2008 %+.1f%% 2020 %+.1f%% 2022 %+.1f%%" % tuple(spy.groupby(spy.index.year).apply(lambda x: ((1+x).prod()-1)*100).get(y) for y in (2008, 2020, 2022)))
