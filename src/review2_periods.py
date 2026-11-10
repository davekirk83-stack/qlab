"""Doc 216 — DK 10:46: test the reviewer's new candidates for repeatable 'worst periods' (doc 201 method, walk-forward by year).
A bucket (month / weekday / VIX band at the prior close / MARKET) is switched off in year Y only if it was negative (>= 10 trades) in all
years BEFORE Y (>= 8 of them). Plus a 'paradigm' switch: trade the book in year Y only if its own previous 3 years were positive.
Adopted only if, out of sample, it raises the total and keeps >= 50% of trades."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review2_new_books as N, fifty_ideas as F
vix = F.D["VIX"].close; vprev = vix.shift(1)
def books():
    A = N.ALL; B = {}
    B["Donchian 55 long"] = sum([N.run_side(k, N.hi(F.D[k], 55) & N.up(F.D[k]), 1, N.lo(F.D[k], 20), 250, 2.0) for k in A], [])
    B["Donchian 55 short"] = sum([N.run_side(k, N.lo(F.D[k], 55) & N.dn(F.D[k]), -1, N.hi(F.D[k], 20), 250, 2.0) for k in A], [])
    B["Donchian 20 long"] = sum([N.run_side(k, N.hi(F.D[k], 20) & N.up(F.D[k]), 1, N.lo(F.D[k], 10), 250, 2.0) for k in A], [])
    def sq(k, side):
        d = F.D[k]; w, ub, lb = N.bbw(d); low = w < w.rolling(100).quantile(0.10); pre = low.rolling(5).max().astype(bool)
        return N.run_side(k, pre & ((d.close > ub) if side == 1 else (d.close < lb)) & (N.up(d) if side == 1 else N.dn(d)), side, None, 60, 2.0, trail=3.0)
    B["Bollinger squeeze up"] = sum([sq(k, 1) for k in A], []); B["Bollinger squeeze down"] = sum([sq(k, -1) for k in A], [])
    def mare(k):
        d = F.D[k]; e20, e50, e200 = N.ema(d.close, 20), N.ema(d.close, 50), N.ema(d.close, 200)
        touched = (d.low <= e20).rolling(3).max().astype(bool); e = (d.close > e200) & (e20 > e50) & touched & (d.close > e20) & (d.close.shift(1) <= e20.shift(1))
        return N.run_side(k, e, 1, d.close < e50, 60, 2.0)
    B["MA re-entry"] = sum([mare(k) for k in A], [])
    return {k: pd.DataFrame(v, columns=["t", "R", "m"]).sort_values("t").reset_index(drop=True) for k, v in B.items()}
NM = {"month": lambda k: ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(k)],
      "weekday": lambda k: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][int(k)], "vix": lambda k: ["VIX<15", "VIX 15-20", "VIX 20-30", "VIX>30"][int(k)], "market": str}
if __name__ == "__main__":
    for name, t in books().items():
        yrs = t.t.dt.year; v = vprev.reindex(t.t.dt.normalize()).ffill().values
        bk = {"month": t.t.dt.month, "weekday": t.t.dt.dayofweek, "vix": pd.Series(pd.cut(v, [0, 15, 20, 30, 300], labels=[0, 1, 2, 3]), index=t.index).astype(float), "market": t.m}
        print(f"\n== {name}: n{len(t)}, mean {t.R.mean():+.3f}, total {t.R.sum():+.1f} ATR", flush=True)
        best = None
        for dim, key in bk.items():
            keep, base, kept, tot = 0.0, 0.0, 0, 0
            for y in sorted(yrs.unique()):
                past = t[yrs < y]
                if past.t.dt.year.nunique() < 8: continue
                m = past.groupby(key[yrs < y]).R.mean(); c = past.groupby(key[yrs < y]).R.size(); off = set(m[(m < 0) & (c >= 10)].index)
                cur = t[yrs == y]; on = cur[~key[yrs == y].isin(off)]; keep += on.R.sum(); base += cur.R.sum(); kept += len(on); tot += len(cur)
            ok = keep > base and kept >= 0.5 * tot
            print(f"  {dim:8s} out of sample: all {base:+.1f} -> switched {keep:+.1f} ATR, trades kept {kept}/{tot} | {'HELPS' if ok else 'no help'}{' — and turns it POSITIVE' if ok and keep > 0 >= base else ''}")
        ys = t.groupby(yrs).R.sum(); on_y = [y for y in ys.index if y - 3 in ys.index and ys.loc[y - 3:y - 1].sum() > 0]
        keep = ys.loc[on_y].sum() if on_y else 0.0; base = ys[ys.index >= ys.index.min() + 3].sum()
        print(f"  paradigm (trade a year only if the previous 3 were positive): all {base:+.1f} -> switched {keep:+.1f} ATR, years traded {len(on_y)}/{len(ys) - 3} | "
              f"{'HELPS' if keep > base else 'no help'} | on in 2026: {2026 in on_y}")
