"""Doc 161 — traderdiegox "Key Intraday Levels" levels tested on BTC before adding any to V21 (DK 29 Oct: "If you think it adds something
useful to it overall, then yes"). Pre-registered. Data: Coinbase BTC 15m, Oct 2021 - Oct 2026. Days are UTC (crypto daily candle), weeks Mon-Sun.
Levels: PDH/PDL (previous day high/low), PWH/PWL (previous week), MO (New York midnight open).
Questions:
 1 TAKEN: how often each level is traded through in the current day/week, and which side first given where the day opens.
 2 REACTION at the first touch: share of first touches where price is back on the approach side 4 hours later (rejection), vs a PLACEBO —
   a random level inside the same day's eventual range, first touched from the same side (100 draws per touch).
 3 MAGNET (midnight open): when price is >0.5% away from MO at the NY 9:30 open, how often does it trade back to MO by 16:00, vs a placebo
   level at the same distance on the far side.
A level earns a place on the chart only if it beats its placebo."""
import numpy as np, pandas as pd, paperbook2 as PB
d = PB._load("BTCUSD")[["open", "high", "low", "close"]]; d = d[d.index >= "2021-10-20"]
rng = np.random.default_rng(7)
day = d.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
wk = d.resample("W-SUN").agg({"high": "max", "low": "min"}).dropna()
def first_touch(bars, level, from_below):
    hit = bars.high.values >= level if from_below else bars.low.values <= level
    k = np.flatnonzero(hit); return None if not len(k) else k[0]
def reaction(bars, k, level, from_below):
    t = bars.index[k] + pd.Timedelta(hours=4); later = d[d.index <= t]
    if later.index[-1] < t - pd.Timedelta(minutes=30): return None
    c = later.close.iloc[-1]; return (c < level) if from_below else (c > level)
out = []
# --- daily levels
rows = []
for i in range(1, len(day)):
    t0, t1 = day.index[i], day.index[i] + pd.Timedelta(days=1)
    bars = d[(d.index >= t0) & (d.index < t1)]
    if len(bars) < 80: continue
    pdh, pdl, o = day.high.iloc[i - 1], day.low.iloc[i - 1], bars.open.iloc[0]
    pos = (o - pdl) / (pdh - pdl) if pdh > pdl else .5
    kh = first_touch(bars, pdh, True) if o < pdh else None; kl = first_touch(bars, pdl, False) if o > pdl else None
    r = dict(pos=pos, H=kh is not None, L=kl is not None, first=("H" if kh is not None and (kl is None or kh < kl) else "L" if kl is not None else "-"))
    for nm, k, lv, fb in (("H", kh, pdh, True), ("L", kl, pdl, False)):
        if k is None: continue
        rej = reaction(bars, k, lv, fb)
        if rej is None: continue
        r[f"rej{nm}"] = rej
        # placebo: random level within the day's eventual range on the same side of the open, first touched from the same side
        lo, hi = (o, bars.high.max()) if fb else (bars.low.min(), o)
        pr = []
        for _ in range(100):
            pl = rng.uniform(lo, hi); kk = first_touch(bars, pl, fb)
            if kk is not None:
                x = reaction(bars, kk, pl, fb)
                if x is not None: pr.append(x)
        r[f"pl{nm}"] = np.mean(pr) if pr else np.nan
    rows.append(r)
R = pd.DataFrame(rows)
out.append(f"DAILY ({len(R)} days): PDH taken {100*R.H.mean():.0f}%, PDL taken {100*R.L.mean():.0f}%, both {100*(R.H&R.L).mean():.0f}%, neither {100*(~R.H&~R.L).mean():.0f}%")
for lab, m in (("open in bottom third", R.pos < 1/3), ("middle", (R.pos >= 1/3) & (R.pos <= 2/3)), ("top third", R.pos > 2/3), ("opens outside range", (R.pos < 0) | (R.pos > 1))):
    s = R[m]; out.append(f"   {lab:22} n{len(s):4}: PDH {100*s.H.mean():.0f}% PDL {100*s.L.mean():.0f}% | first: H {100*(s['first']=='H').mean():.0f}% L {100*(s['first']=='L').mean():.0f}%")
