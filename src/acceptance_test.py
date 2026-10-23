"""Acceptance vs rejection at session extremes (XO filter 5, queued doc 123).
For each day: London (07-13 UTC) high/low. In NY hours (13-20 UTC) the first 1-min bar whose high/low reaches the level.
Dwell = number of the next 10 one-minute closes beyond the level (0 = instant rejection, 10 = full acceptance).
Outcome = move 60 minutes after the tag, in the breakout direction, as % of the level (positive = continued beyond, negative = came back)."""
import numpy as np, pandas as pd
d = pd.read_csv('/home/claude/qlab/data_1m/BTCUSDT.csv'); d['t'] = pd.to_datetime(d.t, unit='ms', utc=True); d = d.set_index('t')
rows = []
for day, g in d.groupby(d.index.date):
    L = g.between_time('07:00', '12:59'); N = g.between_time('13:00', '19:59')
    if len(L) < 300 or len(N) < 400: continue
    for side, lvl in (('H', L.high.max()), ('L', L.low.min())):
        s = 1 if side == 'H' else -1
        hit = N.index[(N.high >= lvl) if s == 1 else (N.low <= lvl)]
        if len(hit) == 0: continue
        i = N.index.get_loc(hit[0])
        if i + 70 >= len(N): continue
        nxt = N.iloc[i+1:i+11]; dwell = int(((nxt.close - lvl)*s > 0).sum())
        out = (N.close.iloc[i+60] - lvl)/lvl*100*s; out30 = (N.close.iloc[i+30] - lvl)/lvl*100*s
        rows.append((day, side, hit[0].strftime('%H:%M'), dwell, out30, out))
r = pd.DataFrame(rows, columns=['day','side','tag','dwell','out30','out60'])
print(f"tags {len(r)} over {r.day.nunique()} days; dwell distribution:\n{r.dwell.value_counts().sort_index().to_dict()}")
r['bin'] = pd.cut(r.dwell, [-1, 0, 2, 5, 8, 10], labels=['0 instant reject','1-2','3-5','6-8','9-10 accepted'])
def summ(x):
    t = x.out60.mean()/x.out60.std()*np.sqrt(len(x)) if len(x) > 2 else np.nan
    return pd.Series({'n': len(x), 'out30 %': round(x.out30.mean(), 3), 'out60 %': round(x.out60.mean(), 3), 'cont60 %': round(100*(x.out60 > 0).mean(), 0), 't60': round(t, 1)})
print("\nAll session-extreme tags (NY hours), by dwell in the first 10 min:"); print(r.groupby('bin', observed=True).apply(summ))
print("\nHigh tags only:"); print(r[r.side=='H'].groupby('bin', observed=True).apply(summ))
print("\nLow tags only:"); print(r[r.side=='L'].groupby('bin', observed=True).apply(summ))
h = len(r)//2
for nm, sub in (('H1', r.iloc[:h]), ('H2', r.iloc[h:])):
    a = sub[sub.dwell == 0].out60; b = sub[sub.dwell >= 6].out60
    print(f"{nm}: instant-reject n {len(a)} out60 {a.mean():+.3f}% | accepted(6+) n {len(b)} out60 {b.mean():+.3f}%")
