"""DK 27 Nov 18:33: "Look online for similar (but improved) trading strategies to glean information from". Ideas found, tested as published
where the source gives full rules (doc 275):
  Q1  Quantpedia 'Seasonal intraday anomalies in Bitcoin' (Gemini 2015-22): buy BTC 21:00 UTC, sell 23:00 UTC (strongest hours 22-23 UTC).
  Q2  Quantpedia 'How to profitably trade Bitcoin's overnight sessions': long at the NYSE close (16:00 New York) on Fri / Mon / Tue when BTC
      is at a 10-day high (daily bars), exit at 10:00 New York the next trading morning (Fri -> Mon 10:00).
  N1  Fire-sale / reversal literature (Nagel 2012 'Evaporating liquidity'; Coval & Stafford 2007): reversal premia concentrate in
      high-volatility, low-liquidity periods -> DK v2 longs only when BTC's 14-day ATR% is above its trailing 1-year median (and the reverse).
  C1  Connors 'ConnorsRSI pullbacks': limit entries Z% below the setup close; "the larger the intraday pullback, the greater the edge" ->
      DK v2 with the ladder started 0.3 / 0.6 daily-ATR lower (deeper first bid), everything else unchanged.
Data: Binance BTCUSDT 15-min 2021-26. Costs Revolut X: maker 0, taker 0.09% + 0.05% slip. Q1/Q2 tested both with market orders and
with a resting (maker) entry at the same time - the source quotes no costs."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dk_v2_all_charts as A, dk_v2_improve as I
d = A.coin("BTCUSDT"); U = d.index; O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values
def summ(r, lab):
    r = r.dropna(); h = len(r) // 2; y = r.groupby(r.index.year).sum()
    return dict(test=lab, n=len(r), win=round((r > 0).mean(), 3), mean_pct=round(100 * r.mean(), 4), h1=round(100 * r[:h].mean(), 4), h2=round(100 * r[h:].mean(), 4),
                yrs=" ".join(f"{k}:{100*v:+.0f}" for k, v in y.items()), total_pct=round(100 * r.sum(), 1))
rows = []
# Q1: 21:00 -> 23:00 UTC
s = pd.Series(O, index=U); e = s[(U.hour == 21) & (U.minute == 0)]; x = s.reindex(e.index + pd.Timedelta("2h"))
g = pd.Series(x.values / e.values - 1, index=e.index)
for lab, cost in (("Q1 BTC 21-23 UTC, gross", 0.0), ("Q1 net, market both ways", 2 * 0.0014), ("Q1 net, maker in / market out", 0.0014)):
    rows.append(summ(g - cost, lab))
# Q2: NYSE close (16:00 NY) -> next 10:00 NY, Fri/Mon/Tue, when BTC daily close is a 10-day high
ny = U.tz_convert("America/New_York"); dc = d.close.resample("1D").last(); hi10 = dc.rolling(10).max()
ent = np.where((ny.hour == 16) & (ny.minute == 0) & np.isin(ny.dayofweek, (0, 1, 4)))[0]; res = {}
for j in ent:
    day = U[j].floor("1D"); prev = dc.index.searchsorted(day) - 1
    if prev < 10: continue
    if dc.iloc[prev] < hi10.iloc[prev]: continue                           # yesterday's close at a 10-day high (known before the entry)
    tgt = (ny[j] + pd.Timedelta(days=3 if ny[j].dayofweek == 4 else 1)).normalize() + pd.Timedelta("10h")
    k = U.searchsorted(tgt.tz_convert("UTC"))
    if k >= len(O): continue
    res[U[j]] = O[k] / O[j] - 1
g2 = pd.Series(res)
for lab, cost in (("Q2 overnight MAX(10), gross", 0.0), ("Q2 net, market both ways", 2 * 0.0014), ("Q2 net, maker in / market out", 0.0014)):
    rows.append(summ(g2 - cost, lab))
# N1 / C1 on DK v2 (+ the 13:00 level kept in doc 274)
dl = d.close.resample("1D").last(); hi = d.high.resample("1D").max(); lo = d.low.resample("1D").min()
tr = np.maximum(hi - lo, np.maximum((hi - dl.shift()).abs(), (lo - dl.shift()).abs())); atrp = (tr.rolling(14).mean() / dl).shift(1); med = atrp.rolling(365, min_periods=120).median()
hv = (atrp > med)
base = I.run(d, {"ny": True}); rows.append(dict(summ(base / 100, "DK v2 + 13:00 level (current best)")))
for lab, keep in (("N1 v2 only when vol is HIGH (ATR% > 1y median)", True), ("N1 v2 only when vol is LOW", False)):
    m = hv.reindex(base.index.floor("1D")).fillna(False).values
    rows.append(summ((base[m] if keep else base[~m]) / 100, lab))
# C1: deeper first bid - shift the 24h-low level down by k x daily ATR% (patched into the improve engine through the lvl factor)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dk_v2_improve.py")).read()
for kdeep in (0.3, 0.6):
    code = src.replace("lvl = L[j - 96:j].min() * 0.997", f"lvl0 = L[j - 96:j].min() * 0.997; lvl = lvl0 * (1 - {kdeep} * a)").replace("if C[j - 1] > lvl * 1.03: continue", "if C[j - 1] > lvl0 * 1.03: continue")   # audit: same events, only the bids move
    ns = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "dk_v2_improve.py")}; exec(compile(code.split('if __name__ == "__main__":')[0], "c1", "exec"), ns)
    r = ns["run"](d, {"ny": True}); rows.append(summ(r / 100, f"C1 v2 + first bid {kdeep} x ATR deeper"))
R = pd.DataFrame(rows); R.to_csv("runs/research/online_ideas.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
