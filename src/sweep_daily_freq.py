"""15 Nov (DK 14 Nov: "if our very best books never actually trade, look at them again to refine the settings so that they do!").
RSI(4) dip book swept looser: RSI threshold, trend filter, exit level, market set. Next-open in/out (review2_fixes.run_o), stop 3 ATR,
costs = fifty_ideas.COST (gate costs, more than IG's real spread), funding charged. £ at live stakes: 2% of £500 = £10 risked at the 3-ATR stop,
so £/trade = R/3 x £10. Reports trades/yr, win, mean R, £/yr, years positive, last 5y and last 12m £/yr."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF
IXG = F.IXG; WIDE = [k for k in F.COST if k not in ("TNOTE", "NATGAS")]
def rsi(d, n): return F.rsi(d.close, n)
def trades(mk, th, filt, ex, n=4, maxd=10):
    out = []
    for k in mk:
        d = F.D[k]; r = rsi(d, n)
        f = {"200d": d.close > d.close.rolling(200).mean(), "100d": d.close > d.close.rolling(100).mean(), "none": pd.Series(True, index=d.index),
             "50>200": d.close.rolling(50).mean() > d.close.rolling(200).mean()}[filt]
        for t, R in RF.run_o(k, f & (r < th), r > ex, maxd, 3.0): out.append((t, R, k))
    return pd.DataFrame(out, columns=["t", "R", "m"])
def summ(t, start="2000-01-01"):
    t = t[t.t >= start]; yrs = (t.t.max() - pd.Timestamp(start)).days / 365.25
    g = t.groupby(t.t.dt.year).R.sum(); last5 = t[t.t >= t.t.max() - pd.Timedelta(days=5 * 365)]; last1 = t[t.t >= t.t.max() - pd.Timedelta(days=365)]
    gbp = lambda x: x.R.sum() / 3 * 10
    return dict(n_yr=len(t) / yrs, win=(t.R > 0).mean(), R=t.R.mean(), gbp_yr=gbp(t) / yrs, yrs_pos=f"{(g > 0).sum()}/{len(g)}",
                gbp5=gbp(last5) / 5, gbp1=gbp(last1))
if __name__ == "__main__":
    rows = []
    for mkn, mk in (("8 idx+gold", IXG), ("16 wide", WIDE)):
        for th, filt, ex in itertools.product((25, 30, 35, 40), ("200d", "50>200", "100d", "none"), (55, 50)):
            s = summ(trades(mk, th, filt, ex)); rows.append(dict(markets=mkn, rsi_lt=th, filt=filt, exit_gt=ex, **s))
    r = pd.DataFrame(rows); r.to_csv("runs/sweep/rsi4_sweep.csv", index=False)
    pd.set_option("display.width", 250); print(r.round(3).sort_values("gbp_yr", ascending=False).head(25).to_string(index=False))
    print("\nlive setting now:"); print(r[(r.markets == "8 idx+gold") & (r.rsi_lt == 25) & (r.filt == "200d") & (r.exit_gt == 55)].round(3).to_string(index=False))
