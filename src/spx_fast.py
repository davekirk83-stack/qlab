import sys; sys.path.insert(0,"/home/claude/qlab/src")
import pandas as pd, numpy as np, os
from concurrent.futures import ThreadPoolExecutor
from get_spx_1m import fetch_hour, INSTR, OUT
DAYS={
 "covid":   ["2020-03-09","2020-03-11","2020-03-12","2020-03-16","2020-03-18","2020-03-20","2020-03-24"],
 "tariff":  ["2025-04-03","2025-04-04","2025-04-07","2025-04-08","2025-04-09","2025-04-10"],
 "calm":    ["2019-06-04","2019-06-05","2019-06-06","2019-06-10","2019-06-11","2019-06-12"],
}
HOURS=range(13,21)
os.makedirs(OUT,exist_ok=True)
for lab,ds in DAYS.items():
    tasks=[(INSTR,pd.Timestamp(d).date(),h) for d in ds for h in HOURS]
    out=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for df in ex.map(fetch_hour,tasks):
            if df is not None and len(df): out.append(df)
    if not out: print(f"  {lab}: nothing",flush=True); continue
    t=pd.concat(out).sort_values("ts"); t["mid"]=(t.ask+t.bid)/2
    t["sp"]=(t.ask-t.bid)/t.mid*1e4; t=t.set_index("ts")
    m=pd.DataFrame({"open":t.mid.resample("1min").first(),"high":t.mid.resample("1min").max(),
                    "low":t.mid.resample("1min").min(),"close":t.mid.resample("1min").last(),
                    "ticks":t.mid.resample("1min").count(),
                    "spread_bp":t.sp.resample("1min").median()}).dropna(subset=["close"])
    m=m[m.ticks>0]; m.to_csv(f"{OUT}/{lab}.csv")
    sd5=(m.close/m.close.shift(5)-1).std()*100
    print(f"  {lab:8s} {len(m):6d} min  5-min SD {sd5:.3f}%  "
          f"spread {m.spread_bp.median():.1f}bp  days {len(ds)}",flush=True)
