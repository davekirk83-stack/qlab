"""DK 21 Nov 14:56: "we need to consider using more size & risk, but with new ways to manage potential downside" / "Like avoiding the worst days".
Live daily core (RSI4L, TPS first rung, TOM; 7 indices + gold, 2000-2026) replayed at 1-5% risk per trade, with downside overlays:
 A  plain fixed-fraction risk
 B  drawdown ladder: half size at -8% from the equity high, quarter at -12%, pause 60 trading days at -15% (CAP-021 'back to paper')
 C  equity-curve filter: full size only while the book's own unsized equity is above its 20-trade average, else quarter size
 D  volatility scaling: risk x min(1, 20 / VIX)  (smaller in wild markets)
 E  B + C + D together, plus the doc-249 calendar sit-out (TOM / Monday after Thanksgiving) and the 2013+ CPI skip proxy n/a for daily
P&L per trade = risk x equity-at-entry x R (R = result in stop units); positions overlap (all books, all markets), 5x exposure ignored."""
import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, "src"); sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
import fifty_ideas as F
from events_test import run2
up = lambda d: d.close > d.close.rolling(200).mean(); r4 = lambda d: F.rsi(d.close, 4)
BOOKS = {"RSI4L": (lambda d: (up(d) & (r4(d) < 35), r4(d) > 55, 10, 3.0, "C"), 3.0),
         "TPS": (lambda d: (lambda r2: (up(d) & (r2 < 25) & (r2.shift(1) < 25), r2 > 70, 30, 5.0, "C"))(F.rsi(d.close, 2)), 5.0),
         "TOM": (lambda d: (pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index), None, 3, 5.0, "C"), 5.0)}
def tgmon(y): d0 = pd.Timestamp(y, 11, 1); return d0 + pd.Timedelta(days=(3 - d0.dayofweek) % 7 + 25)
TGM = {tgmon(y) for y in range(2000, 2028)}
rows = []
for b, (fn, stopatr) in BOOKS.items():
    for k in F.IXG:
        d = F.D[k]; e, x, md, st, how = fn(d); idx = d.index; pos = {t: i for i, t in enumerate(idx)}
        for t0, t1, R in run2(k, e, 1, x, md, st, how):
            i = pos[t0]; skip_cal = b == "TOM" and bool(set(idx[i+1:i+3]) & TGM)
            rows.append(dict(t0=t0, t1=t1, book=b, k=k, R=R / stopatr, cal=skip_cal))
T = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
VIX = F.D["VIX"].close
def sim(risk, B=False, Cf=False, D=False, cal=False, cap=None, start=1.0):
    eq = start; hi = start; pause_until = None; shadow = []; events = []   # (time, kind, idx)
    for i, r in T.iterrows(): events.append((r.t0, 0, i)); events.append((r.t1, 1, i))
    events.sort(); stake = {}; curve = []; sh = 0.0; shs = []
    for t, kind, i in events:
        r = T.loc[i]
        if kind == 0:
            m = 1.0
            if cal and r.cal: continue
            if B:
                dd = 1 - eq/hi
                if pause_until is not None and t < pause_until: continue
                if dd >= 0.15: pause_until = t + pd.offsets.BDay(60); hi = eq; continue
                m *= 0.25 if dd >= 0.12 else 0.5 if dd >= 0.08 else 1.0
            if Cf and len(shs) >= 20 and sh < np.mean(shs[-20:]): m *= 0.25
            if D:
                v = VIX.asof(t); m *= min(1.0, 20.0 / v) if np.isfinite(v) and v > 0 else 1.0
            if cap is not None and (sum(stake.values()) + risk * eq * m) > cap * eq: continue
            stake[i] = risk * eq * m
        else:
            sh += r.R; shs.append(sh)
            if i in stake:
                eq += stake.pop(i) * r.R; hi = max(hi, eq); curve.append((t, eq))
    c = pd.Series([e for _, e in curve], index=[t for t, _ in curve]); c = c[~c.index.duplicated(keep="last")]
    yrs = (c.index[-1] - c.index[0]).days / 365.25; cagr = (c.iloc[-1]/start) ** (1/yrs) - 1
    mdd = (1 - c / c.cummax()).max(); mon = c.resample("ME").last().pct_change().dropna()
    last5 = c[c.index >= c.index[-1] - pd.DateOffset(years=5)]; cagr5 = (last5.iloc[-1]/last5.iloc[0]) ** (1/5) - 1
    return cagr, mdd, mon.min(), cagr5, c
out = [f"Daily core trades 2000-2026: {len(T)} (RSI4L {sum(T.book=='RSI4L')}, TPS {sum(T.book=='TPS')}, TOM {sum(T.book=='TOM')}); mean {T.R.mean():+.3f}R per trade",
       "variant | risk/trade | CAGR | max drawdown | worst month | CAGR last 5y | £/yr on £500 | £/yr on £5,000 | return/DD"]
VAR = {"A plain": {}, "B DD ladder": dict(B=True), "C equity filter": dict(Cf=True), "D vol scaling": dict(D=True), "E all + calendar": dict(B=True, Cf=True, D=True, cal=True),
       "F open-risk cap 6%": dict(cap=0.06), "G cap 6% + DD ladder + cal": dict(cap=0.06, B=True, cal=True), "H cap 10% + DD ladder + cal": dict(cap=0.10, B=True, cal=True),
       "I cap 6% + vol + DD + cal": dict(cap=0.06, B=True, D=True, cal=True)}
best = []
for name, kw in VAR.items():
    for risk in (0.01, 0.02, 0.03, 0.04, 0.05):
        cg, md, wm, c5, _ = sim(risk, **kw)
        out.append(f"{name:17} | {risk:.0%} | {cg:+.1%} | {md:.1%} | {wm:+.1%} | {c5:+.1%} | £{500*cg:,.0f} | £{5000*cg:,.0f} | {cg/md if md else 0:.2f}")
        best.append((name, risk, cg, md))
open("runs/research/sizing_study.txt", "w").write("\n".join(out)); print("\n".join(out))
