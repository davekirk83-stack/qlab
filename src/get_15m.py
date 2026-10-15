import sys, io, zipfile, urllib.request, datetime as dt, pandas as pd
from concurrent.futures import ThreadPoolExecutor
B="https://data.binance.vision/data/futures/um/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume",
      "count","taker_buy_volume","taker_buy_quote_volume","ignore"]
def one(a):
    sym,ym=a
    try:
        with urllib.request.urlopen(f"{B}/{sym}/15m/{sym}-15m-{ym}.zip",timeout=60) as r:
            z=zipfile.ZipFile(io.BytesIO(r.read()))
            d=pd.read_csv(z.open(z.namelist()[0]))
            if str(d.columns[0])!="open_time":
                d=pd.read_csv(z.open(z.namelist()[0]),header=None,names=COLS)
            return d
    except Exception: return None
def build(sym,months=30):
    t=dt.date.today().replace(day=1); ms=[]
    for i in range(1,months+1):
        y,m=divmod((t.year*12+t.month-1)-i,12); ms.append(f"{y}-{m+1:02d}")
    with ThreadPoolExecutor(10) as ex:
        parts=[p for p in ex.map(one,[(sym,m) for m in ms]) if p is not None]
    if not parts: print(sym,"none"); return
    o=pd.concat(parts,ignore_index=True)
    o["date"]=pd.to_datetime(o.open_time,unit="ms")
    o=o[["date","open","high","low","close","volume"]].drop_duplicates("date").sort_values("date")
    o.to_csv(f"/home/claude/qlab/data_15m/{sym}.csv",index=False)
    print(f"{sym}: {len(o)} 15m bars {o.date.min()} -> {o.date.max()}",flush=True)
if __name__=="__main__":
    for s in sys.argv[1:]: build(s)
