"""L2WTrades claim (17 Nov 2026, relayed by DK): NQ entries at 9:30 ET win 41%; entries at 10:00 ET after reading the 06:00-10:00 ET 4h candle win 67%.
Mechanical version on data_nq_cache/nq_5m.csv (Oct 2025 - Nov 2026), cost 2 pts round trip:
  4h candle = 06:00-09:55 ET 5m bars. body ratio = |close-open| / range.
  EXPANSION (body ratio >= T): at 10:00 ET enter in the body direction; exit 10:30 ET (his 'done by 10:30') and, separately, 12:00 ET.
  Baseline '9:30 no profile': enter 9:30 ET in the direction of 06:00-09:25, exit 10:00 ET.
  REVERSAL days (body ratio < T): reported only."""
import pandas as pd, numpy as np
d = pd.read_csv("data_nq_cache/nq_5m.csv", parse_dates=["ts"]).set_index("ts").tz_convert("America/New_York")
d = d[d.index.dayofweek < 5]
COST = 2.0
rows = []
for day, g in d.groupby(d.index.date):
    g = g.between_time("06:00", "12:00")
    c4 = g.between_time("06:00", "09:55")
    if len(c4) < 44 or len(g.between_time("10:00", "12:00")) < 20: continue
    o, h, l, c = c4.open.iloc[0], c4.high.max(), c4.low.min(), c4.close.iloc[-1]
    rng = h - l
    if rng <= 0: continue
    ratio = abs(c - o) / rng; side = 1 if c > o else -1
    def px(t, col="open"):
        x = g.between_time(t, t); return None if x.empty else float(x[col].iloc[0])
    p930, p1000, p1030, p1200 = px("09:30"), px("10:00"), px("10:30"), px("12:00")
    pre = g.between_time("06:00", "09:25"); s930 = 1 if pre.close.iloc[-1] > pre.open.iloc[0] else -1
    if None in (p930, p1000, p1030, p1200): continue
    rows.append(dict(day=day, ratio=ratio, side=side, r930=s930 * (p1000 - p930) - COST,
                     r1030=side * (p1030 - p1000) - COST, r1200=side * (p1200 - p1000) - COST, rng=rng))
r = pd.DataFrame(rows)
def show(name, x):
    print(f"{name:42s} n={len(x):4d}  win {100*(x>0).mean():5.1f}%  avg {x.mean():+7.1f} pts  total {x.sum():+8.0f}")
print(f"days {len(r)}  {r.day.min()} .. {r.day.max()}\n")
show("9:30 entry, no profile, exit 10:00", r.r930)
show("10:00 entry in 4h direction, ALL days, 10:30", r.r1030)
for T in (0.5, 0.6, 0.7):
    e = r[r.ratio >= T]
    show(f"10:00 EXPANSION (body>={T}), exit 10:30", e.r1030)
    show(f"10:00 EXPANSION (body>={T}), exit 12:00", e.r1200)
    h1, h2 = e.iloc[:len(e)//2], e.iloc[len(e)//2:]
    print(f"{'':42s} halves 10:30: {h1.r1030.sum():+.0f} / {h2.r1030.sum():+.0f}")
show("10:00 REVERSAL days (body<0.5), 4h dir, 10:30", r[r.ratio < 0.5].r1030)
show("10:00 REVERSAL days (body<0.5), FADE, 10:30", -r[r.ratio < 0.5].r1030 - 2*COST)

print("\nFADE the 06:00-10:00 expansion at 10:00 ET (opposite to the body), cost 2 pts:")
for T in (0.5, 0.6, 0.7):
    e = r[r.ratio >= T]
    for col in ("r1030", "r1200"):
        f = -(e[col] + COST) - COST
        h = len(f)//2
        print(f"  body>={T} exit {'10:30' if col=='r1030' else '12:00'}: n={len(f)} win {100*(f>0).mean():.1f}% avg {f.mean():+.1f} pts  halves {f.iloc[:h].sum():+.0f} / {f.iloc[h:].sum():+.0f}")
