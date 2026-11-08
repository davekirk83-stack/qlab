"""Doc 191 — BTC STRESS SNAP-BACK LADDER (spot, long only — fits the Revolut X range-long book).
Arm when BTC's 24h move <= -K x its 30-day median absolute 24h move. While armed (and for 24h after the last stress bar):
buy a rung at each NEW 4h low on a 15m close, rungs >= GAP% apart, max 4 rungs, equal size (25% of the episode budget each).
Absorption boost (variant): a rung whose 15m bar has delta z <= -2.5 and closes in the top 40% of its range buys 2 units.
Exit all: average entry x (1 + TP%) touched, or 48h after the first rung, or a stop at first rung x (1 - SL%).
Costs 0.10% round trip per unit (Revolut X taker ~0.09%). Episode return = P&L / episode budget.
Control: same rung schedule triggered at RANDOM non-stress 4h lows (same count), to show the stress condition is what pays."""
import numpy as np, pandas as pd, itertools
OUT = open("runs/btc_stress_ladder.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
m = pd.read_parquet("data_long/btc_1m.parquet")
b = m.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "delta": "sum"}).dropna()
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
r24 = b.close / b.close.shift(96) - 1; typ = r24.abs().rolling(96 * 30).median().shift(96)
lo16 = b.low.rolling(16).min(); atLow = (b.low <= lo16).values
dz = ((b.delta - b.delta.shift(1).rolling(384).mean()) / b.delta.shift(1).rolling(384).std()).values
pos = ((b.close - b.low) / (b.high - b.low).replace(0, np.nan)).values
H, L, C = b.high.values, b.low.values, b.close.values; T = b.index
def run(K, GAP, TP, SL, boost, control=False, seed=0):
    stress = (r24 <= -K * typ).values
    if control:
        rng = np.random.default_rng(seed); cand = np.where(atLow & ~stress & ~np.isnan(typ.values))[0]
        n_eps = len(run(K, GAP, TP, SL, boost)); starts = set(rng.choice(cand, size=n_eps * 3, replace=False))
    eps = []; i = 3000; N = len(b)
    while i < N - 200:
        trig = (stress[i] and atLow[i]) if not control else (i in starts)
        if not trig: i += 1; continue
        units, cost_basis, first, last_px, t0 = 0, 0.0, C[i], None, i; armed_until = i + 96; k = i; rungs = 0; out = None
        while k < N - 1:
            if stress[k] and not control: armed_until = k + 96
            if rungs < 4 and k <= armed_until and atLow[k] and (last_px is None or C[k] <= last_px * (1 - GAP)):
                u = 2 if (boost and dz[k] <= -2.5 and pos[k] >= 0.6) else 1
                units += u; cost_basis += u * C[k]; last_px = C[k]; rungs += 1
            k += 1
            avg = cost_basis / units
            if L[k] <= first * (1 - SL): out = first * (1 - SL); how = "stop"; break
            if H[k] >= avg * (1 + TP): out = avg * (1 + TP); how = "tp"; break
            if k - t0 >= 192: out = C[k]; how = "time"; break
        if out is None: break
        budget = 4 + (4 if boost else 0)   # units the episode could have used
        pnl = units * out - cost_basis - 0.001 * (cost_basis + units * out) / 2
        eps.append((T[t0], pnl / (first * 4), rungs, how, (k - t0) / 4))
        i = k + 1
    return pd.DataFrame(eps, columns=["t", "ret", "rungs", "how", "hours"])
def summ(E):
    cells = []
    for seg, msk in (("dev", E.t < SPLIT), ("hold", E.t >= SPLIT)):
        x = E[msk]
        if len(x) == 0: cells.append(f"{seg} none"); continue
        cells.append(f"{seg} n{len(x):3} mean {100*x.ret.mean():+5.2f}% win {100*(x.ret>0).mean():3.0f}% worst {100*x.ret.min():+6.1f}% total {100*x.ret.sum():+6.0f}%")
    return " || ".join(cells)
log("BTC STRESS SNAP-BACK LADDER — returns per episode as % of the episode budget, after 0.10% costs")
log("Development grid (2020-2023 only is used to choose; holdout shown alongside but NOT used to choose):")
rows = []
for K, GAP, TP, SL in itertools.product((2.0, 2.5, 3.0), (0.005, 0.01), (0.01, 0.02, 0.03), (0.08, 0.12)):
    E = run(K, GAP, TP, SL, False); d = E[E.t < SPLIT]
    rows.append((K, GAP, TP, SL, len(d), d.ret.mean() if len(d) else np.nan, E))
rows.sort(key=lambda r: -np.nan_to_num(r[5] * np.sqrt(r[4])))
for K, GAP, TP, SL, n, mu, E in rows[:8]:
    log(f"  K{K} gap{GAP*100:.1f}% TP{TP*100:.0f}% SL{SL*100:.0f}%  {summ(E)}")
K, GAP, TP, SL = rows[0][:4]
log(f"\nCHOSEN on development: K{K} gap{GAP*100:.1f}% TP{TP*100:.0f}% SL{SL*100:.0f}%")
E = run(K, GAP, TP, SL, False); log("  plain          " + summ(E))
Eb = run(K, GAP, TP, SL, True); log("  absorption x2  " + summ(Eb))
for s in range(3):
    Ec = run(K, GAP, TP, SL, False, control=True, seed=s); log(f"  CONTROL random non-stress 4h lows (seed {s}) " + summ(Ec))
log("\n  exits (chosen, all years): " + E.how.value_counts().to_dict().__str__() + f"; median hours held {E.hours.median():.1f}")
log("  by year: " + " ".join(f"{y}:{100*g.ret.sum():+.0f}%(n{len(g)})" for y, g in E.groupby(E.t.dt.year)))
E.to_csv("runs/btc_stress_ladder_episodes.csv", index=False)
log("done")
