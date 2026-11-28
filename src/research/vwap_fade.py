"""Doc 283: the intraday search's dominant survivor, run as REAL trades (one position at a time per market, no overlapping signals, per
trade, not per day - the checker's doc 282 point). VWAP FADE: on a 15-min close more than K x the 20-bar average bar range above the
session VWAP -> short at the next bar's open; below -> long. Exit: the first 15-min close back across the VWAP, else the last bar's close
(flat every night). Optional stop (S x average range from entry). Costs per side: index ETFs 0.02%, stocks 0.03%; IG NQ in points:
1.0 pt round-trip spread + 0.5 pt slippage each side (2 pts per round trip).
Markets: SPY, QQQ, IWM (2021-26), 13 stocks, commodity ETFs, IG NQ (Oct 2025 - Nov 2026). Halves, by year, worst trade, trades per day."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I

def run(d, K=1.5, stop=None, cost=0.0002, pts=False, exit_rule="vwap", start_bar=0, end_bar=25):
    o, h, l, c, vw = d.open.values, d.high.values, d.low.values, d.close.values, d.vwap.values; b, nb = d.b.values, d.nb.values
    rng = (d.high - d.low).values; ar = pd.Series(rng).rolling(20).mean().shift(1).values; n = len(c); out = []; i = 0
    while i < n - 1:
        if b[i] >= nb[i] - 1 or not np.isfinite(ar[i]) or b[i] < start_bar or b[i] > end_bar: i += 1; continue
        s = -1 if c[i] > vw[i] + K * ar[i] else (1 if c[i] < vw[i] - K * ar[i] else 0)
        if s == 0: i += 1; continue
        e = o[i + 1]; last = i + (nb[i] - 1 - b[i]); st = e - s * stop * ar[i] if stop else None; x = None; j = i + 1
        for j in range(i + 1, last + 1):
            if st is not None and ((s == 1 and l[j] <= st) or (s == -1 and h[j] >= st)): x = st if not ((s == 1 and o[j] < st) or (s == -1 and o[j] > st)) else o[j]; break
            if exit_rule == "vwap" and ((s == 1 and c[j] >= vw[j]) or (s == -1 and c[j] <= vw[j])): x = c[j]; break
        if x is None: x = c[last]; j = last
        r = s * (x - e) - (2.0 if pts else 0.0) if pts else s * (x / e - 1) - 2 * cost
        out.append((d.index[i], s, r, j - i, e)); i = j + 1
    return pd.DataFrame(out, columns=["t", "side", "r", "bars", "entry"])

def summ(T, lab, pts=False):
    if len(T) < 10: return dict(test=lab, n=len(T))
    T = T.sort_values("t"); r = T.r if pts else 100 * T.r; h = len(r) // 2; days = T.t.dt.normalize().nunique(); yrs = (T.t.iloc[-1] - T.t.iloc[0]).days / 365.25
    y = r.groupby(T.t.dt.year.values).sum()
    return dict(test=lab, n=len(r), per_day=round(len(r) / max(1, days), 2), per_yr=round(len(r) / max(yrs, 0.1)), win=round((r > 0).mean(), 3), mean=round(r.mean(), 3),
                h1=round(r[:h].mean(), 3), h2=round(r[h:].mean(), 3), long=round(r[T.side == 1].mean(), 3), short=round(r[T.side == -1].mean(), 3),
                worst=round(r.min(), 2), p5=round(np.percentile(r, 5), 3), years=" ".join(f"{k}:{v:+.0f}" for k, v in y.items()), bars=round(T.bars.mean(), 1))

if __name__ == "__main__":
    spy = I.rth("data_alpaca/SPY_15m.csv.gz"); spy_day = spy.close / spy.groupby(spy.index.normalize()).open.transform("first") - 1
    D = {}
    for f in sorted(glob.glob("data_alpaca/*_15m.csv.gz")):
        s = os.path.basename(f).split("_")[0]; x = I.rth(f)
        if len(x) > 5000: D[s] = I.features(x, spy_day)[0]
    q = I.rth("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/nq15.csv"); NQ = I.features(q, spy_day)[0]
    rows = []
    for K in (1.0, 1.5, 2.0, 2.5):
        for stop in (None, 1.0, 2.0):
            for ex in ("vwap", "eod"):
                idx = pd.concat([run(D[s], K, stop, 0.0002, exit_rule=ex) for s in I.IDXE]); stk = pd.concat([run(D[s], K, stop, 0.0003, exit_rule=ex) for s in D if s not in I.IDXE and s not in I.COMM])
                com = pd.concat([run(D[s], K, stop, 0.0003, exit_rule=ex) for s in D if s in I.COMM]); nq = run(NQ, K, stop, pts=True, exit_rule=ex)
                lab = f"K={K} stop={stop} exit={ex}"
                for nm, T, p in (("index ETFs %", idx, False), ("stocks %", stk, False), ("commodity ETFs %", com, False), ("IG NQ pts", nq, True)):
                    rows.append(dict(market=nm, **summ(T, lab, p)))
        print("K", K, "done", flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/vwap_fade.csv", index=False); pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 60)
    for m, g in R.groupby("market", sort=False): print("\n==", m); print(g.drop(columns="market").to_string(index=False))
