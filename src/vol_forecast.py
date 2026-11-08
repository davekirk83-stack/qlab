"""Doc 191 — VOLATILITY FORECAST (descriptive): which morning facts tell you a session will be a big-range / spike day?
US Tech 100 cash sessions, A = 2020-21, B = 2025-26. Target: session range >= 1.5x its 20-session mean ('big day').
Inputs known by 10:00 NY: overnight gap (open vs prior close, in units of the 20-day mean range), first-30-min range vs its 20-day mean,
prior-day range vs mean, prior VIX close, and the 5-day compression (5-day mean range / 20-day)."""
import json, numpy as np, pandas as pd
OUT = open("runs/vol_forecast.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
vj = json.load(open("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/VIX.json"))["chart"]["result"][0]
VIX = pd.Series(vj["indicators"]["quote"][0]["close"], index=pd.to_datetime(vj["timestamp"], unit="s").date).dropna()
def days(f, start):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[d.index >= start]
    lt = d.index.tz_convert("America/New_York"); mins = lt.hour * 60 + lt.minute; d = d[(mins >= 570) & (mins < 960)].copy()
    d["day"] = d.index.tz_convert("America/New_York").date; d["m"] = (d.index.tz_convert("America/New_York").hour * 60 + d.index.tz_convert("America/New_York").minute) - 570
    g = d.groupby("day"); D = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last(),
        "or30": d[d.m < 30].groupby("day").apply(lambda x: x.high.max() - x.low.min())})
    D["rng"] = D.h - D.l; D["mr"] = D.rng.shift(1).rolling(20).mean()
    D["big"] = D.rng >= 1.5 * D.mr; D["gap"] = (D.o - D.c.shift(1)).abs() / D.mr
    D["or_x"] = D.or30 / D.or30.shift(1).rolling(20).mean(); D["prev_x"] = D.rng.shift(1) / D.mr
    D["comp"] = D.rng.shift(1).rolling(5).mean() / D.mr
    D["vix"] = [VIX[VIX.index < k].iloc[-1] if (VIX.index < k).any() else np.nan for k in D.index]
    return D.dropna()
for tag, f, st in (("A 2020-21", "data_long/nq_5m_2020_21.csv", "2020-01-01"), ("B 2025-26", "data_nq_cache/nq_5m.csv", "2025-10-15")):
    D = days(f, st); log(f"\n[{tag}] {len(D)} sessions, big days {100*D.big.mean():.0f}%")
    for col, bins, lab in (("or_x", [0, .8, 1.2, 1.6, 2.2, 99], "first-30-min range vs normal"), ("gap", [0, .1, .25, .5, 99], "overnight gap (x mean range)"),
                           ("prev_x", [0, .8, 1.2, 1.6, 99], "yesterday's range vs normal"), ("vix", [0, 16, 20, 25, 30, 99], "prior VIX close"), ("comp", [0, .8, 1.0, 1.2, 99], "5-day compression")):
        c = pd.cut(D[col], bins); t = D.groupby(c, observed=True).big.agg(["mean", "size"])
        log(f"  {lab:30} " + "  ".join(f"{str(k):12} {100*v['mean']:3.0f}% (n{int(v['size'])})" for k, v in t.iterrows()))
    hot = (D.or_x >= 1.6) | (D.gap >= .5)
    log(f"  RULE 'first 30 min >= 1.6x normal OR gap >= 0.5x range': flags {100*hot.mean():.0f}% of sessions, catches {100*D.big[hot].sum()/max(D.big.sum(),1):.0f}% of big days; P(big | flagged) {100*D.big[hot].mean():.0f}% vs {100*D.big[~hot].mean():.0f}% otherwise")
