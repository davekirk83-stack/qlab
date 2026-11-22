"""Calendar study for the intraday Williams breakout (live), Nov 2025 - Nov 2026, IG costs. Event day vs normal day, per market."""
import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, "src"); import numpy as np, pandas as pd
import champions_intraday as C
from sweep_williams_mkts import run_k
def third_fri(y, m): d = pd.Timestamp(y, m, 1); return d + pd.Timedelta(days=(4 - d.dayofweek) % 7 + 14)
fomc = ["2025-12-10","2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28"]
cpi = ["2025-12-18","2026-01-13","2026-02-11","2026-03-11","2026-04-10","2026-05-12","2026-06-10","2026-07-14","2026-08-12","2026-09-11","2026-10-14","2026-11-10"]
mins = [str((pd.Timestamp(d)+pd.Timedelta(days=21)).date()) for d in fomc]
days = pd.bdate_range("2025-11-01", "2026-11-21")
nfp = [str(g[0].date()) for _, g in pd.Series(days[days.dayofweek == 4]).groupby([days[days.dayofweek == 4].year, days[days.dayofweek == 4].month]).agg(list).items()]
opex = [str(third_fri(y, m).date()) for y in (2025, 2026) for m in range(1, 13)]
vixe = [str((third_fri(y + (m == 12), 1 if m == 12 else m + 1) - pd.Timedelta(days=30)).date()) for y in (2025, 2026) for m in range(1, 13)]
mend = [str((d + pd.offsets.BMonthEnd(0)).date()) for d in pd.date_range("2025-11-01", "2026-11-01", freq="MS")]
mstart = [str((d + pd.offsets.BDay(0)).date()) for d in pd.date_range("2025-12-01", "2026-11-01", freq="MS")]
hol = ["2025-11-27","2025-12-25","2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19","2026-07-03","2026-09-07","2026-11-26"]
pre = [str((pd.Timestamp(h) - pd.offsets.BDay(1)).date()) for h in hol]; post = [str((pd.Timestamp(h) + pd.offsets.BDay(1)).date()) for h in hol]
EV = {"CPI": cpi, "FOMC": fomc, "FOMC minutes": mins, "Jobs Friday": nfp, "US opex": opex, "VIX expiry": vixe, "Month end": mend, "Month start": mstart,
      "Day before US holiday": pre, "Day after US holiday": post}
out = []
for m, k in (("NQ", .4), ("US500", .5), ("GOLD", .3), ("USDJPY", .5)):
    d, S = C.sessions(m); t = run_k(m, S, d, k); t["ds"] = t.t.dt.strftime("%Y-%m-%d")
    allev = set().union(*map(set, EV.values()))
    out.append(f"== Williams {m} k={k}: {len(t)} trades, mean {t.R.mean():+.3f}R; no-event days {t[~t.ds.isin(allev)].R.mean():+.3f}R")
    for ev, ds in EV.items():
        x = t[t.ds.isin(ds)]
        if len(x) >= 4: out.append(f"   {ev:22} n{len(x):3} {x.R.mean():+.3f}R win {(x.pts>0).mean():.0%} | sum {x.R.sum():+.2f}R")
open("runs/research/calendar_study_williams.txt", "w").write("\n".join(out)); print("\n".join(out))
