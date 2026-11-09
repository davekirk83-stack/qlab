"""Doc 200 — DK 9 Nov 23:03: "I still think we can fix our range / ladder book". The published ladders that work (Connors' TPS, grid
literature: Taranto 2020 / Quantpedia grid primer) share three things our 15-min ladder lacked: (1) a timeframe where mean reversion exists
(daily, equity indices), (2) a trend/regime gate (above the 200-day; grids die in steady trends), (3) finite, restartable episodes with a
kill rule. TPS (Connors & Alvarez, 'High Probability ETF Trading', 2009): price above its 200-day average and RSI(2) < 25 two days running
-> buy 10% of the budget at the close; each later close BELOW the last entry price adds 20%, 30%, 40%; exit at the close when RSI(2) > 70.
Honest by construction: every decision uses the close that has just printed, orders fill at that close + costs (as our daily books).
Added kill rules (grid literature): max 30 days, and an episode stop at -15% on the average cost. Measured per episode as % of the full budget.
Markets: 7 indices + gold (IG daily bets, 0.03% costs + 6%/yr funding), and 10 crypto coins spot long-only (Revolut X-style 0.2%, no funding)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import market_search_2 as M2, market_search_4 as M4
from gate_books import crypto15
def tps(d, cost, fund_yr, rsi_in=25, maxd=30, kill=0.15, ladder=(0.1, 0.2, 0.3, 0.4)):
    C = d.close.values; r = M4.rsi2(d.close).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 1:
        if not (C[i] > ma[i] and r[i] < rsi_in and r[i - 1] < rsi_in): i += 1; continue
        qty, spent, last, k, j0 = 0.0, 0.0, None, 0, i
        j = i
        while j < n:
            if k < len(ladder) and (last is None or C[j] < last):
                w = ladder[k]; qty += w / (C[j] * (1 + cost)); spent += w; last = C[j]; k += 1
            avg = spent / qty
            done = r[j] > 70 or (j - j0) >= maxd or C[j] <= avg * (1 - kill)
            if done and j > j0:
                val = qty * C[j] * (1 - cost) - spent * fund_yr / 365 * 1.4 * (j - j0) * 0.5
                out.append((d.index[j0], val - spent, spent, j - j0)); break
            j += 1
        i = j + 1
    return out
def report(name, E):
    t = pd.DataFrame(E, columns=["t", "pnl", "used", "days"]); t["y"] = t.t.dt.year; y = t.groupby("y").pnl.sum()
    s = t.pnl.std(ddof=1); tt = t.pnl.mean() / s * np.sqrt(len(t)) if s > 0 else 0
    last5 = t[t.y >= 2022].pnl.mean(); last1 = t[t.t >= t.t.max() - pd.Timedelta(days=365)].pnl.mean()
    print(f"{name:44s} episodes {len(t):4d} ({len(t)/max(y.size,1):.0f}/yr) mean {100*t.pnl.mean():+.3f}% of budget t {tt:+.2f} win {100*(t.pnl>0).mean():.0f}% "
          f"worst {100*t.pnl.min():+.1f}% | years + {int((y>0).sum())}/{y.size} | last 5y {100*last5:+.3f}% | last year {100*last1:+.3f}%", flush=True)
    return t
IX = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")
if __name__ == "__main__":
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06)) for k in IX]; report("TPS ladder, 7 indices + gold (IG)", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, ladder=(1.0,))) for k in IX]; report("same entry, ALL-IN at once (no ladder)", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, kill=9.9, maxd=10 ** 6)) for k in IX]; report("TPS without kill rules", E)
    CR = ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "ADAUSD", "LTCUSD", "DOTUSD")
    def cday(s): return crypto15(s).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    CD = {s: cday(s) for s in CR if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")}
    E = []; [E.extend(tps(d, .002, 0)) for d in CD.values()]; report("TPS ladder, 10 coins spot (Revolut X)", E)
    E = []; [E.extend(tps(d, .002, 0, ladder=(1.0,))) for d in CD.values()]; report("coins, ALL-IN at once", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, rsi_in=30)) for k in IX]; report("TPS indices, RSI<30", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, rsi_in=20)) for k in IX]; report("TPS indices, RSI<20", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, maxd=20)) for k in IX]; report("TPS indices, max 20 days", E)
    E = []; [E.extend(tps(d, .002, 0, rsi_in=20)) for d in CD.values()]; report("TPS coins, RSI<20", E)
    E = []; [E.extend(tps(d, .002, 0, rsi_in=30)) for d in CD.values()]; report("TPS coins, RSI<30", E)
    E = []; [E.extend(tps(d, .002, 0, kill=0.10)) for d in CD.values()]; report("TPS coins, kill at -10%", E)
    E = []; [E.extend(tps(d, .002, 0, kill=9.9, maxd=10 ** 6)) for d in CD.values()]; report("TPS coins, no kill rules", E)
    E = []; [E.extend(tps(d, .002, 0, maxd=20)) for d in CD.values()]; report("TPS coins, max 20 days", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, kill=0.10)) for k in IX]; report("TPS indices, kill at -10%", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, maxd=45)) for k in IX]; report("TPS indices, max 45 days", E)
    E = []; [E.extend(tps(d, .002, 0, maxd=45)) for d in CD.values()]; report("TPS coins, max 45 days", E)
    E = []; [E.extend(tps(M2.daily(k, .0003, 0), .0003, 0.06, kill=0.20)) for k in IX]; report("TPS indices, kill at -20%", E)
    E = []; [E.extend(tps(d, .002, 0, kill=0.20)) for d in CD.values()]; report("TPS coins, kill at -20%", E)
