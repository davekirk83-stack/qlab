"""Doc 199 — DK 22:45: "Find out when the bad periods are for each book historically". For each shortlisted book, its results split by
things knowable IN ADVANCE: month of year, day of week, hour (intraday books), and the VIX level at the previous close (calm < 15,
normal 15-20, elevated 20-30, stressed > 30). Units: ATR per trade (mean) and the bucket total. Descriptive only — a bucket is a candidate
'fallow' period only if it is bad in BOTH halves of the history (checked below); the switch itself still has to pass the walk-forward test."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).normalize(); vprev = vix.close.shift(1)
BOOKS = {"Trend (IG quarterly bets)": ("runs/gate/TREND100_IG_quarterly_bets_18_markets_trades.csv", True),
         "RSI(2) pullback": ("runs/gate/RSI2_8_markets_trades.csv", True),
         "Turn of the month": ("runs/gate/TURN-OF-MONTH_6_indices_trades.csv", True),
         "Ignition (US hours)": ("runs/gate/IGNITION_v1.1_US_Tech_100_trades.csv", False),
         "Gold London breakout": ("runs/gate/GOLD_London_breakout_of_Asian_range_trades.csv", False),
         "Noise band US Tech 100": ("runs/gate/NOISEBAND_US_Tech_100_trades.csv", False),
         "Ignition all hours + regime + coil": ("runs/gate/AD_ignition_+_REGIME_+_COIL_trades.csv", False)}
out = []
def p(s): print(s, flush=True); out.append(s)
for name, (f, daily) in BOOKS.items():
    if not os.path.exists(f): p(f"{name}: no trades file"); continue
    t = pd.read_csv(f, parse_dates=["t"]); t["t"] = pd.to_datetime(t.t, utc=True)
    v = vprev.reindex(t.t.dt.normalize()).ffill().values
    t["vix"] = pd.cut(v, [0, 15, 20, 30, 200], labels=["VIX<15", "15-20", "20-30", ">30"])
    t["month"] = t.t.dt.month_name().str[:3]; t["dow"] = t.t.dt.day_name().str[:3]; t["hour_ny"] = t.t.dt.tz_convert("America/New_York").dt.hour
    half = t.t < t.t.iloc[len(t) // 2]
    p(f"\n== {name}: n{len(t)}, {t.t.min().date()}..{t.t.max().date()}, mean {t.R.mean():+.3f} ATR")
    for col in (["month", "vix", "dow"] if daily else ["hour_ny", "dow", "vix"]):
        g = t.groupby(col).R.agg(["size", "mean", "sum"])
        h1 = t[half].groupby(col).R.mean(); h2 = t[~half].groupby(col).R.mean()
        bad = [str(k) for k in g.index if g.loc[k, "size"] >= 8 and h1.get(k, 0) < 0 and h2.get(k, 0) < 0]
        cells = "  ".join(f"{k}:{g.loc[k,'mean']:+.2f}(n{int(g.loc[k,'size'])})" for k in g.index if g.loc[k, "size"] > 0)
        p(f"  by {col}: {cells}")
        p(f"    bad in BOTH halves: {', '.join(bad) if bad else 'none'}")
open("runs/gate/bad_periods.txt", "w").write("\n".join(out) + "\n")
