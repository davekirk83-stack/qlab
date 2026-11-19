"""19-year-old's '9:30-10:30 premarket box' system (DK relayed 19 Nov 2026), tested mechanically on NQ 5m (data_nq_cache, Oct 2025-Nov 2026).
Rules as written, adapted to NQ futures (no options), cost 2 pts round trip:
  daily filter: previous daily close vs daily 8 EMA (RTH closes) -> only longs above, only shorts below.
  box: premarket high/low 04:00-09:25 ET.
  trigger: first 5m bar from 09:30 whose BODY closes outside the box in the filter's direction (by 10:25).
  entry: retest -- a later bar trades back to the level (PMH for longs, or VWAP if VWAP is beyond PMH); fill at that level.
  stop: a 5m CLOSE back through the entry level (exit at that close).
  target: new high/low of day reached -> exit 75% there (approximated: exit all at the prior HOD/LOD + 0); runner ignored.
  time stop: 10:30 ET close.  One trade a day; after a loss, no more trades (only one trade anyway)."""
import pandas as pd, numpy as np
d = pd.read_csv("data_nq_cache/nq_5m.csv", parse_dates=["ts"]).set_index("ts").tz_convert("America/New_York")
d = d[d.index.dayofweek < 5]
rth = d.between_time("09:30", "15:55")
dc = rth.close.groupby(rth.index.date).last()
ema8 = dc.ewm(span=8, adjust=False).mean()
COST = 2.0; res = []
days = sorted(set(d.index.date))
for i, day in enumerate(days):
    if i == 0 or days[i-1] not in dc.index: continue
    prev = days[i-1]
    side = 1 if dc[prev] > ema8[prev] else -1
    g = d[d.index.date == day]
    pm = g.between_time("04:00", "09:25"); s = g.between_time("09:30", "10:30")
    if len(pm) < 40 or len(s) < 12: continue
    pmh, pml = pm.high.max(), pm.low.min()
    tp = (s.high + s.low + s.close) / 3; vw = (tp * s.vol).cumsum() / s.vol.cumsum()
    trig = None
    for j in range(len(s)):
        b = s.iloc[j]
        if s.index[j].strftime("%H:%M") > "10:25": break
        if side == 1 and min(b.open, b.close) > pmh: trig = j; break
        if side == -1 and max(b.open, b.close) < pml: trig = j; break
    if trig is None: continue
    hod, lod = s.high.iloc[:trig+1].max(), s.low.iloc[:trig+1].min()
    lvl0 = pmh if side == 1 else pml
    entry = None
    for k in range(trig + 1, len(s)):
        b = s.iloc[k]; lvl = max(lvl0, vw.iloc[k]) if side == 1 else min(lvl0, vw.iloc[k])
        if entry is None:
            if (side == 1 and b.low <= lvl) or (side == -1 and b.high >= lvl):
                entry, lvl_e = lvl, lvl
                if (side == 1 and b.close < lvl_e) or (side == -1 and b.close > lvl_e):
                    res.append((day, side * (b.close - entry) - COST, "stop")); break
            continue
        tgt = hod if side == 1 else lod
        if (side == 1 and b.high >= tgt) or (side == -1 and b.low <= tgt):
            res.append((day, side * (tgt - entry) - COST, "HOD")); break
        if (side == 1 and b.close < lvl_e) or (side == -1 and b.close > lvl_e):
            res.append((day, side * (b.close - entry) - COST, "stop")); break
        if s.index[k].strftime("%H:%M") >= "10:30":
            res.append((day, side * (b.close - entry) - COST, "time")); break
r = pd.DataFrame(res, columns=["day", "pts", "exit"])
print(f"days tested {len(days)}; trades {len(r)}")
if len(r):
    h = len(r)//2
    print(f"win {100*(r.pts>0).mean():.1f}%  avg {r.pts.mean():+.1f} pts  total {r.pts.sum():+.0f}  avg win {r.pts[r.pts>0].mean():+.1f}  avg loss {r.pts[r.pts<=0].mean():+.1f}")
    print(f"halves {r.pts.iloc[:h].sum():+.0f} / {r.pts.iloc[h:].sum():+.0f}")
    print(r.exit.value_counts().to_dict())
    r["m"] = pd.to_datetime(r.day).dt.to_period("M"); print(r.groupby("m").pts.agg(["count","sum"]).round(0).T.to_string())
