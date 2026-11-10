"""Doc 217 — builders for the standard test (src/standard_test.py): the core books and the Donchian regime study (DK 10:47:
"a better system to know when [Donchian] would most safely apply, and when not, in terms of market conditions")."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF, review2_new_books as N, review_ideas_test as V, standard_test as S
IX8, TR6 = F.IXG, RF.TR6; ALL = N.ALL
NONCRYPTO = [k for k in ALL if not k.endswith("USD") or k in ("EURUSD", "GBPUSD", "AUDUSD")]
up = lambda d: d.close > d.close.rolling(200).mean(); r4 = lambda d: F.rsi(d.close, 4)
class cost:
    def __init__(s, cm): s.cm = cm
    def __enter__(s): s.old = dict(F.COST); [F.COST.__setitem__(k, v * s.cm) for k, v in s.old.items()]
    def __exit__(s, *a): F.COST.clear(); F.COST.update(s.old)
def mk(rows): return pd.DataFrame(rows, columns=["t", "R", "m"])
def rsi4(cm=1.0, rnd=None):
    with cost(cm): return mk([(t, R, k) for k in IX8 for t, R in RF.run_o(k, (rnd or (lambda k, e: e))(k, up(F.D[k]) & (r4(F.D[k]) < 25)), r4(F.D[k]) > 55, 10, 3.0)])
def tom(cm=1.0, rnd=None):
    with cost(cm): return mk([(t, R, k) for k in TR6 for t, R in F.run(k, (rnd or (lambda k, e: e))(k, V.tom(F.D[k])), 1, None, 3, stop=5.0)])
def core(): return pd.concat([rsi4(), tom()])
# ---- Donchian 55 long and market-condition filters (all known at the signal close; thresholds fixed in advance, one each)
def er(c, n=60): return (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()          # Kaufman efficiency ratio: 1 = straight line
def adx(d, n=14):
    up_, dn_ = d.high.diff(), -d.low.diff(); pdm = up_.where((up_ > dn_) & (up_ > 0), 0.0); ndm = dn_.where((dn_ > up_) & (dn_ > 0), 0.0)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    a = tr.ewm(alpha=1 / n, adjust=False).mean(); pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / a; ndi = 100 * ndm.ewm(alpha=1 / n, adjust=False).mean() / a
    return (100 * (pdi - ndi).abs() / (pdi + ndi)).ewm(alpha=1 / n, adjust=False).mean()
def breadth():
    px = pd.DataFrame({k: F.D[k].close for k in NONCRYPTO}).ffill(); return (px > px.rolling(200).mean()).mean(axis=1)
_BR = None
FILT = {
    "none": lambda d: pd.Series(True, index=d.index),
    "trend efficiency ER(60) > 0.30": lambda d: er(d.close) > 0.30,
    "ADX(14) > 25": lambda d: adx(d) > 25,
    "12-month momentum > 0": lambda d: d.close > d.close.shift(252),
    "volatility low: ATR below its 1-year median": lambda d: d.atr < d.atr.rolling(252).median(),
    "volatility high: ATR above its 1-year median": lambda d: d.atr > d.atr.rolling(252).median(),
    "breadth: > 60% of markets above their 200-day": lambda d: breadth().reindex(d.index).ffill() > 0.6,
    "breadth: < 40% of markets above their 200-day": lambda d: breadth().reindex(d.index).ffill() < 0.4,
}
def donch(filt, markets=NONCRYPTO):
    def b(cm=1.0, rnd=None):
        rows = []
        with cost(cm):
            for k in markets:
                d = F.D[k]; e = N.hi(d, 55) & up(d) & FILT[filt](d).fillna(False)
                rows += N.run_side(k, (rnd or (lambda k, e: e))(k, e), 1, N.lo(d, 20), 250, 2.0)
        return mk(rows)
    return b
if __name__ == "__main__":
    C = core()
    print("== core books through the standard test"); S.judge("RSI(4) dip, next-open in/out", "dip", IX8, rsi4, register=True)
    S.judge("Turn of the month, 6 traded markets", "calendar", TR6, tom, register=True)
    print("\n== Donchian 55 long (IG-tradable markets, no crypto), by market condition at the signal")
    for f in FILT: S.judge(f"Donchian 55 long | {f}", "trend", NONCRYPTO, donch(f), core=C, random_runs=40)
