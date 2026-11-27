"""Own idea 1 (DK 27 Nov 16:52 "Create own potential strategies"): the overnight drift. Published finding (Cooper/Cliff/Gulen 2008;
Lou-Polk-Skouras 2019; Kelly-Clark 2011): nearly all US stock-index gains come close->open, intraday open->close is near zero.
Test: long at the cash close, out at the next cash open, daily, SPX / NDX / DJI 2000-26 (data_daily: open & close of the cash session).
Costs on IG spread bets: spread both ways (US500 0.4 pt, NQ 1.0, Wall St 2.4 at today's levels -> scaled as a % of price) + one night of
funding (~SONIA+2.5% a year / 365 = ~0.02%). Variants: every night; only above the 200-day; skip Fridays (weekend); only after a down day."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import market_search_2 as M2
SPREAD_PCT = {"SPX": 0.4 / 7000, "NDX": 1.0 / 25000, "DJI": 2.4 / 48000}; FUND = 0.065 / 365
def load(k):
    d = pd.read_csv(f"data_daily/{k}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d
rows = []
for k in ("SPX", "NDX", "DJI"):
    d = load(k).dropna(); c, o = d.close, d.open
    night = (o.shift(-1) / c - 1); day = (c / o - 1)
    cost = SPREAD_PCT[k] + FUND
    ma = c.rolling(200).mean(); up = c > ma; dn_day = c < c.shift(1); fri = d.index.dayofweek == 4
    for lab, mask in (("every night", pd.Series(True, index=d.index)), ("above 200-day", up), ("below 200-day", ~up), ("skip Fridays", ~pd.Series(fri, index=d.index)),
                      ("after a down day", dn_day), ("after a down day, above 200-day", dn_day & up)):
        r = (night - cost)[mask].dropna(); h = len(r) // 2; y = r.groupby(r.index.year).sum()
        rows.append(dict(mkt=k, rule=lab, n=len(r), win=round((r > 0).mean(), 3), mean_bp=round(r.mean() * 1e4, 2), h1_bp=round(r[:h].mean() * 1e4, 2),
                         h2_bp=round(r[h:].mean() * 1e4, 2), last5_bp=round(r[r.index.year >= 2022].mean() * 1e4, 2), yrs_pos=f"{(y>0).sum()}/{len(y)}",
                         ann_pct=round(r.mean() * 252 * 100 * mask.mean(), 1), sharpe=round(r.mean() / r.std() * np.sqrt(252 * mask.mean()), 2)))
    rd = (day - SPREAD_PCT[k]).dropna(); rows.append(dict(mkt=k, rule="(compare) intraday open->close", n=len(rd), win=round((rd > 0).mean(), 3), mean_bp=round(rd.mean() * 1e4, 2),
                     h1_bp=round(rd[:len(rd)//2].mean() * 1e4, 2), h2_bp=round(rd[len(rd)//2:].mean() * 1e4, 2), last5_bp=round(rd[rd.index.year >= 2022].mean() * 1e4, 2)))
R = pd.DataFrame(rows); R.to_csv("runs/research/overnight_drift.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
