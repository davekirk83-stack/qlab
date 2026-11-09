"""Doc 199 — DK 9 Nov 22:41: let a book "go fallow" in its bad months instead of killing it. Honest version (walk-forward):
for each year Y, the months to skip are chosen ONLY from the years before Y (a month is skipped if its average result over all earlier
years is negative, with at least 8 earlier years); then year Y is traded with that calendar. Compared with trading every month."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
B = {"TREND100 IG quarterly bets": "runs/gate/TREND100_IG_quarterly_bets_18_markets_trades.csv",
     "TURN-OF-MONTH 6 indices": "runs/gate/TURN-OF-MONTH_6_indices_trades.csv"}
import gate as G, market_search_4 as M4   # noqa (RSI2 trades are recomputed below)
rs = []
for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD"):
    d = M4.prep_rsi(k); tr = G.simulate(d, M4.rsi_signals_t(d)); rs += [dict(x, mkt=k) for x in tr]
pd.DataFrame(rs).to_csv("runs/gate/RSI2_8_markets_trades.csv", index=False); B["RSI2 pullback 8 markets"] = "runs/gate/RSI2_8_markets_trades.csv"
out = []
for name, f in B.items():
    t = pd.read_csv(f, parse_dates=["t"]); t["y"] = t.t.dt.year; t["m"] = t.t.dt.month
    rows = []
    for y in sorted(t.y.unique()):
        past = t[t.y < y]
        if past.y.nunique() < 8: continue
        mm = past.groupby("m").R.mean(); off = set(mm[mm < 0].index)
        cur = t[t.y == y]; on = cur[~cur.m.isin(off)]
        rows.append(dict(y=y, all=cur.R.sum(), seasonal=on.R.sum(), n_all=len(cur), n_on=len(on), off=",".join(str(m) for m in sorted(off))))
    r = pd.DataFrame(rows)
    line = (f"{name}: years {len(r)} | every month: total {r['all'].sum():+.1f} ATR, positive years {(r['all']>0).sum()}/{len(r)} | "
            f"seasonal switch: total {r.seasonal.sum():+.1f} ATR, positive years {(r.seasonal>0).sum()}/{len(r)}, trades kept {r.n_on.sum()}/{r.n_all.sum()} | "
            f"last 5 years every month {r['all'].tail(5).sum():+.1f} vs seasonal {r.seasonal.tail(5).sum():+.1f} | months off in 2026: {r.off.iloc[-1] or 'none'}")
    print(line, flush=True); out.append(line); r.to_csv(f"runs/gate/seasonal_{name.replace(' ', '_')}.csv", index=False)
open("runs/gate/seasonal_switch.txt", "w").write("\n".join(out) + "\n")
