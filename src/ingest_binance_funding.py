"""Binance USDT-perp funding history 2021-2026 from the public Vision archive
(monthly zips, 8-hourly settlements). For the alt-short gate. Read-only."""
import io, os, sys, time, zipfile, urllib.request
import pandas as pd
OUT="/home/claude/qlab/data_funding_binance"; os.makedirs(OUT, exist_ok=True)
COINS=["AAVE","ADA","ARB","AVAX","DOGE","DOT","FET","FIL","HBAR","ICP","INJ","LINK","LTC","NEAR","ONDO","QNT","SOL","STRK","SUI","UNI","XLM","XRP","ZEC","ZRO","BTC","ETH"]
months=[f"{y}-{m:02d}" for y in range(2021,2027) for m in range(1,13) if (y,m)<=(2026,10)]
for c in COINS:
    p=f"{OUT}/{c}.csv"
    if os.path.exists(p): continue
    rows=[]
    for ym in months:
        url=f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{c}USDT/{c}USDT-fundingRate-{ym}.zip"
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as r: b=r.read()
        except Exception: continue
        try:
            z=zipfile.ZipFile(io.BytesIO(b)); n=z.namelist()[0]; d=pd.read_csv(z.open(n))
            d.columns=[x.lower() for x in d.columns]
            tcol=[x for x in d.columns if "time" in x][0]; rcol=[x for x in d.columns if "rate" in x][0]
            rows.append(d[[tcol,rcol]].rename(columns={tcol:"ts",rcol:"rate"}))
        except Exception: pass
    if rows:
        d=pd.concat(rows); d["ts"]=pd.to_datetime(d.ts,unit="ms",utc=True); d=d.sort_values("ts").drop_duplicates("ts"); d.to_csv(p,index=False)
        print(f"{c:<6}{len(d):>6} rows {str(d.ts.iloc[0])[:10]} -> {str(d.ts.iloc[-1])[:10]}  share negative {(d.rate<0).mean():.0%}", flush=True)
    else: print(f"{c:<6} nothing", flush=True)
