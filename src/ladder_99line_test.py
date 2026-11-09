"""DK 9 Nov ("test it and let me know"): should the panel's LONG/SHORT advisory (the Range v3 ladder, paperbook6) use the 99-day line?
BTC 15-min, Binance spot 2020 - Nov 2026, the registered ladder with its own costs. Dev 2020-2023 / hold 2024-2026.
Regime = YESTERDAY's daily close vs the 99-day smoothed MA (RMA), so it is known before the bar.
V0 baseline; V1 long rungs only above the line; V2 short rungs only below the line; V3 both (trend-aligned only)."""
import sys, os, inspect, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
import paperbook6 as P6
OUT = open("/home/claude/qlab-git/runs/ladder_99line_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
src = inspect.getsource(P6.step).replace('def step(sym, d, pos, since, slots_free, hold_regime=False):', 'def step_blk(sym, d, pos, since, slots_free, hold_regime=False, BLK=None):')
src = src.replace('''        if not ok: continue
        for side in ("L", "S"):
            p = pos.get(side)''', '''        if not ok: continue
        for side in ("L", "S"):
            if BLK is not None and BLK[side][i]: continue
            p = pos.get(side)''')
assert "BLK[side][i]" in src
exec(src, P6.__dict__)
m = pd.read_parquet("/home/claude/qlab-git/data_long/btc_1m.parquet")
b = m.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
d = b.close.resample("1D").last(); sm = d.ewm(alpha=1/99, adjust=False).mean()
above = (d > sm).shift(1).reindex(b.index.floor("D")).fillna(False).values.astype(bool)
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
V = {"V0 baseline": None, "V1 longs only above the line": {"L": ~above, "S": np.zeros(len(b), bool)},
     "V2 shorts only below the line": {"L": np.zeros(len(b), bool), "S": above}, "V3 both trend-aligned": {"L": ~above, "S": above}}
log("RANGE v3 LADDER (the panel's LONG/SHORT advisory) on BTC with the 99-day line — sum of episode returns (% of ladder budget)")
for lab, BLK in V.items():
    P6._MED = {}
    closed, _ = P6.step_blk("BTC", b, {}, str(b.index[3000]), [10**6], BLK=BLK)
    E = pd.DataFrame([(pd.Timestamp(c[2]) if pd.Timestamp(c[2]).tzinfo else pd.Timestamp(c[2]).tz_localize("UTC"), c[1] if isinstance(c[1], str) else "?", c[4], c[5]) for c in closed], columns=["t", "side", "r", "how"])
    cells = []
    for seg, x in (("dev", E[E.t < SPLIT]), ("hold", E[E.t >= SPLIT])):
        cells.append(f"{seg} n{len(x):4} sum {100*x.r.sum():+7.1f}% mean {100*x.r.mean():+.3f}% win {100*(x.r>0).mean():.0f}% worst {100*x.r.min():+.1f}%")
    log(f"  {lab:30} " + " || ".join(cells))
    if lab == "V0 baseline":
        E["above"] = above[np.searchsorted(b.index.values, E.t.values.astype("datetime64[ns]")).clip(0, len(b) - 1)] if len(E) else []
        E.to_csv("/home/claude/qlab-git/runs/ladder_99line_episodes.csv", index=False)
log("done")
