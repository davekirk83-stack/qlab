"""Doc 209 — the other narrow fails, refined (DK 10 Nov 07:24). Same checks as doc 208 (src/refine_nearmiss.py), 6 traded markets.
USCL: US 500 closes in top 10% of its range and +1% -> DAX/FTSE. HALLO: month-end Nov-Apr long. MDD: only the dips RSI(4) misses."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refine_nearmiss as R, fifty_ideas as F
R.NTRIED = 266; from statistics import NormalDist; R.TSTAR = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / R.NTRIED)) / 2)
up, ma = R.up, R.ma; S = F.D["SPX"]
strong = ((S.close - S.low) / (S.high - S.low) >= 0.9) & (S.close / S.close.shift(1) - 1 >= 0.01)
def eu(filt=None):  # signal on US day t -> European session t+1
    def f(d):
        s = strong if filt is None else strong & filt; s = s.reindex(d.index, method=None).fillna(False)
        e = s.shift(1, fill_value=False); return e
    return f
def uscl(k, e, hold, cm=1.0):  # open of day i -> close of day i+hold-1, stop 2 ATR (prev ATR)
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values; E = e.reindex(d.index).fillna(False).values
    c = F.COST[k] * cm; out = []
    for i in np.where(E)[0]:
        if i < 1 or i + hold - 1 >= len(d) or not np.isfinite(A[i-1]): continue
        en = O[i]; st = en - 2 * A[i-1]; px = None
        for j in range(i, i + hold):
            if L[j] <= st: px = min(st, O[j]) if j > i else st; break
        if px is None: px = C[i + hold - 1]
        out.append((d.index[i], (px - en - 2 * c * en - (hold - 1) * 0.06 / 365 * 1.4 * en) / A[i-1]))
    return out
# hook USCL into R.go via kind "u"
_go = R.go
def go(kind, mk, fn, cm=1.0, rnd=None, cost=None):
    if kind[0] != "u": return _go(kind, mk, fn, cm, rnd, cost)
    hold = int(kind[1]); out = []
    for k in mk:
        e = fn(F.D[k]); e = e if rnd is None else rnd(k, e); out += uscl(k, e, hold, cm)
    return pd.DataFrame(out, columns=["t", "R"])
R.go = go
EUM = ["DAX", "FTSE"]; TR = ["SPX", "NDX", "DJI", "DAX", "FTSE", "GOLD"]; IDX5 = TR[:5]
mdd = lambda d: up(d) & (d.close < ma(d.close, 5)) & ((d.close.diff() < 0).astype(int).rolling(5).sum() >= 4)
nm = lambda d: d.index.to_series().shift(-1).dt.month.reindex(d.index)
hal = lambda d: pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index) & nm(d).isin([11, 12, 1, 2, 3, 4])
IDEAS = {
 "USCL base: DAX/FTSE open -> close":                         ("u1", EUM, eu()),
 "USCL hold 2 sessions (open -> next close)":                 ("u2", EUM, eu()),
 "USCL only when US 500 above its 200-day":                   ("u1", EUM, eu(up(S))),
 "USCL only when US 500 below its 200-day":                   ("u1", EUM, eu(~up(S))),
 "USCL also trade the US 500 itself next open -> close":      ("u1", ["SPX", "NDX", "DJI"], eu()),
 "HALLO base: Nov-Apr month-ends, hold 21d, stop 8 ATR":      ("run", IDX5, lambda d: (hal(d), None, 21, 8.0)),
 "HALLO + above 200-day":                                     ("run", IDX5, lambda d: (hal(d) & up(d), None, 21, 8.0)),
 "HALLO whole season: buy end-Oct, hold to end-Apr":          ("run", IDX5, lambda d: (pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index) & (nm(d) == 11), d.index.to_series().dt.month.eq(4) & pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index), 130, 10.0)),
 "MDD only the dips RSI(4) misses (RSI(4) >= 25)":            ("run", TR, lambda d: (mdd(d) & (F.rsi(d.close, 4) >= 25), d.close > ma(d.close, 5), 10, 3.0)),
}
if __name__ == "__main__":
    print(f"t* = {R.TSTAR:.2f} ({R.NTRIED} ideas tried)")
    for name, (kind, mk, fn) in IDEAS.items():
        R.report(name, kind if kind[0] != "u" else kind, mk, fn)
        if kind[0] == "u":
            t = go(kind, mk, fn); print("              by year since 2018:", " ".join(f"{y}:{v:+.1f}" for y, v in t.groupby(t.t.dt.year).R.sum().items() if y >= 2018))
