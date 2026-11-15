"""15 Nov: scale-in bids at Fibonacci extensions of the previous bar's range (DK: small chunks at stacked levels; fib extensions).
Each bar: resting BUYs at H - f x R for f in RUNGS (R = previous bar's range); a rung fills if the bar's low reaches it (maker 0%).
Each filled rung: take profit +TP% (limit), stop at the 3.618 extension (taker 0.09% + 0.05% slip), else exit at the close after HOLD bars.
Control: identical rungs shifted +0.06 (non-Fib levels). £ at 1% of £500 per rung (£5 notional... reported per £100 notional)."""
import json, urllib.request, numpy as np, pandas as pd
RUNGS = [1.272, 1.618, 2.0, 2.618]; TAKER = 0.0014
def get(sym, iv, n):
    k = []; end = None
    for _ in range(n):
        u = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval={iv}&limit=1000" + (f"&endTime={end}" if end else "")
        r = json.load(urllib.request.urlopen(u, timeout=30)); k = r + k; end = r[0][0] - 1
    d = pd.DataFrame(k).iloc[:, :5].astype(float); d.columns = "t o h l c".split(); d = d.drop_duplicates("t").reset_index(drop=True); d["t"] = pd.to_datetime(d.t, unit="ms"); return d
def run(d, rungs, tp, hold, stop_f=3.618):
    O, H, L, C = d.o.values, d.h.values, d.l.values, d.c.values; out = []
    for i in range(1, len(d) - hold - 1):
        R = H[i-1] - L[i-1]
        if R <= 0: continue
        st = H[i-1] - stop_f * R
        for f in rungs:
            px = H[i-1] - f * R
            if L[i] > px or px <= st: continue
            tgt = px * (1 + tp); res = None
            if L[i] <= st: res = st * (1 - TAKER) / px - 1     # same bar: stop first (conservative)
            else:
                for j in range(i + 1, i + 1 + hold):
                    if L[j] <= st: res = st * (1 - TAKER) / px - 1; break
                    if H[j] >= tgt: res = tp; break
                if res is None: res = C[i + hold] * (1 - TAKER) / px - 1
            out.append((d.t[i], f, res))
    return pd.DataFrame(out, columns=["t", "f", "r"])
if __name__ == "__main__":
    for sym, iv, n, tp, hold in (("BTCUSDT", "1d", 4, 0.03, 3), ("BTCUSDT", "4h", 8, 0.02, 6), ("ETHUSDT", "1d", 4, 0.03, 3)):
        d = get(sym, iv, n)
        for nm, rg in (("Fib", RUNGS), ("shifted +0.06", [x + 0.06 for x in RUNGS])):
            t = run(d, rg, tp, hold); yrs = (t.t.max() - t.t.min()).days / 365.25; g = t.groupby(t.t.dt.year).r.sum()
            print(f"{sym} {iv} {nm:14s}: fills/yr {len(t)/yrs:5.0f}, win {100*(t.r>0).mean():.0f}%, avg {100*t.r.mean():+.2f}%/fill, "
                  f"£ per £100 rung {100*t.r.sum()/yrs:+.0f}/yr, years + {(g>0).sum()}/{len(g)} | by rung " + " ".join(f"{f}:{100*x:+.2f}%" for f, x in t.groupby('f').r.mean().items()))
