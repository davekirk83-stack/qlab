"""Range v3 on FX, commodities and bonds (task 10, 24 Oct 2026) — the doc 116 template on IG spread-bet costs.
IG spreads (typical, points of the quoted price): EUR/USD 0.6 pip, GBP/USD 0.9, USD/JPY 0.7, AUD/USD 0.6, USD/CAD 1.7, USD/CHF 1.5;
silver 2.0 (cents), Brent 2.8 (cents), WTI 2.8, copper (per IG 'High Grade Copper' ~ 0.3), Bund 2.0 (ticks of 0.01), gilt 2.0."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); from range_index_test import load, run
from scipy.stats import norm
SPEC = {"EURUSD": 0.00006, "GBPUSD": 0.00009, "USDJPY": 0.007, "AUDUSD": 0.00006, "USDCAD": 0.00017, "USDCHF": 0.000015*10,
        "XAGUSD": 0.02, "BRENTCMDUSD": 0.028, "LIGHTCMDUSD": 0.028, "COPPERCMDUSD": 0.03, "BUNDTREUR": 0.02, "UKGILTTRGBP": 0.02}
rows = []
for name, sp in SPEC.items():
    f = f"/home/claude/qlab/data_ig_cache/{name}_5m.csv"
    if not os.path.exists(f): continue
    b = load(f)
    if len(b) < 2000: print(f"{name}: only {len(b)} 15-min bars so far — skipped"); continue
    r = run(name, b, sp); h1 = run(name, b, sp, half=1); h2 = run(name, b, sp, half=2)
    if not r: print(name, "no episodes"); continue
    rows.append((name, len(b), r["n"], r["per_ep"], r["ctrl"], r["t"], r["win"], h1["per_ep"] if h1 else np.nan, h2["per_ep"] if h2 else np.nan, r["eps_per_week"], r["hows"]))
df = pd.DataFrame(rows, columns=["instr", "bars15", "n", "per_ep%", "ctrl%", "t", "win", "H1%", "H2%", "eps/wk", "exits"])
pd.set_option("display.width", 220); print(df.round(3).to_string(index=False))
n = len(df); print(f"\ndeflated bar for {n} instruments (rule 179): t > {norm.ppf(1-0.05/max(n,1)):.2f}; a clear needs that, both halves positive, and per-episode > control")
