"""16 Nov (DK: the crash-alert level should drive trading more directly; add a GOLD level, "a historic buying opportunity window").
Rebuilds GREEN / AMBER / RED / GOLD from history (S&P 500 since 1928, VIX since 1990 — before that a 20-day realised-vol proxy, US 10y since 1962)
and measures (1) S&P forward returns by level, (2) every GOLD episode vs the eventual low, (3) the daily dip books (RSI4 + RSI4L, 8 markets) by level.
RED  = trend broken (last month-end close below its 10-month average, or 10%+ below the 252-day high)
       AND stress (VIX > 30 on 2 of the last 5 days, or the 10y above 5% for 20+ days AND rising 1 pt+ over a year).
GOLD = after real damage (S&P 20%+ below its high at some point in the last 12 months), the turn confirmed by
       (a) a month-end close back above the 10-month average, or (b) VIX back below 25 within 60 days of being above 40.
       Lasts 6 months, ends early on a new RED.  (The central-bank EXIT trigger has no clean history and is not used.)
AMBER = not RED/GOLD, and (close below the 200-day, or VIX >= 22).  GREEN = everything else."""
import json, os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
Y = "data_long/yahoo"
def y(sym):
    r = json.load(open(f"{Y}/{sym}.json"))["chart"]["result"][0]
    s = pd.Series(r["indicators"]["quote"][0]["close"], index=pd.to_datetime(r["timestamp"], unit="s").normalize()).dropna()
    return s[~s.index.duplicated()]
spx, vix, tnx = y("%5EGSPC"), y("%5EVIX"), y("%5ETNX")
d = pd.DataFrame({"c": spx}); d["vix"] = vix.reindex(d.index).ffill(limit=3)
rv = np.log(d.c).diff().rolling(20).std() * np.sqrt(252) * 100 * 1.15
d["vol"] = d.vix.where(d.vix.notna(), rv)                     # VIX, or a realised-vol proxy before 1990
d["y10"] = tnx.reindex(d.index).ffill()
me = d.c.resample("ME").last(); ma10 = me.rolling(10).mean()
below10 = (me < ma10).reindex(d.index, method="ffill")        # as of the last COMPLETED month-end
hi = d.c.rolling(252, min_periods=60).max(); dd = d.c / hi - 1
d["trend_broken"] = below10.fillna(False) | (dd <= -0.10)
stress_v = (d.vol > 30).rolling(5).sum() >= 2
y5 = (d.y10 > 5).rolling(20).sum() >= 20; yrise = d.y10 - d.y10.shift(252) >= 1.0
d["stress"] = stress_v | (y5 & yrise.fillna(False))
d["red"] = d.trend_broken & d.stress
d["ma200"] = d.c.rolling(200).mean()
# GOLD
dmg = (dd <= -0.20).rolling(252, min_periods=1).max().astype(bool)
reclaim = ((me > ma10) & (me.shift(1) <= ma10.shift(1))).reindex(d.index, method="ffill", limit=22).fillna(False)
reclaim_day = reclaim & ~reclaim.shift(1, fill_value=False)
vixcalm = (d.vol < 25) & (d.vol > 40).rolling(60).max().astype(bool) & ~((d.vol.shift(1) < 25) & (d.vol > 40).shift(1).rolling(60).max().fillna(0).astype(bool))
trig = dmg & (reclaim_day | vixcalm)
gold = np.zeros(len(d), bool); until = -1; idx = np.arange(len(d)); red = d.red.values; tr = trig.values
starts = []
for i in range(len(d)):
    if red[i]: until = -1
    if tr[i] and until < i: until = i + 126; starts.append(d.index[i])
    if i <= until and not red[i]: gold[i] = True
d["gold"] = gold
d["level"] = np.where(d.red, "RED", np.where(d.gold, "GOLD", np.where((d.c < d.ma200) | (d.vol >= 22), "AMBER", "GREEN")))
d = d[d.index >= "1929-01-01"]
for h, nm in ((21, "1m"), (63, "3m"), (252, "12m"), (756, "3y")): d[nm] = d.c.shift(-h) / d.c - 1
print("== share of days and S&P forward returns by level (1929-2026)")
g = d.groupby("level"); out = pd.DataFrame({"share": g.size() / len(d), "fwd1m": g["1m"].mean(), "fwd3m": g["3m"].mean(), "fwd12m": g["12m"].mean(),
                                           "12m_up": g["12m"].apply(lambda x: (x.dropna() > 0).mean()), "fwd3y": g["3y"].mean()})
print((out * 100).round(1).to_string())
for era in (("1990", "2026"),):
    e = d[d.index >= era[0]]; g = e.groupby("level")
    print(f"\n  since {era[0]} (real VIX):", ((pd.DataFrame({'share': g.size() / len(e), 'fwd3m': g['3m'].mean(), 'fwd12m': g['12m'].mean()})) * 100).round(1).to_dict("index"))
print("\n== GOLD episodes: start vs the low of the preceding fall, and what followed")
rows = []
for s in starts:
    if s < pd.Timestamp("1929-06-01"): continue
    win = d.c[s - pd.Timedelta(days=400):s]; low_t = win.idxmin(); low = win.min()
    f = lambda n: d.c.shift(-n).get(s, np.nan) / d.c[s] - 1
    later_low = d.c[s:s + pd.Timedelta(days=365)].min() / d.c[s] - 1
    rows.append(dict(start=s.date(), days_after_low=(s - low_t).days, above_low=d.c[s] / low - 1, worse_low_next_12m=later_low,
                     fwd1y=f(252), fwd3y=f(756), fwd5y=f(1260)))
G = pd.DataFrame(rows); pd.set_option("display.width", 200)
print(G.round(3).to_string(index=False)); print("median:", G[["days_after_low", "above_low", "worse_low_next_12m", "fwd1y", "fwd3y", "fwd5y"]].median().round(3).to_dict())
print("all-days median fwd1y/3y/5y:", round(d["12m"].median(), 3), round(d["3y"].median(), 3), round((d.c.shift(-1260) / d.c - 1).median(), 3))
# daily books by level at entry
try:
    import sweep_daily_freq as W, fifty_ideas as F
    t = pd.concat([W.trades(F.IXG, 25, "200d", 55), W.trades(F.IXG, 35, "200d", 55)])
    t["level"] = d.level.reindex(t.t.dt.normalize().values, method="ffill").values
    print("\n== daily dip books (RSI4 + RSI4L, 8 markets, 2000-2026) by alert level at entry (£ at £10 risk per 3-ATR stop)")
    b = t.groupby("level").R.agg(["count", "mean", lambda x: (x > 0).mean()]); b.columns = ["trades", "R", "win"]; b["gbp_trade"] = b.R / 3 * 10
    print(b.round(3).to_string())
except Exception as ex: print("books:", ex)
d[["c", "vol", "y10", "level"]].to_csv("runs/sweep/alert_levels_daily.csv")
print("\nlevel now:", d.level.iloc[-1], d.index[-1].date())
