"""DK 27 Nov 17:23: "can you improve it, however small, it all counts". One change at a time to the DK v2 long method ('as tested'),
judged on BTC (both halves) AND on the pooled 9 altcoins (a change that only helps BTC is a fit to BTC, not an improvement).
Candidate changes (each from a reason, not a sweep):
  part1      a third off at +1% instead of +1.5% (bank the first bounce sooner - DK: "should have taken profit on the bounce")
  trail      after the partial, trail the rest 2% under the best price (let winners run past +3%)
  tgt4       target +4% (the bounces after deep flushes run further, doc 229: median +9% in 3 days)
  w_even     equal rungs 25/25/25/25 (more size near the first level, which fills more often)
  r5         5 rungs instead of 4 (deeper last bid in violent flushes)
  fill1      bids live 1 day instead of 2 (stale levels)
  ny         a second level set at 13:00 UTC (before the NY open) as well as 07:00 UTC (more campaigns)
  noweekend  no new ladders on Friday/Saturday (weekend raids; DK: "I expect a weekend raid")
  deep12     deep flush at 12% instead of 15%
  stop15     stop 1.5 steps under the deepest bid instead of 1 (the obvious wick gets run)
  t3d        3-day time limit instead of 7"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dk_v2_all_charts as A

def run(d, o):
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; U = d.index; N = len(C)
    dl = pd.DataFrame({"h": d.high.resample("1D").max(), "l": d.low.resample("1D").min(), "c": d.close.resample("1D").last()}).dropna()
    tr = np.maximum(dl.h - dl.l, np.maximum((dl.h - dl.c.shift()).abs(), (dl.l - dl.c.shift()).abs())); day = U.floor("1D")
    ATRP = (tr.rolling(14).mean() / dl.c).shift(1).reindex(day).values
    UP = ((dl.c > dl.c.rolling(50).mean()) & (dl.c > dl.c.rolling(200, min_periods=120).mean())).shift(1).reindex(day).fillna(False).values
    HI20 = dl.h.rolling(20).max().shift(1).reindex(day).values
    cpi = np.searchsorted(U.values, A.CPI_T.values); taker, maker = 0.0014, 0.0
    hours = o.get("hours") or ((7, 13) if o.get("ny") else (7,))
    starts = np.where(np.isin(U.hour, hours) & (U.minute == 0))[0]
    nr = 5 if o.get("r5") else 4; wts = (0.25,) * 4 if o.get("w_even") else ((0.07, 0.13, 0.2, 0.27, 0.33) if nr == 5 else (0.1, 0.2, 0.3, 0.4))
    p_lvl = 0.01 if o.get("part1") else 0.015; t_lvl = 0.04 if o.get("tgt4") else 0.03; fillb = 96 if o.get("fill1") else 192
    deep_th = 0.12 if o.get("deep12") else 0.15; stop_k = 1.5 if o.get("stop15") else 1.0; days = 3 if o.get("t3d") else 7
    out = []; busy = -1
    for j in starts:
        if j < 96 * 30 or j >= N - 96 * 8 or j <= busy or not np.isfinite(ATRP[j]) or not np.isfinite(HI20[j]): continue
        if o.get("noweekend") and U[j].dayofweek in (4, 5): continue
        a = ATRP[j]; lvl = L[j - 96:j].min() * 0.997
        if C[j - 1] > lvl * 1.03: continue
        if not (C[j] <= HI20[j] * (1 - deep_th) or UP[j]): continue
        step = float(np.clip(0.3 * a, 0.006, 0.03)); rungs = [lvl * (1 - step * r) for r in range(nr)]; stop = rungs[-1] * (1 - stop_k * step)
        nc = cpi[np.searchsorted(cpi, j + 1)] if np.searchsorted(cpi, j + 1) < len(cpi) else 10 ** 9
        qty = cost = pnl = 0.0; part = False; done = [False] * nr; k1 = None; res = None; kend = min(N - 1, j + 96 * days); best = 0
        for k in range(j, kend + 1):
            for r in range(nr):
                if not done[r] and k <= j + fillb and L[k] <= rungs[r]: done[r] = True; qty += wts[r]; cost += wts[r] * rungs[r]; k1 = k1 if k1 is not None else k
            if qty <= 0:
                if k > j + fillb: break
                continue
            avg = cost / qty; best = max(best, H[k])
            if L[k] <= stop: res = pnl + qty * (stop * (1 - taker) - avg); break
            if k >= nc - 1: res = pnl + qty * (C[k] * (1 - taker) - avg); break
            if not part and k > k1 and H[k] >= avg * (1 + p_lvl):
                q = qty / 3; pnl += q * avg * p_lvl; qty -= q; cost = avg * qty; part = True
            if o.get("trail") and part: stop = max(stop, best * 0.98)
            if not o.get("trail") and k > k1 and H[k] >= avg * (1 + t_lvl): res = pnl + qty * avg * t_lvl; break
        if qty <= 0 and res is None: continue
        if res is None: avg = cost / qty; res = pnl + qty * (C[kend] * (1 - taker) - avg); k = kend
        out.append((U[j], res / lvl * 100)); busy = max(k, j + 96)
    return pd.Series([v for _, v in out], index=pd.DatetimeIndex([a for a, _ in out]))

def stats(t):
    h = len(t) // 2; return round(t.mean(), 3), round(t[:h].mean(), 3), round(t[h:].mean(), 3), len(t)

if __name__ == "__main__":
    ALTS = ("ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")
    DATA = {s: A.coin(s) for s in ("BTCUSDT",) + ALTS}
    rows = []
    for lab in ("v2 (base)", "part1", "trail", "tgt4", "w_even", "r5", "fill1", "ny", "noweekend", "deep12", "stop15", "t3d"):
        o = {} if lab == "v2 (base)" else {lab: True}
        b = run(DATA["BTCUSDT"], o); alts = pd.concat([run(DATA[s], o) for s in ALTS]).sort_index()
        bm, bh1, bh2, bn = stats(b); am, ah1, ah2, an = stats(alts)
        rows.append(dict(change=lab, btc_n=bn, btc_mean=bm, btc_h1=bh1, btc_h2=bh2, btc_total=round(b.sum(), 1), alts_n=an, alts_mean=am, alts_h1=ah1, alts_h2=ah2, alts_total=round(alts.sum(), 1)))
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows); base = R.iloc[0]
    R["keeps"] = (R.btc_mean > base.btc_mean) & (R.btc_h1 > 0) & (R.btc_h2 > 0) & (R.alts_mean > base.alts_mean) & (R.alts_h2 >= base.alts_h2)
    R.to_csv("runs/research/dk_v2_improve.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
