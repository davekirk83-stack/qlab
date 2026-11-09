"""Doc 197 addendum — the daily 100-day breakout trend book traded as IG QUARTERLY (futures) spread bets instead of daily funded bets.
No overnight funding; instead: forward spread (about 2x the daily spread), one spread per quarterly roll (every 63 trading days held),
and the futures basis: index longs pay ~(rates - dividends) ~2.5%/yr and shorts earn it; FX and commodities: no basis adjustment
(commodities are Yahoo continuous futures already). Same rules as market_search_2 D. Reported through THE GATE + year by year."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M
SPREAD = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003, "SILVER": .0008, "OIL": .0008,
          "COPPER": .0010, "NATGAS": .0020, "GBPUSD": .0001, "EURUSD": .0001, "USDJPY": .0001, "AUDUSD": .0001, "USDCAD": .0002, "TNOTE": .0003}
IDX = {"SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225"}
def prep(k, basis=0.025):
    d = M.daily(k, 2 * SPREAD[k], 0.0).drop(columns=["carry"])
    b = basis / 365 * 1.4 if k in IDX else 0.0
    d["carry_long"] = d.close * b; d["carry_short"] = -d.close * b; d["roll_every"] = 63
    return d
items = [(k, prep(k), M.trend_signals, {"manage": M.trend_manage}) for k in SPREAD]
r = G.judge_pool("TREND100 IG quarterly bets 18 markets", items); print(G.line(r), "| by market", r.get("by_market"), flush=True)
t = pd.read_csv(f"{G.OUT}/TREND100_IG_quarterly_bets_18_markets_trades.csv", parse_dates=["t"]); t["y"] = t.t.dt.year
g = t.groupby("y").agg(n=("R", "size"), sum=("R", "sum"), mean=("R", "mean"))
print(g.round(2).to_string()); print("positive years", int((g["sum"] > 0).sum()), "of", len(g))
for lab, s in (("2000-2025 (dev)", t[t.y <= 2025]), ("last 5 years 2022-26", t[t.y >= 2022]), ("all", t)):
    print(f"{lab}: n{len(s)} mean {s.R.mean():+.3f} ATR/trade, t {s.R.mean()/s.R.std()*np.sqrt(len(s)):+.2f}, ex-2020 {s[s.y != 2020].R.mean():+.3f}")
open(f"{G.OUT}/trend_futures_bets.txt", "w").write(G.line(r) + "\n" + g.round(2).to_string() + "\n")
