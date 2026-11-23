"""doc 256: true NQ order flow from Databento (CME Globex trades with aggressor side) to test AuclairsDad's divergence entry on real delta.
Budget: DK's $125 free credit - this script NEVER spends more than BUDGET (default $90). It prices the request first (metadata.get_cost),
shrinks the window (most recent first) until it fits, then downloads trades for the continuous front-month NQ and writes 5-min bars with
true buy / sell aggressor volume: data_nq_cache/nq_true_delta_5m.csv.gz. Key comes only from the DATABENTO_API_KEY secret (never printed)."""
import os, sys, datetime as dt
import databento as db, pandas as pd
BUDGET = float(os.environ.get("DB_BUDGET", "90")); END = pd.Timestamp(os.environ.get("DB_END", "2026-11-21"))
START = pd.Timestamp(os.environ.get("DB_START", "2025-10-01"))
c = db.Historical(os.environ["DATABENTO_API_KEY"])
q = dict(dataset="GLBX.MDP3", schema="trades", symbols=["NQ.c.0"], stype_in="continuous")
s = START
while True:
    cost = c.metadata.get_cost(start=s.strftime("%Y-%m-%d"), end=END.strftime("%Y-%m-%d"), **q)
    print(f"cost {s.date()} -> {END.date()}: ${cost:.2f}", flush=True)
    if cost <= BUDGET: break
    s = s + (END - s) / 4
    if (END - s).days < 20: sys.exit("even 20 days is over budget - stopping, nothing downloaded")
os.makedirs("data_nq_cache", exist_ok=True); out = []
months = pd.date_range(s.normalize(), END, freq="MS").tolist()
edges = [s] + [m for m in months if m > s] + [END]
for a, b in zip(edges[:-1], edges[1:]):
    store = c.timeseries.get_range(start=a.strftime("%Y-%m-%d"), end=b.strftime("%Y-%m-%d"), **q)
    for chunk in store.to_df(count=2_000_000):
        chunk = chunk[["price", "size", "side"]]
        buy = chunk["size"].where(chunk.side == "B", 0); sell = chunk["size"].where(chunk.side == "A", 0)
        g = pd.DataFrame({"open": chunk.price, "high": chunk.price, "low": chunk.price, "close": chunk.price, "vol": chunk["size"], "buy": buy, "sell": sell})
        r = g.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "buy": "sum", "sell": "sum"}).dropna(subset=["close"])
        out.append(r)
    print(f"done {a.date()} -> {b.date()}", flush=True)
d = pd.concat(out); d = d.groupby(level=0).agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "buy": "sum", "sell": "sum"})
d["delta"] = d.buy - d.sell; d.to_csv("data_nq_cache/nq_true_delta_5m.csv.gz")
print(f"saved {len(d)} 5-min bars {d.index[0]} -> {d.index[-1]}; spent about ${cost:.2f} of the free credit")
