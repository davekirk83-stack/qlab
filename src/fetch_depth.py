"""
DEPTH ARCHIVE EXTENSION — 20 symbols x 1 year of order-book depth.

Doc 59 found price is drawn toward resting liquidity, but on 4 symbols and
45 days. The follow-up check (2026-10-15) showed the effect is NOT a
restatement of the positioning elements -- the partial IC retains 88% of the
raw IC at daily resolution -- but 32 independent days cannot support a
registration. The bootstrap CI straddles zero. So the binding constraint is
sample, and this fixes the sample.

Binance publishes bookDepth daily: notional resting size at +/-1,2,3,4,5%
and +/-0.2%, sampled every ~minute. We stream each day, pivot to the twelve
band columns, resample to 5 minutes to match the OI archive, and discard the
raw file -- 3.8GB of zips would not fit, 105k rows per symbol does.
"""
import os, sys, io, zipfile, urllib.request
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta

OUT = "/home/claude/qlab/data_depth_full"
BASE = "https://data.binance.vision/data/futures/um/daily/bookDepth"
SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","XRPUSDT","BNBUSDT","ADAUSDT",
        "AVAXUSDT","LINKUSDT","LTCUSDT","DOTUSDT","NEARUSDT","APTUSDT","ARBUSDT",
        "OPUSDT","SUIUSDT","TRXUSDT","BCHUSDT","ATOMUSDT","UNIUSDT"]
END = date(2026, 10, 11)
DAYS = 365


def one(args):
    sym, d = args
    url = f"{BASE}/{sym}/{sym}-bookDepth-{d}.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        df = pd.read_csv(z.open(z.namelist()[0]))
    except Exception:
        return sym, None
    df["ts"] = pd.to_datetime(df.timestamp)
    p = df.pivot_table(index="ts", columns="percentage", values="notional",
                       aggfunc="last")
    p.columns = [f"d{c:+g}" for c in p.columns]
    return sym, p.resample("5min").last()


if __name__ == "__main__":
    dates = [(END - timedelta(days=k)).isoformat() for k in range(DAYS)]
    jobs = [(s, d) for s in SYMS for d in dates]
    print(f"{len(SYMS)} symbols x {DAYS} days = {len(jobs)} files")
    acc = {s: [] for s in SYMS}
    done = miss = 0
    with ProcessPoolExecutor(max_workers=24) as ex:
        for sym, p in ex.map(one, jobs, chunksize=8):
            done += 1
            if p is None or not len(p):
                miss += 1
            else:
                acc[sym].append(p)
            if done % 500 == 0:
                print(f"  {done}/{len(jobs)}  missing {miss}", flush=True)
    for s in SYMS:
        if not acc[s]:
            print(f"  {s}: nothing"); continue
        df = pd.concat(acc[s]).sort_index()
        df = df[~df.index.duplicated()].dropna(how="all")
        df.index.name = "ts"
        df.to_csv(f"{OUT}/{s}.csv")
        print(f"  {s:10s} {len(df):7d} rows  {df.index[0].date()} -> {df.index[-1].date()}")
