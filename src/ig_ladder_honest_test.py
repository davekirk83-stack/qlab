"""Doc 194 check on the IG ladder: paperbook6 engine (prices bar i's orders from bar i's own close) vs resting orders priced from the
previous closed bar (what src/ig_range_engine.py actually does live). Both sides; shorts via the mirror K - price. IG-like costs."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paperbook6 as P, revx_honest_test as H
P.MK, P.TAKER, P.SLIP = 0.0, 0.0, 0.0001
def to15(d): return d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def load(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    return to15(d[["open", "high", "low", "close"]].astype(float))
F = {"NQ": "data_nq_cache/nq_5m.csv", "US500": "data_ig_cache/USA500IDXUSD_5m.csv", "FTSE": "data_ig_cache/GBRIDXGBP_5m.csv"}
for name, f in F.items():
    d = load(f); start = d.index[300]
    P._MED.pop(name, None); ema, lo, hi, a, _ = P.indicators(d); cont = pd.Series(((d.close.values <= hi) & (d.close.values >= lo)).astype(float)).rolling(50).mean()
    P._MED[name] = {"median": float(cont.median())}
    K = 2 * d.high.max(); m = pd.DataFrame({"open": K - d.open, "high": K - d.low, "low": K - d.high, "close": K - d.close}, index=d.index)
    closed, _ = P.step(name, d, {}, str(d.index[250]), [99])
    eng = np.array([c[4] for c in closed])
    hon = np.array([x[3] for x in H.honest2(d, name, start)] + [x[3] for x in H.honest2(m, name, start)])
    print(f"{name:6s} {d.index[0].date()}..{d.index[-1].date()}  engine n{len(eng)} mean {100*eng.mean():+.3f}% sum {100*eng.sum():+.1f}%  |  "
          f"resting-honest n{len(hon)} mean {100*hon.mean():+.3f}% sum {100*hon.sum():+.1f}%", flush=True)
