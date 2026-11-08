"""Reduce Binance aggTrades zips to taker orders >= 5 BTC (one file per day), deleting each zip after. Newest first."""
import glob, zipfile, os, sys, numpy as np, pandas as pd
from multiprocessing import Pool
def one(f):
    out = f"data_long/bigorders_days/{os.path.basename(f)[:-4]}.parquet"
    try:
        z = zipfile.ZipFile(f); a = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[1, 2, 5, 6], names=["p", "q", "t", "mk"], low_memory=False)
        if a.p.dtype == object: a = a.iloc[1:].astype({"p": float, "q": float, "t": "int64"}); a["mk"] = a.mk.astype(str).str.lower() == "true"
        a["t"] = np.where(a.t > 1e14, a.t // 1000, a.t)
        o = a.groupby(["t", "mk"]).agg(q=("q", "sum"), pmin=("p", "min"), pmax=("p", "max")).reset_index()
        o[o.q >= 5].to_parquet(out)
    except Exception as e: print(f, e, flush=True)
    os.remove(f); return f
if __name__ == "__main__":
    os.makedirs("data_long/bigorders_days", exist_ok=True)
    fs = sorted(glob.glob("data_long/agg/*.zip"), reverse=True)
    with Pool(2) as p:
        for i, f in enumerate(p.imap_unordered(one, fs)):
            if i % 20 == 0: print(i, f, flush=True)
