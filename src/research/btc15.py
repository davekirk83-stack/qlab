"""Binance BTCUSDT 15m bars 2021-now (data.binance.vision monthly zips + recent API), with taker-buy volume. Cached to data_long/btc15.parquet."""
import os, glob, zipfile, json, urllib.request, numpy as np, pandas as pd
ZIPS = os.environ.get("BZ", "/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/bz")
CACHE = "data_long/btc15.parquet"
def load(refresh=False):
    if os.path.exists(CACHE) and not refresh: return pd.read_parquet(CACHE)
    fr = []
    for f in sorted(glob.glob(f"{ZIPS}/*.zip")):
        z = zipfile.ZipFile(f); fr.append(pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0,1,2,3,4,5,9]))
    d = pd.concat(fr); d.columns = ["t","o","h","l","c","v","tb"]
    d["t"] = np.where(d.t > 1e14, d.t // 1000, d.t)
    end = int(d.t.max())
    while True:
        k = json.load(urllib.request.urlopen(f"https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=15m&startTime={end+1}&limit=1000", timeout=30))
        if not k: break
        x = pd.DataFrame([[r[0], r[1], r[2], r[3], r[4], r[5], r[9]] for r in k], columns=d.columns).astype(float)
        d = pd.concat([d, x]); end = int(x.t.max())
        if len(k) < 1000: break
    d = d.astype(float).drop_duplicates("t").sort_values("t")
    d.index = pd.to_datetime(d.t.astype("int64"), unit="ms", utc=True); d = d.drop(columns="t")
    d["delta"] = 2 * d.tb - d.v
    d = d.iloc[:-1]
    os.makedirs("data_long", exist_ok=True); d.to_parquet(CACHE); return d
if __name__ == "__main__":
    d = load(True); print(d.index[0], d.index[-1], len(d))
