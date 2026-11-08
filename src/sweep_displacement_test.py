"""Doc 191 — DK 8 Nov (ICT 'market structure shift'): a STOP RAID (liquidity sweep) alone vs a sweep FOLLOWED BY DISPLACEMENT.
15-min bars. Sweep: a bar trades beyond the prior 16-bar (4h) high/low by >= 0.1 ATR(14). Within the next 2 bars, look for the reversal close:
  RAID ONLY: the first bar that closes back inside the swept level (any size).
  RAID + DISPLACEMENT: that close-back bar has range >= 1.5 ATR and closes in its last 30% in the reversal direction.
Enter at that close against the sweep; stop = sweep extreme + 0.1 ATR; target 2R; exit after 16 bars (4h). Costs: BTC 0.1% round trip,
US Tech 100 1 pt. BTC: dev 2020-23 / hold 2024-26. NQ: A 2020-21 / B 2025-26 (cash session only)."""
import numpy as np, pandas as pd
OUT = open("runs/sweep_displacement_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def bars15(d): return d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def test(q, cost_fn, sess=None):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().shift(1).values
    hh = pd.Series(H).rolling(16).max().shift(1).values; ll = pd.Series(L).rolling(16).min().shift(1).values
    ok = np.ones(len(q), bool) if sess is None else sess
    res = {"raid": [], "disp": []}; i = 20
    while i < len(q) - 20:
        side = 0
        if ok[i] and H[i] >= hh[i] + 0.1 * atr[i]: side, lvl, ext = -1, hh[i], H[i]
        elif ok[i] and L[i] <= ll[i] - 0.1 * atr[i]: side, lvl, ext = 1, ll[i], L[i]
        if not side: i += 1; continue
        for j in range(i, i + 3):
            ext = max(ext, H[j]) if side == -1 else min(ext, L[j])
            if (side == -1 and C[j] < lvl) or (side == 1 and C[j] > lvl):
                e = C[j]; stop = ext - side * 0.1 * atr[i]; risk = abs(e - stop); tgt = e + side * 2 * risk
                disp = (H[j] - L[j]) >= 1.5 * atr[i] and ((side == 1 and (C[j] - L[j]) >= 0.7 * (H[j] - L[j])) or (side == -1 and (H[j] - C[j]) >= 0.7 * (H[j] - L[j])))
                r = None
                for k in range(j + 1, min(j + 17, len(q))):
                    if (side == 1 and L[k] <= stop) or (side == -1 and H[k] >= stop): r = -risk; break
                    if (side == 1 and H[k] >= tgt) or (side == -1 and L[k] <= tgt): r = 2 * risk; break
                if r is None: r = side * (C[min(j + 16, len(q) - 1)] - e)
                R = (r - cost_fn(e)) / risk
                res["raid"].append((q.index[j], R))
                if disp: res["disp"].append((q.index[j], R))
                i = j; break
        i += 1
    return {k: pd.DataFrame(v, columns=["t", "R"]) for k, v in res.items()}
def show(tag, R, split):
    for k, lab in (("raid", "raid only (any close back)"), ("disp", "raid + DISPLACEMENT")):
        X = R[k]; c = []
        for seg, msk in (("dev", X.t < split), ("hold", X.t >= split)):
            x = X[msk]; c.append(f"{seg} n{len(x):5} {x.R.mean():+.3f}R win {100*(x.R>0).mean():3.0f}%")
        log(f"  {tag:12} {lab:28} " + " || ".join(c))
m = pd.read_parquet("data_long/btc_1m.parquet"); qb = bars15(m)
log("STOP RAID vs RAID + DISPLACEMENT — R per trade after costs (target 2R, stop beyond the sweep)")
show("BTC 15m", test(qb, lambda e: 0.001 * e), pd.Timestamp("2024-01-01", tz="UTC"))
show("BTC gross", test(qb, lambda e: 0.0), pd.Timestamp("2024-01-01", tz="UTC"))
show("BTC maker", test(qb, lambda e: 0.0002 * e), pd.Timestamp("2024-01-01", tz="UTC"))
for tag, f, st in (("NQ A 2020-21", "data_long/nq_5m_2020_21.csv", "2020-01-01"), ("NQ B 2025-26", "data_nq_cache/nq_5m.csv", "2025-10-15")):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated()].sort_index(); d = d[d.index >= st]
    q = bars15(d); lt = q.index.tz_convert("America/New_York"); mn = lt.hour * 60 + lt.minute
    R = test(q, lambda e: 1.0, sess=np.asarray((mn >= 600) & (mn < 945)))
    for k in R: R[k]["t"] = R[k].t
    show(tag, R, pd.Timestamp("2099-01-01", tz="UTC"))
# iteration 2: only sweeps of LOWS during a down-stress move (24h move <= -2x its 30-day median) — the place the stress ladder found the edge
r24 = qb.close / qb.close.shift(96) - 1; typ = r24.abs().rolling(96 * 30).median().shift(96); stressD = np.asarray(r24 <= -2 * typ)
R = test(qb, lambda e: 0.001 * e, sess=stressD)
for k in R: R[k] = R[k]   # longs at swept lows and shorts at swept highs both possible inside stress windows
show("BTC stress", R, pd.Timestamp("2024-01-01", tz="UTC"))
