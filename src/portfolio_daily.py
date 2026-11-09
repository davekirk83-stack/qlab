"""Doc 199 — the long-history daily books combined: how often do they lose together? Monthly results per book (ATR units per trade,
summed), correlation, and the combined portfolio's share of positive months / years. Trend uses the walk-forward fallow months."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2, trend_futures_bets as TF, market_search_5 as M5, market_search_4 as M4
def trades(items):
    T = []
    for k, df, fn, kw in items:
        for x in G.simulate(df, fn(df), kw.get("manage")): x["mkt"] = k; T.append(x)
    t = pd.DataFrame(T); t["t"] = pd.to_datetime(t.t, utc=True); return t
IX = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")
books = {
 "RSI2": trades([(k, M4.prep_rsi(k), M4.rsi_signals_t, {}) for k in IX]),
 "Double7": trades([(k, M5.prep(k), M5.d7, {"manage": M5.d7_manage}) for k in IX]),
 "TSMOM12": trades([(k, TF.prep(k), M5.tsmom, {}) for k in TF.SPREAD]),
}
tr = trades(TF.items); tr["y"] = tr.t.dt.year; tr["m"] = tr.t.dt.month; keep = []
for y in sorted(tr.y.unique()):
    past = tr[tr.y < y]; cur = tr[tr.y == y]
    if past.y.nunique() >= 8: mm = past.groupby("m").R.mean(); cur = cur[~cur.m.isin(set(mm[mm < 0].index))]
    keep.append(cur)
books["Trend+fallow"] = pd.concat(keep)
M = pd.DataFrame({k: v.groupby(v.t.dt.tz_convert(None).dt.to_period("M")).R.sum() for k, v in books.items()}).fillna(0)
M = M[M.index >= pd.Period("2001-01", "M")]
out = []
def p(s): print(s, flush=True); out.append(s)
p("Monthly correlation (ATR units):\n" + M.corr().round(2).to_string())
for k in M.columns: p(f"{k:13s} months + {100*(M[k]>0).mean():.0f}%  years + {int((M[k].groupby(M.index.year).sum()>0).sum())}/{M.index.year.nunique()}  worst month {M[k].min():+.1f}")
# equal weight by each book's own volatility so no one book dominates
w = 1 / M.std(); P = (M * w).sum(axis=1) / w.sum()
Y = P.groupby(P.index.year).sum()
p(f"COMBINED (risk-balanced) months + {100*(P>0).mean():.0f}%  years + {int((Y>0).sum())}/{len(Y)}  last 5 years: {', '.join(f'{y}:{v:+.1f}' for y, v in Y.tail(5).items())}")
p(f"worst 12 months combined {P.rolling(12).sum().min():+.1f} vs best book alone {min(M[k].rolling(12).sum().min() for k in M.columns):+.1f}")
open("runs/gate/portfolio_daily.txt", "w").write("\n".join(out) + "\n")
