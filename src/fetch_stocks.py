import json, os, time, urllib.request, pandas as pd
from concurrent.futures import ThreadPoolExecutor
OUT="/home/claude/qlab/data_stk"; U=json.load(open("/home/claude/qlab/data_eqd/sp500_universe.json"))
syms=U["current"]+["SPY","QQQ"]
def get(s):
    p=f"{OUT}/{s}.csv"
    if os.path.exists(p): return s,"cached"
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1=1072915200&period2=1793000000&interval=1d&events=div,split"
    for k in range(3):
        try:
            j=json.load(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30))
            r=j["chart"]["result"][0]; q=r["indicators"]["quote"][0]; adj=r["indicators"]["adjclose"][0]["adjclose"]
            d=pd.DataFrame({"t":pd.to_datetime(r["timestamp"],unit="s").normalize(),"open":q["open"],"high":q["high"],"low":q["low"],"close":q["close"],"adj":adj,"volume":q["volume"]}).dropna()
            f=d.adj/d.close
            for c in ("open","high","low","close"): d[c]=d[c]*f   # adjust OHLC for splits/dividends
            d.drop(columns="adj").to_csv(p,index=False); return s,len(d)
        except Exception as e: err=e; time.sleep(2*(k+1))
    return s,f"fail {err}"
with ThreadPoolExecutor(8) as ex: res=list(ex.map(get,syms))
print(sum(1 for _,x in res if isinstance(x,int) or x=="cached"),"ok;", [r for r in res if isinstance(r[1],str) and r[1].startswith("fail")][:10])
