"""DK 9 Nov ("run the research now"): VolSignals' dealer-hedging forces, tested on price/VIX data alone (no options data).
1) OPEX: monthly options expiry (3rd Friday). S&P 500 daily 1990-2026: range on expiry Friday and in expiry week vs other days;
   return in expiry week vs the week after (the well-known 'week after opex' weakness).
2) VANNA: a VIX crush (VIX down >= 10% on the day) -> dealers buy back hedges -> S&P drift up? Next 1/3/5-day S&P return vs base.
   Also the opposite (VIX spike >= +15%).
3) CHARM into the close: on calm days (prior VIX < 20, no big morning move) does the S&P drift in the last 2 hours (14:00-16:00 NY)
   in a consistent direction? Intraday S&P 500 5-min (IG/Dukascopy cache, Nov 2025 - Nov 2026) and US Tech 100 2020-21.
Splits: daily 1990-2009 / 2010-2026."""
import json, numpy as np, pandas as pd
S = "/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/"
OUT = open("runs/dealer_flow_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def ld(n):
    r = json.load(open(S + n + ".json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=pd.to_datetime(r["timestamp"], unit="s").normalize()).dropna()
spx = ld("GSPC"); vix = ld("VIX").close; spx = spx[spx.index >= "1990-01-02"]
spx["r"] = spx.close.pct_change() * 100; spx["rng"] = (spx.high - spx.low) / spx.close.shift(1) * 100
spx["rngx"] = spx.rng / spx.rng.shift(1).rolling(20).mean()
d = spx.index; third_fri = (d.weekday == 4) & (d.day >= 15) & (d.day <= 21)
spx["opex"] = third_fri
wk = d.to_period("W-FRI"); opex_weeks = set(wk[third_fri]); spx["opexwk"] = [w in opex_weeks for w in wk]
spx["after"] = [(w - 1) in opex_weeks for w in wk]
SPLIT = pd.Timestamp("2010-01-01")
def two(x, f):
    a, b = x[x.index < SPLIT], x[x.index >= SPLIT]
    return f"1990-2009 {f(a)} || 2010-2026 {f(b)}"
log("1) OPTIONS EXPIRY (S&P 500 daily)")
log("  range vs its 20-day mean:  expiry Fri " + two(spx[spx.opex].rngx, lambda s: f"{s.mean():.2f} (n{len(s)})") + " | other days " + two(spx[~spx.opex].rngx, lambda s: f"{s.mean():.2f}"))
wr = spx.groupby(wk).agg(ret=("r", "sum"), opexwk=("opexwk", "first"), after=("after", "first"), t=("close", lambda s: s.index[0]))
wr.index = wr.t
for lab, msk in (("expiry week", wr.opexwk), ("week AFTER expiry", wr.after), ("other weeks", ~wr.opexwk & ~wr.after)):
    log(f"  {lab:18} " + two(wr[msk].ret, lambda s: f"mean {s.mean():+.2f}% up {100*(s>0).mean():.0f}% (n{len(s)})"))
log("\n2) VANNA (VIX daily moves -> S&P next days)")
vc = vix.pct_change().reindex(spx.index) * 100
for n in (1, 3, 5): spx[f"f{n}"] = (spx.close.shift(-n) / spx.close - 1) * 100
for lab, msk in (("VIX crush <= -10%", vc <= -10), ("VIX down 5-10%", (vc > -10) & (vc <= -5)), ("VIX spike >= +15%", vc >= 15), ("all days", vc.notna())):
    x = spx[msk]
    log(f"  {lab:18} " + " | ".join(f"+{n}d " + two(x[f'f{n}'].dropna(), lambda s: f"{s.mean():+.2f}% ({100*(s>0).mean():.0f}%)") for n in (1, 5)) + f"  n{int(msk.sum())}")
log("\n3) CHARM INTO THE CLOSE (last 2 hours, 14:00-16:00 New York)")
for name, f in (("US 500 2025-26", "data_ig_cache/USA500IDXUSD_5m.csv"), ("US Tech 100 2020-21", "data_long/nq_5m_2020_21.csv"), ("US Tech 100 2025-26", "data_nq_cache/nq_5m.csv")):
    b = pd.read_csv(f, index_col=0); b.index = pd.to_datetime(b.index, utc=True); b = b[~b.index.duplicated()].sort_index()
    lt = b.index.tz_convert("America/New_York"); b["day"] = lt.date; b["m"] = lt.hour * 60 + lt.minute
    rows = []
    for day, g in b[(b.m >= 570) & (b.m < 960)].groupby("day"):
        if len(g) < 70: continue
        o = g.open.iloc[0]; p14 = g[g.m < 840].close.iloc[-1]; c = g.close.iloc[-1]
        rows.append(dict(day=pd.Timestamp(day), am=(p14 / o - 1) * 100, pm=(c / p14 - 1) * 100, opex=pd.Timestamp(day).weekday() == 4 and 15 <= pd.Timestamp(day).day <= 21))
    D = pd.DataFrame(rows).set_index("day"); D["vix"] = vix.shift(1).reindex(D.index).values
    calm = (D.vix < 20) & (D.am.abs() < 0.5)
    log(f"  {name}: days {len(D)}")
    for lab, msk in (("all days", D.index == D.index), ("calm (VIX<20, small morning)", calm), ("stressed (VIX>=20)", D.vix >= 20), ("expiry Fridays", D.opex)):
        x = D[msk]
        same = np.sign(x.pm) == np.sign(x.am)
        log(f"    {lab:28} n{len(x):3} last-2h mean {x.pm.mean():+.3f}% up {100*(x.pm>0).mean():.0f}% | continues the morning's direction {100*same.mean():.0f}%")
