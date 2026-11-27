"""DK 27 Nov 17:22: "Does it work on stocks or commodities". DK v2 long method on US stocks and commodity ETFs (Alpaca 15-min bars,
2021-26, regular session only). Stocks trade 09:30-16:00 New York, so the ladder is set at each session's open under the previous
session's low (the stock equivalent of 'just under the obvious overnight low'). Both ports: 'as tested' (BTC % rules) and 'vol-scaled'
(each market's daily ATR). Costs as IG share spread bets would roughly be: 0.10% round trip + 0.018%/day overnight funding.
Result = % of the ladder budget per campaign."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dk_v2_all_charts as A
def load(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.ts, utc=True); d = d[["open", "high", "low", "close"]].astype(float)
    ny = d.index.tz_convert("America/New_York"); m = ny.hour * 60 + ny.minute
    return d[(m >= 570) & (m < 960) & (ny.dayofweek < 5)]
def run(d, mode, rt=0.001, fund=0.00018):
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; U = d.index; N = len(C)
    ny = U.tz_convert("America/New_York"); sday = pd.Series(ny.date, index=U)
    dl = pd.DataFrame({"h": d.high.groupby(ny.date).max(), "l": d.low.groupby(ny.date).min(), "c": d.close.groupby(ny.date).last()})
    tr = np.maximum(dl.h - dl.l, np.maximum((dl.h - dl.c.shift()).abs(), (dl.l - dl.c.shift()).abs()))
    atrp = (tr.rolling(14).mean() / dl.c).shift(1); up = ((dl.c > dl.c.rolling(50).mean()) & (dl.c > dl.c.rolling(200, min_periods=120).mean())).shift(1)
    hi20 = dl.h.rolling(20).max().shift(1); plow = dl.l.shift(1)
    first = np.where(sday.values != np.roll(sday.values, 1))[0]
    out = []; busy = -1; spb = 26                                           # 26 x 15-min bars per session
    for j in first:
        dd = sday.iloc[j]
        if j < spb * 30 or j >= N - spb * 8 or j <= busy: continue
        a, u, h20, pl = atrp.get(dd, np.nan), up.get(dd, False), hi20.get(dd, np.nan), plow.get(dd, np.nan)
        if not (np.isfinite(a) and np.isfinite(h20) and np.isfinite(pl)): continue
        lvl = pl * (1 - 0.1 * a if mode == "vol-scaled" else 0.997)
        if O[j] > lvl * (1 + (a if mode == "vol-scaled" else 0.03)): continue
        deep = O[j] <= h20 * (1 - (5 * a if mode == "vol-scaled" else 0.15))
        if not (deep or u): continue
        step = float(np.clip(0.3 * a, 0.006 if mode == "as tested" else 0.1 * a, 0.03)); rungs = [lvl * (1 - step * r) for r in range(4)]; wts = (0.1, 0.2, 0.3, 0.4)
        stop = rungs[-1] * (1 - step); p_lvl, t_lvl = (0.5 * a, 1.0 * a) if mode == "vol-scaled" else (0.015, 0.03)
        qty = cost = pnl = 0.0; part = False; done = [False] * 4; k1 = None; res = None; kend = min(N - 1, j + spb * 7)
        for k in range(j, kend + 1):
            for r in range(4):
                if not done[r] and k <= j + spb * 2 and L[k] <= rungs[r]: done[r] = True; qty += wts[r]; cost += wts[r] * min(rungs[r], O[k]); k1 = k1 if k1 is not None else k
            if qty <= 0:
                if k > j + spb * 2: break
                continue
            avg = cost / qty; hold = (k - k1) / spb * fund
            if L[k] <= stop: res = pnl + qty * (min(stop, O[k]) - avg * (1 + rt + hold)); break      # gap through the stop fills at the open
            if not part and k > k1 and H[k] >= avg * (1 + p_lvl): q = qty / 3; pnl += q * (avg * p_lvl - avg * (rt / 2 + hold)); qty -= q; cost = avg * qty; part = True
            if k > k1 and H[k] >= avg * (1 + t_lvl): res = pnl + qty * (avg * t_lvl - avg * (rt + hold)); break
        if qty <= 0 and res is None: continue
        if res is None: avg = cost / qty; res = pnl + qty * (C[kend] - avg * (1 + rt + (kend - k1) / spb * fund)); k = kend
        out.append((U[j], res / lvl * 100)); busy = max(k, j + spb)
    return pd.Series([v for _, v in out], index=pd.DatetimeIndex([a for a, _ in out]))
if __name__ == "__main__":
    rows = []; pool = {"as tested": {"stocks": [], "commodities": []}, "vol-scaled": {"stocks": [], "commodities": []}}
    COM = {"GLD", "SLV", "USO", "UNG", "CPER", "DBA", "GDX"}
    for f in sorted(glob.glob("data_alpaca/*_15m.csv.gz")):
        s = os.path.basename(f).split("_")[0]; d = load(f)
        for mode in ("as tested", "vol-scaled"):
            t = run(d, mode); grp = "commodities" if s in COM else "stocks"; pool[mode][grp].append(t)
            rows.append(dict(A.summ(t, s, mode, str(d.index[0].date())), group=grp)); print(rows[-1], flush=True)
    for mode in pool:
        for grp, ts in pool[mode].items():
            if ts: rows.append(dict(A.summ(pd.concat(ts).sort_index(), f"ALL {grp.upper()} pooled", mode, "2021"), group=grp))
    R = pd.DataFrame(rows); R.to_csv("runs/research/dk_v2_stocks.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
