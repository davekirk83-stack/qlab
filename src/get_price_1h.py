"""Hourly spot price from Coinbase, paginated. 300 bars/call."""
import sys, time, json, urllib.request, datetime as dt, pandas as pd
B="https://api.exchange.coinbase.com/products"
def grab(prod, gran=3600, days=400):
    end=dt.datetime.now(dt.timezone.utc); out=[]
    step=dt.timedelta(seconds=gran*300)
    while (dt.datetime.now(dt.timezone.utc)-end).days < days:
        s=end-step
        url=f"{B}/{prod}/candles?granularity={gran}&start={s.isoformat()}&end={end.isoformat()}"
        try:
            with urllib.request.urlopen(url,timeout=30) as r: d=json.load(r)
        except Exception: break
        if not d: break
        out+=d; end=s; time.sleep(0.34)
    if not out: return None
    df=pd.DataFrame(out,columns=["t","low","high","open","close","volume"])
    df["date"]=pd.to_datetime(df.t,unit="s",utc=True).dt.tz_localize(None)
    df=df[["date","open","high","low","close","volume"]].drop_duplicates("date").sort_values("date")
    p=f"/home/claude/qlab/data_1h/{prod.replace('-','')}.csv"; df.to_csv(p,index=False)
    print(f"{prod}: {len(df)} hourly bars {df.date.min()} -> {df.date.max()}",flush=True)
if __name__=="__main__":
    import os; os.makedirs("/home/claude/qlab/data_1h",exist_ok=True)
    for p in sys.argv[1:]: grab(p)
