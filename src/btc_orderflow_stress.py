"""Doc 191 iteration 2 — the same order-flow signals, but only where they should matter: after a STRESS move
(BTC down/up >= k x its 30-day typical 24h move within the last 24h). Dev 2020-2023 / hold 2024+. Shows base rate under stress too."""
import numpy as np, pandas as pd
exec(open("src/btc_orderflow_test.py").read().split("# 15m bars")[0].replace('runs/btc_orderflow_test.txt', 'runs/btc_orderflow_stress.txt'))
b = m.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "delta": "sum"}).dropna()
b["t_end"] = b.index + pd.Timedelta(minutes=14)
lo16 = b.low.rolling(16).min(); hi16 = b.high.rolling(16).max(); atLow = b.low <= lo16; atHigh = b.high >= hi16
dz = (b.delta - b.delta.shift(1).rolling(384).mean()) / b.delta.shift(1).rolling(384).std()
pos = (b.close - b.low) / (b.high - b.low).replace(0, np.nan)
r24 = b.close / b.close.shift(96) - 1
typ = r24.abs().rolling(96 * 30).median().shift(96)
cvd = b.delta.rolling(96).sum()
# delta exhaustion: selling delta over the last 4 bars smaller than over the 4 bars before, while price lower
d4 = b.delta.rolling(4).sum()
log("STRESS-CONDITIONED order flow. stress = 24h move beyond k x the 30-day median absolute 24h move.")
for k in (2.0, 3.0):
    sD = r24 <= -k * typ; sU = r24 >= k * typ
    log(f"\n k = {k}  (down-stress bars {int(sD.sum())}, up-stress {int(sU.sum())})")
    report("base: any 4h low in stress", fwd(pd.DatetimeIndex(b.t_end[atLow & sD]), 1), fwd(pd.DatetimeIndex(b.t_end[atLow]), 1))
    report("A absorption, stress -> long", fwd(pd.DatetimeIndex(b.t_end[atLow & sD & (dz <= -1.5) & (pos >= 0.5)]), 1), fwd(pd.DatetimeIndex(b.t_end[atLow & sD]), 1))
    report("A2 absorption z<=-2.5", fwd(pd.DatetimeIndex(b.t_end[atLow & sD & (dz <= -2.5) & (pos >= 0.6)]), 1), fwd(pd.DatetimeIndex(b.t_end[atLow & sD]), 1))
    report("E delta exhaustion, stress", fwd(pd.DatetimeIndex(b.t_end[atLow & sD & (d4 < 0) & (d4 > d4.shift(4))]), 1), fwd(pd.DatetimeIndex(b.t_end[atLow & sD]), 1))
    report("E' NO exhaustion (selling growing)", fwd(pd.DatetimeIndex(b.t_end[atLow & sD & (d4 < 0) & (d4 <= d4.shift(4))]), 1), fwd(pd.DatetimeIndex(b.t_end[atLow & sD]), 1))
    report("base: any 4h high in up-stress -> short", fwd(pd.DatetimeIndex(b.t_end[atHigh & sU]), -1), fwd(pd.DatetimeIndex(b.t_end[atHigh]), -1))
    report("A absorption at high, up-stress", fwd(pd.DatetimeIndex(b.t_end[atHigh & sU & (dz >= 1.5) & (pos <= 0.5)]), -1), fwd(pd.DatetimeIndex(b.t_end[atHigh & sU]), -1))
log("done")
