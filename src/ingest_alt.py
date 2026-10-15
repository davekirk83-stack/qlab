"""Wide altcoin universe, daily bars, from the Binance public archive.
Includes DELISTED symbols -> survivorship-clean by construction."""
import io, json, zipfile, urllib.request, datetime as dt, pandas as pd, os
from concurrent.futures import ThreadPoolExecutor

B="https://data.binance.vision/data/spot/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume",
      "count","taker_buy_volume","taker_buy_quote_volume","ignore"]
OUT="/home/claude/qlab/data_alt"
MONTHS=[]
t=dt.date.today().replace(day=1)
for i in range(1,49):
    y,m=divmod((t.year*12+t.month-1)-i,12); MONTHS.append(f"{y}-{m+1:02d}")

def one(args):
    sym,ym=args
    try:
        with urllib.request.urlopen(f"{B}/{sym}/1d/{sym}-1d-{ym}.zip",timeout=30) as r:
            z=zipfile.ZipFile(io.BytesIO(r.read()))
            d=pd.read_csv(z.open(z.namelist()[0]))
            if str(d.columns[0])!="open_time":
                d=pd.read_csv(z.open(z.namelist()[0]),header=None,names=COLS)
            return d
    except Exception: return None

def build(sym):
    if os.path.exists(f"{OUT}/{sym}.csv"): return None
    with ThreadPoolExecutor(12) as ex:
        parts=[p for p in ex.map(one,[(sym,m) for m in MONTHS]) if p is not None]
    if len(parts)<12: return None
    o=pd.concat(parts,ignore_index=True)
    o["date"]=pd.to_datetime(o.open_time,unit="ms")
    o=o[["date","open","high","low","close","volume","quote_volume","taker_buy_volume","count"]]
    o=o.drop_duplicates("date").sort_values("date")
    if len(o)<400: return None
    o.to_csv(f"{OUT}/{sym}.csv",index=False)
    return (sym,len(o),float(o.quote_volume.tail(120).median()))

if __name__=="__main__":
    syms=json.load(open("/home/claude/qlab/syms_usdt.json"))
    done=0
    for s in syms:
        r=build(s)
        if r: done+=1
        if done and done%25==0: print(f"{done} built",flush=True)
    print(f"DONE {done}",flush=True)
