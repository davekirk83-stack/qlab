"""DK 21 Nov: (1) L2WTrades' "6AM candle" rule; (2) @XAUUSD_oyazi EMA contraction (30m/1h) -> enter on the move out.
NQ 5m (Oct 2025-Nov 2026), US 500 5m (Nov 2025-Nov 2026), gold 5m (Apr-Oct 2026). Costs: NQ 2 pts, US500 0.5, gold 0.4 per round trip."""
import numpy as np, pandas as pd
SRC = {"NQ": ("data_nq_cache/nq_5m.csv", 2.0), "US500": ("data_ig_cache/USA500IDXUSD_5m.csv", 0.5), "GOLD": ("data_ig_cache/XAUUSD_5m.csv", 0.4)}
def load(m):
    d = pd.read_csv(SRC[m][0], parse_dates=["ts"]).set_index("ts")[["open","high","low","close"]]
    d.index = d.index.tz_convert("America/New_York"); return d
out = []
# ---------- 1. 6AM candle ----------
for m in ("NQ", "US500"):
    d = load(m); cost = SRC[m][1]; mm = d.index.hour*60 + d.index.minute; day = d.index.date
    rth = d[(mm >= 570) & (mm < 960)]; R = rth.groupby(rth.index.date).agg(o=("open","first"), h=("high","max"), l=("low","min"), c=("close","last"), n=("open","size"))
    R = R[R.n >= 60]; R["ph"], R["pl"] = R.h.shift(1), R.l.shift(1); R["rng"] = (R.h - R.l).rolling(10).mean().shift(1)
    six = d[(mm >= 360) & (mm < 420)]; S6 = six.groupby(six.index.date).agg(h=("high","max"), l=("low","min"), c=("close","last"))
    rows = []
    for dd, r in R.dropna().iterrows():
        if dd not in S6.index: continue
        s = S6.loc[dd]
        if s.h > r.ph and s.c < r.ph: kind, side = "sweep high, close back in -> short", -1
        elif s.l < r.pl and s.c > r.pl: kind, side = "sweep low, close back in -> long", 1
        elif s.c > r.ph: kind, side = "close above high -> long", 1
        elif s.c < r.pl: kind, side = "close below low -> short", -1
        else: kind, side = "inside -> no signal", 0
        pts = side*(r.c - r.o) - (cost if side else 0)
        rows.append(dict(day=dd, kind=kind, side=side, pts=pts, R=pts/r.rng if side else np.nan, right=float(np.sign(r.c-r.o)==side) if side else np.nan))
    X = pd.DataFrame(rows); out.append(f"== 6AM candle, {m}: {len(X)} days, trade 09:30 open -> 16:00 close")
    for k, g in X.groupby("kind"):
        out.append(f"  {k:38} n{len(g):3} ({len(g)/len(X):.0%} of days) | direction right {g.right.mean():.0%} | mean {g.pts.mean():+.1f} pts ({g.R.mean():+.3f} x avg range)")
    t = X[X.side != 0]; half = len(t)//2
    out.append(f"  ALL signals: n{len(t)} right {t.right.mean():.0%}, mean {t.pts.mean():+.1f} pts, total {t.pts.sum():+.0f} pts, halves {t.pts.iloc[:half].mean():+.1f} / {t.pts.iloc[half:].mean():+.1f}")
    l14 = t[pd.to_datetime(t.day) >= pd.Timestamp("2026-10-15")]
    out.append(f"  last month ({len(l14)} signals): right {l14.right.mean():.0%}  (claim: 14 of 15)")
# ---------- 2. EMA contraction ----------
def ema_contraction(m, tf):
    d = load(m).resample(tf).agg(dict(open="first", high="max", low="min", close="last")).dropna(); cost = SRC[m][1]
    c = d.close; E = pd.concat([c.ewm(span=s, adjust=False).mean() for s in (20, 50, 100, 200)], axis=1)
    tr = np.maximum(d.high-d.low, np.maximum((d.high-c.shift()).abs(), (d.low-c.shift()).abs())); A = tr.rolling(14).mean()
    spread = (E.max(axis=1) - E.min(axis=1)) / A; tight = spread < spread.rolling(500, min_periods=200).quantile(0.2)
    was = tight.rolling(6).max().astype(bool)
    up = was & (c > E.max(axis=1)) & (c.shift() <= E.max(axis=1).shift()); dn = was & (c < E.min(axis=1)) & (c.shift() >= E.min(axis=1).shift())
    H, L, C, a = d.high.values, d.low.values, c.values, A.values; res = []; nxt = 0
    for i in np.where((up | dn).values)[0]:
        if i < nxt or i < 220: continue
        side = 1 if up.iloc[i] else -1; st = C[i] - side*1.5*a[i]; tg = C[i] + side*3*a[i]; r = None
        for j in range(i+1, min(i+49, len(C))):
            if (side>0 and L[j]<=st) or (side<0 and H[j]>=st): r = -1.5*a[i]; break
            if (side>0 and H[j]>=tg) or (side<0 and L[j]<=tg): r = 3*a[i]; break
        if r is None: j = min(i+48, len(C)-1); r = side*(C[j]-C[i])
        res.append((r - cost)/a[i]); nxt = j
    # control: random entries, same exits
    rng = np.random.default_rng(2); ctl = []
    for i in rng.integers(220, len(C)-50, 800):
        side = rng.choice([1,-1]); st = C[i]-side*1.5*a[i]; tg = C[i]+side*3*a[i]; r=None
        for j in range(i+1, i+49):
            if (side>0 and L[j]<=st) or (side<0 and H[j]>=st): r=-1.5*a[i]; break
            if (side>0 and H[j]>=tg) or (side<0 and L[j]<=tg): r=3*a[i]; break
        if r is None: r = side*(C[i+48]-C[i])
        ctl.append((r-cost)/a[i])
    res = np.array(res); half = len(res)//2
    return f"  {m:5} {tf:4}: n{len(res):3} mean {res.mean():+.3f} ATR win {(res>0).mean():.0%} | halves {res[:half].mean():+.3f} / {res[half:].mean():+.3f} | random {np.mean(ctl):+.3f}"
out.append("== EMA contraction (EMA 20/50/100/200 spread in bottom 20% -> trade the close out of the bunch; stop 1.5 ATR, target 3 ATR, max 48 bars)")
for m in ("GOLD", "NQ", "US500"):
    for tf in ("30min", "1h"): out.append(ema_contraction(m, tf))
open("runs/research/sixam_and_ema.txt","w").write("\n".join(out)); print("\n".join(out))
