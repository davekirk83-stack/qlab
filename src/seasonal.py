"""Month-end surge into month-start then reverse · Sell in May · bank holidays."""
import os, numpy as np, pandas as pd
D="/home/claude/qlab/data_1h"
SY=sorted(f[:-4] for f in os.listdir(D) if f.endswith(".csv"))
def daily(sym):
    d=pd.read_csv(f"{D}/{sym}.csv",parse_dates=["date"]).set_index("date").sort_index()
    return d.resample("D").agg(open=("open","first"),high=("high","max"),
                               low=("low","min"),close=("close","last")).dropna()
US_HOL=pd.to_datetime(["2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27",
"2024-06-19","2024-07-04","2024-09-02","2024-11-28","2024-12-25",
"2025-01-01","2025-01-20","2025-02-17","2025-04-18","2025-05-26","2025-06-19",
"2025-07-04","2025-09-01","2025-11-27","2025-12-25",
"2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19",
"2026-07-03","2026-09-07"])
ASIA_HOL=pd.to_datetime(["2024-02-10","2024-02-12","2024-05-01","2024-10-01","2024-10-02",
"2025-01-29","2025-01-30","2025-05-01","2025-10-01","2025-10-02",
"2026-02-17","2026-02-18","2026-05-01","2026-10-01","2026-10-02"])
def main():
    R=[]
    for s in SY:
        d=daily(s); r=d.close.pct_change().dropna()
        R.append(r.rename(s))
    P=pd.concat(R,axis=1).mean(axis=1).dropna()
    print("SEASONAL TESTS — %d symbols, %s to %s, %d days\n"%(len(SY),P.index.min().date(),P.index.max().date(),len(P)))
    print("="*72); print("  1. MONTH-END SURGE INTO MONTH-START, THEN REVERSAL?"); print("="*72)
    dom=P.index.day; dim=P.index.days_in_month
    buckets={"last 3 days of month":(dom>=dim-2),"first 3 days of month":(dom<=3),
             "days 4-7":(dom>=4)&(dom<=7),"days 8-21 (mid)":(dom>=8)&(dom<=21),
             "days 22-28":(dom>=22)&(dom<=28)}
    print("  %-26s %7s %12s %9s"%("window","n","mean daily","win%"))
    for k,m in buckets.items():
        x=P[m]
        print("  %-26s %7d %+11.4f%% %8.1f%%"%(k,len(x),x.mean()*100,(x>0).mean()*100))
    print()
    print("="*72); print("  2. SELL IN MAY AND GO AWAY  (May-Oct vs Nov-Apr)"); print("="*72)
    mo=P.index.month
    summer=P[(mo>=5)&(mo<=10)]; winter=P[(mo<=4)|(mo>=11)]
    print("  %-26s %7s %12s %9s %14s"%("period","n","mean daily","win%","annualised"))
    for k,x in (("May-Oct ('sell in May')",summer),("Nov-Apr",winter)):
        print("  %-26s %7d %+11.4f%% %8.1f%% %+13.1f%%"%(k,len(x),x.mean()*100,(x>0).mean()*100,((1+x.mean())**252-1)*100))
    print("  -> difference: %+.4f%% per day in favour of %s"%(abs(winter.mean()-summer.mean())*100,"Nov-Apr" if winter.mean()>summer.mean() else "May-Oct"))
    print()
    print("="*72); print("  3. BANK HOLIDAYS — what happens to crypto when TradFi is shut?"); print("="*72)
    print("  %-30s %7s %12s %9s %12s"%("day type","n","mean daily","win%","mean |ret|"))
    for k,dates in (("US bank holiday",US_HOL),("day AFTER US holiday",US_HOL+pd.Timedelta(days=1)),
                    ("Asia holiday (CNY/Golden Wk)",ASIA_HOL)):
        m=P.index.normalize().isin(dates)
        x=P[m]
        if len(x)>=5:
            print("  %-30s %7d %+11.4f%% %8.1f%% %11.3f%%"%(k,len(x),x.mean()*100,(x>0).mean()*100,x.abs().mean()*100))
    allh=US_HOL.union(ASIA_HOL)
    norm=P[~P.index.normalize().isin(allh)]
    print("  %-30s %7d %+11.4f%% %8.1f%% %11.3f%%"%("normal days",len(norm),norm.mean()*100,(norm>0).mean()*100,norm.abs().mean()*100))
if __name__=="__main__": main()
