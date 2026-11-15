"""15 Nov: Williams volatility breakout per market and k (DK: regular earners across lots of markets). champions_intraday sessions/costs.
Bracket open +/- k x previous session range, stop = other side (2k x range), flat at the cash close. £ at live stakes: 3% of £500 = £15
risked at the stop -> £/trade ~ 15 x R / (2k) (R = pts / 10-day average range, ~ previous range)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import champions_intraday as C
def run_k(m, S, d, k, cm=1.0):
    out = []; g = dict(tuple(d.groupby("day")))
    for day, r in S.iterrows():
        if not np.isfinite(r.avg10) or not np.isfinite(r.prng) or day not in g: continue
        b = g[day]; bars = (b.open.values, b.high.values, b.low.values, b.close.values); a = k * r.prng
        res = C.bracket(bars, r.o + a, r.o - a, r.o - a, r.o + a)
        if res: s, e, x = res; pts = s * (x - e) - cm * r.cost; out.append((pd.Timestamp(day), pts, pts / r.avg10))
    return pd.DataFrame(out, columns=["t", "pts", "R"])
rows = []
for m in ["NQ", "US500", "DOW", "DAX", "FTSE", "GOLD", "GOLD5Y", "GBPUSD", "USDJPY"]:
    try: d, S = C.sessions(m)
    except Exception as ex: print(m, "no data", ex); continue
    wk = len(S) / 5
    for k in (0.2, 0.3, 0.4, 0.5, 0.6):
        t = run_k(m, S, d, k)
        if len(t) < 20: continue
        t15 = run_k(m, S, d, k, 1.5); gbp = 15 * t.R / (2 * k); wkly = gbp.groupby(t.t.dt.to_period("W")).sum()
        half = len(t) // 2
        rows.append(dict(m=m, k=k, n_wk=len(t) / wk, win=(t.pts > 0).mean(), gbp_trade=gbp.mean(), gbp_wk=gbp.sum() / wk,
                         wks_pos=(wkly > 0).mean(), h1=t.R[:half].mean(), h2=t.R[half:].mean(), c15=t15.R.mean(), months=f"{len(S)//21}"))
r = pd.DataFrame(rows); r.to_csv("runs/sweep/williams_mkts.csv", index=False)
pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
