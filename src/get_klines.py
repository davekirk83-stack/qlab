"""Hourly futures klines from the Binance public archive (monthly zips)."""
import sys, io, zipfile, urllib.request, datetime as dt, pandas as pd
B="https://data.binance.vision/data/futures/um/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume",
      "count","taker_buy_volume","taker_buy_quote_volume","ignore"]
def month(sym, ym, iv="1h"):
    try:
        with urllib.request.urlopen(f"{B}/{sym}/{iv}/{sym}-{iv}-{ym}.zip",timeout=45) as r:
            z=zipfile.ZipFile(io.BytesIO(r.read()))
            d=pd.read_csv(z.open(z.namelist()[0]))
            if d.columns[0]!="open_time": 
                d=pd.read_csv(z.open(z.namelist()[0]),header=None,names=COLS)
            return d
    except Exception: return None
def build(sym, months=30, iv="1h"):
    rows=[]; t=dt.date.today().replace(day=1)
    for i in range(1,months+1):
        y,m=divmod((t.year*12+t.month-1)-i,12); ym=f"{y}-{m+1:02d}"
        d=month(sym,ym,iv)
        if d is not None: rows.append(d)
    if not rows: print(f"{sym}: nothing"); return
    o=pd.concat(rows,ignore_index=True)
    o["date"]=pd.to_datetime(o.open_time,unit="ms")
    o=o[["date","open","high","low","close","volume","taker_buy_volume","quote_volume","count"]]
    o=o.drop_duplicates("date").sort_values("date")
    p=f"/home/claude/qlab/data_1h/{sym}.csv"; o.to_csv(p,index=False)
    print(f"{sym}: {len(o)} x{iv} bars {o.date.min()} -> {o.date.max()}",flush=True)
if __name__=="__main__":
    for s in sys.argv[1:]: build(s)
