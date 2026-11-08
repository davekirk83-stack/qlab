"""Doc 191 — DK 6 Nov (@aymane_eth): big aggressive orders 'trapped inside the wicks' = exhaustion. Binance spot BTCUSDT aggTrades on 40
stress days (2024-2026, days with a stress-ladder episode). Taker ORDER = consecutive aggTrades with the same millisecond and side, summed.
Event: a 1-min bar at a 4h low with a lower wick >= 50% of its range, containing >= 1 taker SELL order >= Q BTC printed in the bottom 30% of
the bar (inside the wick). Control: the same bars (4h low, wick >= 50%) with no such order. Mirror for highs/buy orders. Forward return (bp)."""
import glob, zipfile, numpy as np, pandas as pd
OUT = open("runs/big_order_wick_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
m = pd.read_parquet("data_long/btc_1m.parquet"); C = m.close
lo240 = m.low.rolling(240).min(); hi240 = m.high.rolling(240).max(); rng = (m.high - m.low).replace(0, np.nan)
lw = (np.minimum(m.open, m.close) - m.low) / rng; uw = (m.high - np.maximum(m.open, m.close)) / rng
rows = []
for f in sorted(glob.glob("data_long/agg/*.zip")):
    z = zipfile.ZipFile(f); a = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[1, 2, 5, 6], names=["p", "q", "t", "mk"])
    if a.p.dtype == object: a = a.iloc[1:].astype({"p": float, "q": float, "t": "int64"}); a["mk"] = a.mk.astype(str).str.lower() == "true"
    a["t"] = np.where(a.t > 1e14, a.t // 1000, a.t)
    o = a.groupby(["t", "mk"]).agg(q=("q", "sum"), pmin=("p", "min"), pmax=("p", "max")).reset_index()
    o["ts"] = pd.to_datetime(o.t, unit="ms", utc=True).dt.floor("1min")
    rows.append(o)
O = pd.concat(rows); log(f"taker orders on {len(rows)} days: {len(O):,}; >=10 BTC {int((O.q>=10).sum())}, >=20 BTC {int((O.q>=20).sum())}, >=30 BTC {int((O.q>=30).sum())}")
days = sorted(set(O.ts.dt.floor("D")))
mm = m[m.index.floor("D").isin(days)]
def fwd(ix, side):
    p0 = C.reindex(ix).values
    return {h: side * (C.reindex(ix + pd.Timedelta(minutes=h)).values / p0 - 1) * 1e4 for h in (15, 60, 240)}
for Q in (5, 10, 20):
    for side, name in ((1, "LOW wick, big SELL orders -> long"), (-1, "HIGH wick, big BUY orders -> short")):
        if side == 1:
            cand = mm.index[(mm.low <= lo240.reindex(mm.index)) & (lw.reindex(mm.index) >= .5)]
            big = O[(O.mk) & (O.q >= Q)]   # buyer is maker -> aggressive SELL
        else:
            cand = mm.index[(mm.high >= hi240.reindex(mm.index)) & (uw.reindex(mm.index) >= .5)]
            big = O[(~O.mk) & (O.q >= Q)]
        bar = m.reindex(cand)
        hit = []
        for ts in cand:
            b = big[big.ts == ts]
            if len(b) == 0: hit.append(False); continue
            lo, hi = m.low[ts], m.high[ts]
            zone = (b.pmin <= lo + 0.3 * (hi - lo)) if side == 1 else (b.pmax >= hi - 0.3 * (hi - lo))
            hit.append(bool(zone.any()))
        hit = np.array(hit)
        ev, ctl = cand[hit], cand[~hit]
        fe, fc = fwd(ev + pd.Timedelta(minutes=1), side), fwd(ctl + pd.Timedelta(minutes=1), side)
        cell = lambda F: " ".join(f"{h}m {np.nanmean(F[h]):+6.1f}bp/{100*np.nanmean(F[h]>0):3.0f}%" for h in F)
        log(f"  Q>={Q:2} BTC {name:36} event n{len(ev):4} {cell(fe)} || without n{len(ctl):4} {cell(fc)}")