for nm in ("H", "L"):
    a = R[f"rej{nm}"].dropna().astype(float); b = R[f"pl{nm}"].dropna()
    out.append(f"   first touch of PD{nm}: back on the approach side 4h later {100*a.mean():.0f}% (n{len(a)}) vs placebo level {100*b.mean():.0f}%")
# --- weekly levels
wrows = []
for i in range(1, len(wk)):
    t1 = wk.index[i] + pd.Timedelta(days=1); t0 = t1 - pd.Timedelta(days=7)
    bars = d[(d.index >= t0) & (d.index < t1)]
    if len(bars) < 500: continue
    o = bars.open.iloc[0]; pwh, pwl = wk.high.iloc[i - 1], wk.low.iloc[i - 1]
    r = {"H": bars.high.max() > pwh, "L": bars.low.min() < pwl}
    for nm, lv, fb in (("H", pwh, True), ("L", pwl, False)):
        if (fb and o >= lv) or (not fb and o <= lv): continue
        k = first_touch(bars, lv, fb)
        if k is None: continue
        rej = reaction(bars, k, lv, fb)
        if rej is None: continue
        lo, hi = (o, bars.high.max()) if fb else (bars.low.min(), o); pr = []
        for _ in range(100):
            pl = rng.uniform(lo, hi); kk = first_touch(bars, pl, fb)
            if kk is not None:
                x = reaction(bars, kk, pl, fb)
                if x is not None: pr.append(x)
        r[f"rej{nm}"] = rej; r[f"pl{nm}"] = np.mean(pr) if pr else np.nan
    wrows.append(r)
W = pd.DataFrame(wrows)
out.append(f"WEEKLY ({len(W)} weeks): PWH taken {100*W.H.mean():.0f}%, PWL taken {100*W.L.mean():.0f}%, both {100*(W.H&W.L).mean():.0f}%")
for nm in ("H", "L"):
    a = W[f"rej{nm}"].dropna().astype(float); b = W[f"pl{nm}"].dropna()
    out.append(f"   first touch of PW{nm}: back on the approach side 4h later {100*a.mean():.0f}% (n{len(a)}) vs placebo {100*b.mean():.0f}%")
# --- midnight open magnet
mm = []
for dd in pd.date_range("2021-11-01", d.index[-1].tz_convert(None).normalize(), freq="D"):
    if dd.weekday() >= 5: continue
    mo_t = pd.Timestamp(dd.strftime("%Y-%m-%d") + " 00:00", tz="America/New_York").tz_convert("UTC")
    op_t = pd.Timestamp(dd.strftime("%Y-%m-%d") + " 09:30", tz="America/New_York").tz_convert("UTC")
    cl_t = pd.Timestamp(dd.strftime("%Y-%m-%d") + " 16:00", tz="America/New_York").tz_convert("UTC")
    a = d[(d.index >= mo_t)]
    if not len(a) or a.index[0] != mo_t: continue
    mo = a.open.iloc[0]; s = d[(d.index >= op_t) & (d.index < cl_t)]
    if len(s) < 20: continue
    p = s.open.iloc[0]; dist = (p - mo) / p
    if abs(dist) < 0.005: continue
    back = s.low.min() <= mo if dist > 0 else s.high.max() >= mo
    plac = p + (p - mo); away = s.high.max() >= plac if dist > 0 else s.low.min() <= plac
    mm.append((back, away))
M = np.array(mm)
out.append(f"MIDNIGHT OPEN ({len(M)} NY sessions opening >0.5% away): traded back to MO by 16:00 {100*M[:,0].mean():.0f}% vs placebo same distance the other way {100*M[:,1].mean():.0f}%")
txt = "\n".join(out); print(txt); open("/home/claude/qlab/runs/key_levels_test.txt", "w").write(txt + "\n")
