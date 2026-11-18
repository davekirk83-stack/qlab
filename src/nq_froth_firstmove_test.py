"""DK's NY-open model (18 Nov 2026): "the first 5 minutes [froth], then the first move (30-40 mins), then reversals."
NQ 5m (data_nq_cache, Oct 2025-Nov 2026), New York time, cost 2 pts round trip.
  froth = 09:30 bar; first move = 09:35 open -> 10:05/10:10 close; reversal trade = fade the first move from the end of it."""
import pandas as pd, numpy as np
d = pd.read_csv("data_nq_cache/nq_5m.csv", parse_dates=["ts"]).set_index("ts").tz_convert("America/New_York")
d = d[d.index.dayofweek < 5]; COST = 2.0
def at(g, t, col):
    x = g.between_time(t, t); return None if x.empty else float(x[col].iloc[0])
out = []
for day, g in d.groupby(d.index.date):
    g = g.between_time("09:30", "16:00")
    if len(g) < 70: continue
    fo, fc = at(g, "09:30", "open"), at(g, "09:30", "close")
    m0 = at(g, "09:35", "open")
    if None in (fo, fc, m0): continue
    rec = dict(day=day, froth=np.sign(fc - fo))
    for end in ("10:00", "10:05", "10:10"):          # first move ends at the close of this bar (35-45 min after the open)
        m1 = at(g, end, "close")
        if m1 is None: break
        rec[f"move_{end}"] = m1 - m0
        nxt = (pd.Timestamp(f"2000-01-01 {end}") + pd.Timedelta(minutes=5)).strftime("%H:%M")
        e = at(g, nxt, "open")
        for ex in ("11:00", "12:00", "15:55"):
            x = at(g, ex, "close" if ex == "15:55" else "open")
            rec[f"fade_{end}_{ex}"] = np.nan if (x is None or e is None) else -np.sign(m1 - m0) * (x - e) - COST
    out.append(rec)
r = pd.DataFrame(out).dropna()
print(f"days {len(r)}  {r.day.min()} .. {r.day.max()}")
for end in ("10:00", "10:05", "10:10"):
    mv = r[f"move_{end}"]
    print(f"\nfirst move 09:35->{end}: froth opposite to the first move on {100*(np.sign(mv)!=r.froth).mean():.0f}% of days; median |move| {mv.abs().median():.0f} pts")
    for big in (0, 50, 100):
        s = r[mv.abs() >= big]
        for ex in ("11:00", "12:00", "15:55"):
            f = s[f"fade_{end}_{ex}"]; h = len(f)//2
            print(f"  |move|>={big:3d}  fade to {ex}: n={len(f):3d} win {100*(f>0).mean():5.1f}% avg {f.mean():+6.1f} pts  halves {f.iloc[:h].sum():+6.0f} / {f.iloc[h:].sum():+6.0f}")
