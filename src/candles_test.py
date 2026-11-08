"""Doc 191 — all TA-Lib candlestick patterns (61) on BTC 1h 2020-2026: plain, and IN CONTEXT.
Signal direction from TA-Lib (+100 bullish / -100 bearish). Forward return over the next 4 and 24 hours in the signal's direction (bp),
vs the unconditional drift. Contexts: (1) at a 24h low/high, (2) at a 24h low/high after a stress move (24h move beyond 2x its 30-day median).
Dev 2020-2023 / hold 2024+. Lists patterns that are positive in BOTH halves with n>=30 in each."""
import numpy as np, pandas as pd, talib
OUT = open("runs/candles_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
m = pd.read_parquet("data_long/btc_1m.parquet")
h = m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
O, H, L, C = (h[c].values.astype(float) for c in ("open", "high", "low", "close"))
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
f4 = (h.close.shift(-4) / h.close - 1) * 1e4; f24 = (h.close.shift(-24) / h.close - 1) * 1e4
r24 = h.close / h.close.shift(24) - 1; typ = r24.abs().rolling(24 * 30).median().shift(24)
lo24 = h.low <= h.low.rolling(24).min(); hi24 = h.high >= h.high.rolling(24).max()
ctx = {"plain": pd.Series(True, index=h.index),
       "at 24h extreme": None, "extreme after stress": None}
rows = []
for name in talib.get_function_groups()["Pattern Recognition"]:
    s = pd.Series(getattr(talib, name)(O, H, L, C), index=h.index)
    sig = np.sign(s)
    for cname in ("plain", "at 24h extreme", "extreme after stress"):
        if cname == "plain": mask = sig != 0
        elif cname == "at 24h extreme": mask = ((sig > 0) & lo24) | ((sig < 0) & hi24)
        else: mask = ((sig > 0) & lo24 & (r24 <= -2 * typ)) | ((sig < 0) & hi24 & (r24 >= 2 * typ))
        out = [name[3:], cname]
        ok = True
        for seg, sm in (("dev", h.index < SPLIT), ("hold", h.index >= SPLIT)):
            mm = mask & sm
            a4 = (sig[mm] * f4[mm]).dropna(); a24 = (sig[mm] * f24[mm]).dropna()
            out += [len(a4), a4.mean(), a24.mean(), 100 * (a24 > 0).mean() if len(a24) else np.nan]
            ok &= len(a4) >= 30 and a4.mean() > 0 and a24.mean() > 0
        rows.append(out + [ok])
R = pd.DataFrame(rows, columns=["pattern", "context", "n_dev", "dev4", "dev24", "devwin24", "n_hold", "hold4", "hold24", "holdwin24", "both"])
R.to_csv("runs/candles_test.csv", index=False)
log(f"BTC 1h, {len(talib.get_function_groups()['Pattern Recognition'])} TA-Lib patterns. Unconditional 24h drift: dev {f24[h.index<SPLIT].mean():+.1f}bp, hold {f24[h.index>=SPLIT].mean():+.1f}bp (long side)")
for cname in ("plain", "at 24h extreme", "extreme after stress"):
    g = R[R.context == cname]
    tested = g[(g.n_dev >= 30) & (g.n_hold >= 30)]
    log(f"\n[{cname}] patterns with >=30 cases in each half: {len(tested)}; positive at 4h AND 24h in BOTH halves: {int(tested.both.sum())}")
    for r in tested[tested.both].sort_values("hold24", ascending=False).itertuples():
        log(f"   {r.pattern:20} dev n{r.n_dev:5} 4h {r.dev4:+6.1f} 24h {r.dev24:+6.1f}bp ({r.devwin24:.0f}%) || hold n{r.n_hold:5} 4h {r.hold4:+6.1f} 24h {r.hold24:+6.1f}bp ({r.holdwin24:.0f}%)")
