"""Doc 191 addendum — big taker orders inside 1-min wicks, all stress days processed so far (2022+; taker order = same-ms same-side aggTrades).
Event: 1-min bar at a 4h low (high) with lower (upper) wick >= 50% of range containing a taker SELL (BUY) order >= Q BTC inside the
outer 30% of the bar. Control: same kind of bar on the same days without such an order. Forward return in the reversal direction (bp)."""
import glob, numpy as np, pandas as pd
OUT = open("runs/big_order_wick_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
O = pd.concat([pd.read_parquet(f) for f in glob.glob("data_long/bigorders_*.parquet") + glob.glob("data_long/bigorders_days/*.parquet")]).drop_duplicates()
O["ts"] = pd.to_datetime(O.t, unit="ms", utc=True).dt.floor("1min")
days = sorted(set(O.ts.dt.floor("D"))); SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
m = pd.read_parquet("data_long/btc_1m.parquet"); C = m.close
lo240 = m.low.rolling(240).min(); hi240 = m.high.rolling(240).max(); rng = (m.high - m.low).replace(0, np.nan)
lw = (np.minimum(m.open, m.close) - m.low) / rng; uw = (m.high - np.maximum(m.open, m.close)) / rng
mm = m[m.index.floor("D").isin(days)]
log(f"stress days with order data: {len(days)} ({days[0].date()} .. {days[-1].date()}); taker orders >= 20 BTC: {int((O.q>=20).sum())}")
def fwd(ix, side):
    p0 = C.reindex(ix).values
    return {h: side * (C.reindex(ix + pd.Timedelta(minutes=h)).values / p0 - 1) * 1e4 for h in (15, 60, 240)}
for Q in (10, 20, 50):
    for side, name in ((1, "LOW wick + big SELL orders -> long"), (-1, "HIGH wick + big BUY orders -> short")):
        if side == 1: cand = mm.index[(mm.low <= lo240.reindex(mm.index)) & (lw.reindex(mm.index) >= .5)]; big = O[O.mk & (O.q >= Q)]
        else: cand = mm.index[(mm.high >= hi240.reindex(mm.index)) & (uw.reindex(mm.index) >= .5)]; big = O[~O.mk & (O.q >= Q)]
        bg = big.groupby("ts").agg(pmin=("pmin", "min"), pmax=("pmax", "max"))
        j = bg.reindex(cand); lo, hi = m.low.reindex(cand).values, m.high.reindex(cand).values
        zone = (j.pmin.values <= lo + .3 * (hi - lo)) if side == 1 else (j.pmax.values >= hi - .3 * (hi - lo))
        hit = np.nan_to_num(zone.astype(float)) > 0
        for seg, sm in (("2022-23", cand < SPLIT), ("2024-26", cand >= SPLIT)):
            ev, ctl = cand[hit & sm], cand[~hit & sm]
            fe, fc = fwd(ev + pd.Timedelta(minutes=1), side), fwd(ctl + pd.Timedelta(minutes=1), side)
            cell = lambda F: " ".join(f"{h}m {np.nanmean(F[h]):+6.1f}/{100*np.nanmean(F[h]>0):3.0f}%" for h in F)
            log(f"  Q>={Q:2} {name:35} {seg} event n{len(ev):4} {cell(fe)} || without n{len(ctl):4} {cell(fc)}")
