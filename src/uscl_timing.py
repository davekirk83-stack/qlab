"""Doc 209 — USCL entry timing on Dukascopy minutes: buy DAX/FTSE at the US close (IG prices them out of hours) vs at the European open.
Signal: US 500 closes in top 10% of range and +1% (daily). Entry 15:50 New York on signal day; exits: Europe open (08:05 London) or Europe close (16:25 London) next day.
Costs: IG out-of-hours spread (DAX 5pt, FTSE 4pt round trip, worst case) + 1 night funding 2.3bp. Stop ignored (reported pre-stop)."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import fifty_ideas as F
DL = "/home/claude/qlab-git/data_long"; S = F.D["SPX"]
sig = ((S.close - S.low) / (S.high - S.low) >= 0.9) & (S.close / S.close.shift(1) - 1 >= 0.01); days = S.index[sig & (S.index >= "2012-01-01")]
def bars(instr, d):
    f = f"{DL}/{instr}/{d.date()}.npz"
    if not os.path.exists(f): return None
    x = np.load(f)["x"]
    if len(x) == 0: return None
    return pd.Series(x[:, 4] / 1000.0, index=(pd.Timestamp(d.date()) + pd.to_timedelta(x[:, 0], unit="s")).tz_localize("UTC"))
def at(s, ts):
    s2 = s[s.index <= ts]; return s2.iloc[-1] if len(s2) and (ts - s2.index[-1]) < pd.Timedelta("20min") else np.nan
SPREAD = {"DEUIDXEUR": 5.0, "GBRIDXGBP": 4.0}; DM = {"DEUIDXEUR": "DAX", "GBRIDXGBP": "FTSE"}
rows = []
for instr in SPREAD:
    A = F.D[DM[instr]].atr
    for d in days:
        i = S.index.get_loc(d)
        if i + 1 >= len(S): continue
        n = S.index[i + 1]; a, b = bars(instr, d), bars(instr, n)
        if a is None or b is None: continue
        e_us = at(a, pd.Timestamp(f"{d.date()} 15:50", tz="America/New_York").tz_convert("UTC"))
        eo = at(b, pd.Timestamp(f"{n.date()} 08:05", tz="Europe/London").tz_convert("UTC")); ec = at(b, pd.Timestamp(f"{n.date()} 16:25", tz="Europe/London").tz_convert("UTC"))
        atr = A.asof(d)
        if not np.isfinite([e_us, eo, ec, atr]).all(): continue
        fund = 0.06 / 365 * 1.4 * e_us; c = SPREAD[instr]
        rows.append(dict(m=DM[instr], t=d, usclose_to_open=(eo - e_us - c - fund) / atr, usclose_to_close=(ec - e_us - c - fund) / atr,
                         open_to_close=(ec - eo - 1.2) / atr))
r = pd.DataFrame(rows)
if __name__ == "__main__":
    print(f"signal days {len(days)}, usable trades {len(r)}")
    for col in ["usclose_to_open", "usclose_to_close", "open_to_close"]:
        x = r[col]; tt = x.mean() / x.std() * np.sqrt(len(x)); y = r.groupby(r.t.dt.year)[col].sum()
        print(f"{col:17s} n{len(x)} mean {x.mean():+.3f} ATR t {tt:+.2f} yrs+ {(y>0).sum()}/{len(y)} last5y {x[r.t.dt.year>=2022].mean():+.3f} | "
              + " ".join(f"{m}:{g[col].mean():+.2f}" for m, g in r.groupby("m")))
        print("   by year:", " ".join(f"{k}:{v:+.1f}" for k, v in y.items()))
