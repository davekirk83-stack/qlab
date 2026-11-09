"""Doc 199 — parameter-neighbourhood robustness for the two long-history books (a cheap stand-in for PBO / CPCV):
if only the exact published settings work, the edge is fragile; if most nearby settings work, it is structural.
Trend (IG quarterly bets): breakout 50/100/200 days x trailing channel 20/50/100 x initial stop 2/3/4 ATR (27 variants).
RSI(2) pullback: entry RSI < 5/10/15/20 x trend filter 100/200 days x exit MA 3/5/10 (24 variants). Full 2000-2026, per-year positivity."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2, trend_futures_bets as TF
from gate_books import sigframe
out = []
def summ(lab, T):
    t = pd.DataFrame(T); y = t.groupby(pd.to_datetime(t.t).dt.year).R.sum(); last5 = t[pd.to_datetime(t.t).dt.year >= 2022].R.mean()
    s = f"{lab:38s} n{len(t):5d} mean {t.R.mean():+.3f} ATR t {t.R.mean()/t.R.std()*np.sqrt(len(t)):+.2f} | years + {int((y>0).sum())}/{len(y)} | last 5y {last5:+.3f}"
    print(s, flush=True); out.append(s); return t.R.mean()
TM = {k: TF.prep(k) for k in TF.SPREAD}
res_t = []
for bo in (50, 100, 200):
    for tr in (20, 50, 100):
        for sa in (2, 3, 4):
            T = []
            for k, d in TM.items():
                d = d.copy(); d["hi50"] = d.high.rolling(tr).max().shift(1); d["lo50"] = d.low.rolling(tr).min().shift(1)
                def sigs(x, bo=bo, sa=sa):
                    hh = x.high.rolling(bo).max().shift(1).values; ll = x.low.rolling(bo).min().shift(1).values; C = x.close.values; a = x.atr.values
                    s = np.where(C > hh, 1, np.where(C < ll, -1, 0)); ix = np.where((s != 0) & np.isfinite(a))[0]
                    return sigframe(x.index[ix], s[ix], "market", np.nan, sa * a[ix], np.nan, 10 ** 6, dist=True)
                T += G.simulate(d, sigs(d), M2.trend_manage)
            res_t.append(summ(f"TREND bo{bo} trail{tr} stop{sa}", T))
import market_search_4 as M4
res_r = []
for lvl in (5, 10, 15, 20):
    for f in (100, 200):
        for ex in (3, 5, 10):
            T = []
            for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD"):
                d = M2.daily(k, .0003, 0.06); d["ma5"] = d.close.rolling(ex).mean()
                C = d.close; ok = (C > C.rolling(f).mean()) & (M4.rsi2(C) < lvl) & d.atr.notna(); ix = np.where(ok.values)[0]
                sg = sigframe(d.index[ix], 1, "close", np.nan, 3 * d.atr.values[ix], np.nan, 10, dist=True)
                sg["target"] = (d["ma5"].values[ix] - C.values[ix]).clip(min=0.1 * d.atr.values[ix])
                T += G.simulate(d, sg)
            res_r.append(summ(f"RSI2 <{lvl} trend{f} exitMA{ex}", T))
s = f"TREND: {sum(m > 0 for m in res_t)}/{len(res_t)} variants positive | RSI2: {sum(m > 0 for m in res_r)}/{len(res_r)} variants positive"
print(s); out.append(s); open("runs/gate/robustness_daily.txt", "w").write("\n".join(out) + "\n")
