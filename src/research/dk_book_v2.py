"""DK approach v2 (DK 27 Nov 16:52: "if you could improve my approach, how would you? Then ... test it for further improvements").
Claude's deductions from the v1 test (doc 270) and the other studies:
  1. Longs only made money 2021-23. Every one of the 2024-26 losses came from bidding ordinary dips in a falling market. The daily
     flush-reclaim test (flush_reclaim.py) shows the bounces that still pay are after DEEP flushes (>= 15-20% off the 20-day high).
     -> v2 bids longs only in a deep flush, or when the trend is up (above the 50-day AND the 200-day).
  2. A fixed 1% ladder spacing is too tight in a violent flush and too wide in a quiet one. -> rungs spaced by volatility:
     step = 0.3 x the daily ATR% (clipped 0.6%-3%); stop 1 step under the deepest bid.
  3. On longs the breakeven, the confirmation add and the re-entry each LOST money (ablations, doc 270); the partial and the ladder helped.
     -> longs keep the ladder + a third off at +1.5%; no breakeven, no add, no re-entry; target +3%.
  4. On shorts the "free swing" (a third off, then breakeven) is what works, best after a pump (doc 271). -> shorts unchanged from the best
     version: 24h high, only after a >= 6% pump, a third off at -1%.
Run as two sub-books on the same 2021-26 BTC data with their own venue costs (longs Revolut X spot; shorts a perp venue)."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dk_book as D, btc_short_book as SB
H, L, C, N, IX, U = D.H, D.L, D.C, D.N, D.IX, D.U
dly = pd.DataFrame({"h": pd.Series(H, index=U).resample("1D").max(), "l": pd.Series(L, index=U).resample("1D").min(), "c": pd.Series(C, index=U).resample("1D").last()}).dropna()
tr = np.maximum(dly.h - dly.l, np.maximum((dly.h - dly.c.shift()).abs(), (dly.l - dly.c.shift()).abs()))
atrp = (tr.rolling(14).mean() / dly.c).shift(1); ma50 = dly.c.rolling(50).mean().shift(1); ma200 = dly.c.rolling(200).mean().shift(1); hi20 = dly.h.rolling(20).max().shift(1)
day = U.floor("1D")
ATRP = atrp.reindex(day).values; UP = ((dly.c.shift(1) > ma50) & (dly.c.shift(1) > ma200)).reindex(day).fillna(False).values
HI20 = hi20.reindex(day).values

def campaign_v2(j, lvl, o):
    step = float(np.clip(o["k"] * (ATRP[j] if np.isfinite(ATRP[j]) else 0.03), 0.006, 0.03)) if o["volstep"] else 0.01
    rungs = [lvl * (1 - step * r) for r in range(4)]; wts = (0.1, 0.2, 0.3, 0.4)
    stop = rungs[-1] * (1 - step); opt = dict(part=True, be=False, near=False, add=False)
    r = D.manage(j, min(N - 1, j + 96 * 7), 0.0, 0.0, stop, 0, dict(opt, **o.get("mgmt", {})), lvl, filling=(rungs, wts, min(N - 1, j + 192), [False] * 4))
    if r is None: return None
    pnl, kx = r[0], r[1]
    if o.get("reentry") and r[2]:                      # DK: "buys again after each stop-run sweep ... stop under the new low" (fixed 27 Nov audit)
        sw = r[3]
        for k in range(kx + 1, min(N - 1, kx + 32)):
            sw = min(sw, L[k])
            if C[k] > r[4]:
                e = C[k] * (1 + D.SLIP) * (1 + D.TAKER)
                r2 = D.manage(k + 1, min(N - 1, k + 96 * 3), 0.5, 0.5 * e, sw * 0.995, 0, dict(opt, **o.get("mgmt", {})), lvl)
                if r2: pnl += r2[0]; kx = r2[1]
                break
    return pnl / lvl * 100, kx

def run_longs(o, label):
    rows = []; busy = -1
    for j, lvl, _, _ in D.low_events().values:
        j = int(j)
        if j <= busy: continue
        deep = np.isfinite(HI20[j]) and C[j] <= HI20[j] * (1 - o["deep"])
        if o["ctx"] == "deep or uptrend" and not (deep or UP[j]): continue
        if o["ctx"] == "deep only" and not deep: continue
        if o["ctx"] == "v1 (flush or bull)" and not (D.BULL[j] or C[j] <= D.hi72[j] * 0.94): continue
        r = campaign_v2(j, lvl, o)
        if r is None: continue
        rows.append((IX[j], r[0])); busy = max(r[1], j + 96)
    return pd.Series([x for _, x in rows], index=pd.to_datetime([a for a, _ in rows])).sort_index()

def summ(t, label):
    if len(t) < 10: return dict(version=label, n=len(t))
    y = t.groupby(t.index.year).sum(); h = len(t) // 2; eq = t.cumsum()
    return dict(version=label, n=len(t), per_yr=round(len(t) / ((t.index[-1] - t.index[0]).days / 365.25), 1), win=round((t > 0).mean(), 2), mean=round(t.mean(), 3),
                h1=round(t[:h].mean(), 3), h2=round(t[h:].mean(), 3), last12m=round(t[t.index >= t.index[-1] - pd.Timedelta("365D")].mean(), 3),
                years=" ".join(f"{k}:{v:+.0f}" for k, v in y.items()), total=round(t.sum(), 1), max_dd=round((eq - eq.cummax()).min(), 1))

if __name__ == "__main__":
    rows = []
    V2 = dict(ctx="deep or uptrend", deep=0.15, volstep=True, k=0.3)
    tests = [("v1 longs (doc 270 'lows', simple)", dict(ctx="v1 (flush or bull)", deep=0.15, volstep=False, k=0.3, mgmt=dict(part=False))),
             ("v2 LONGS (all improvements)", V2),
             ("v2 without vol-scaled ladder", dict(V2, volstep=False)),
             ("v2 context = v1 (flush or bull)", dict(V2, ctx="v1 (flush or bull)")),
             ("v2 deep flush only (no uptrend dips)", dict(V2, ctx="deep only")),
             ("v2 deep = 10%", dict(V2, deep=0.10)), ("v2 deep = 20%", dict(V2, deep=0.20)),
             ("v2 ladder step 0.5 x ATR", dict(V2, k=0.5)), ("v2 ladder step 0.2 x ATR", dict(V2, k=0.2)),
             ("v2 + breakeven after the partial", dict(V2, mgmt=dict(be=True))), ("v2 without the partial", dict(V2, mgmt=dict(part=False)))]
    S = {}
    for lab, o in tests:
        t = run_longs(o, lab); S[lab] = t; rows.append(summ(t, lab)); print(rows[-1], flush=True)
    sh = SB.run(dict(SB.BASE, part=0.01), "pump", "24h high", "perp"); rows.append(dict(version="v2 SHORTS (24h high after a pump, a third at -1%, free swing; perp)", **sh)); print(rows[-1])
    R = pd.DataFrame(rows); R.to_csv("runs/research/dk_book_v2.csv", index=False); S["v2 LONGS (all improvements)"].to_csv("runs/research/dk_book_v2_longs.csv")
    pd.set_option("display.width", 300); print(R.drop(columns=["years"], errors="ignore").to_string(index=False))
    print("\nv2 longs by year:", R.iloc[1]["years"])
