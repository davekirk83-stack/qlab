"""15 Nov (DK 14 Nov: "I don't think you're using fib extensions enough" / "Most algos use it"). When a day's range breaks, where does the
breaking day's extreme stop, measured as an extension of the prior range? (ext = (H - low)/(H - L) for breaks down; mirror for up.)
Are extremes more likely within +/-tol of 1.272/1.414/1.618/2.0/2.618 than at non-Fibonacci levels in the same zone?
Baseline: the same window around a set of shifted 'fake' levels (each Fib level +0.06), so the density of the distribution itself is controlled."""
import json, urllib.request, sys, numpy as np, pandas as pd
FIB = np.array([1.272, 1.414, 1.618, 2.0, 2.618]); FAKE = FIB + 0.06
def get(sym, iv, n=6):
    k = []; end = None
    for _ in range(n):
        u = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval={iv}&limit=1000" + (f"&endTime={end}" if end else "")
        r = json.load(urllib.request.urlopen(u, timeout=30)); k = r + k; end = r[0][0] - 1
    d = pd.DataFrame(k).iloc[:, :5].astype(float); d.columns = "t o h l c".split(); return d.drop_duplicates("t").reset_index(drop=True)
def exts(d):
    H, L = d.h.values, d.l.values; out = []
    for i in range(1, len(d)):
        R = H[i-1] - L[i-1]
        if R <= 0: continue
        if L[i] < L[i-1]: out.append((H[i-1] - L[i]) / R)
        if H[i] > H[i-1]: out.append((H[i] - L[i-1]) / R)
    return np.array(out)
def hit(e, lv, tol): return np.mean([np.any(np.abs(x - lv) <= tol) for x in e])
for sym, iv, n in (("BTCUSDT", "1d", 4), ("BTCUSDT", "4h", 6), ("ETHUSDT", "1d", 4)):
    d = get(sym, iv, n); e = exts(d); e = e[(e > 1.2) & (e < 2.75)]
    for tol in (0.01, 0.02):
        f, g = hit(e, FIB, tol), hit(e, FAKE, tol)
        print(f"{sym} {iv}: breaks with extreme in 1.2-2.75 n {len(e)} | within ±{tol} of Fib levels {100*f:.1f}% vs shifted levels {100*g:.1f}% | ratio {f/g:.2f}")
    for lv in FIB:
        print(f"   {lv}: Fib ±0.02 {100*np.mean(np.abs(e-lv)<=0.02):.1f}%  vs +0.06 {100*np.mean(np.abs(e-lv-0.06)<=0.02):.1f}%  vs -0.06 {100*np.mean(np.abs(e-lv+0.06)<=0.02):.1f}%")
