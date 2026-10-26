"""How long should the crosses hold? (DK, 26 Oct: don't lock capital in very long trades; catch the meat of the move.)
5 years, 25 registered alts, 4-hour bars from data_15m. Death-cross short v1 signal; exits compared:
  trail3  - 3-ATR trail from the low, 30-day cap (registered)
  trail3 + cap 7d / 3d
  trail2  - tighter 2-ATR trail, 7-day cap
  fixed 7d / 3d - hold to the time cap, 3-ATR safety stop
Golden-cross v1 (BTC-gated) likewise: registered 3-day hold vs 7-day hold vs 3-ATR trail with 7-day cap.
Reported: mean per trade, t, win, average days held, capture = realised / max favourable move, and return per day held."""
import glob, os, numpy as np, pandas as pd
COST = 4.5/10000
UNIV = [os.path.basename(f)[:-4] for f in sorted(glob.glob("/home/claude/qlab/data_15m/*.csv"))]
def four(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    return d.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def ind(d):
    C, H, L = d.close.values, d.high.values, d.low.values
    pc = np.roll(C, 1); pc[0] = C[0]; tr = np.maximum(H-L, np.maximum(abs(H-pc), abs(L-pc))); a = pd.Series(tr).rolling(14).mean().bfill().values
    ef = pd.Series(C).ewm(span=20, adjust=False).mean().values; es = pd.Series(C).ewm(span=50, adjust=False).mean().values; e200 = pd.Series(C).ewm(span=200, adjust=False).mean().values
    return C, H, L, a, ef, es, e200
def death(C, a, ef, es):
    g = ef-es; out = []; armed = True
    for i in range(60, len(C)):
        if g[i] > 0 and g[i] < 0.25*a[i] and g[i] < g[i-1] < g[i-2] < g[i-3] and armed: out.append(i); armed = False
        if g[i] > 0.5*a[i] or g[i] < 0: armed = True
    return out
def golden(C, a, ef, es):
    out = []; up = np.where((ef-es > 0) & (np.roll(ef-es, 1) <= 0))[0]
    for i in up:
        if i < 60: continue
        for k in range(i+1, min(i+21, len(C))):
            if ef[k] < es[k]: break
            if C[k] > ef[k] > es[k] and ef[k]-es[k] > 0.5*a[k]: out.append(k); break
    return out
def exit_(C, H, L, a, i, side, mode, k, cap):
    e = C[i]; atr = a[i]; best = e; mfe = 0.0
    for j in range(i+1, min(i+cap+1, len(C))):
        fav = L[j] if side < 0 else H[j]; adv = H[j] if side < 0 else L[j]
        if mode == "trail":
            stop = (best + k*atr) if side < 0 else (best - k*atr)
        else:
            stop = e + side*(-k*atr)
        if (side < 0 and adv >= stop) or (side > 0 and adv <= stop):
            r = side*(stop/e - 1); return r - 2*COST, j-i, mfe
        best = min(best, fav) if side < 0 else max(best, fav); mfe = max(mfe, side*(best/e - 1))
    j = min(i+cap, len(C)-1); return side*(C[j]/e - 1) - 2*COST, j-i, mfe
btc = ind(four("/home/claude/qlab/data_15m/BTCUSD.csv")); btc_idx = four("/home/claude/qlab/data_15m/BTCUSD.csv").index
D = {"death": {}, "golden": {}}
SPECS = {"death": [("registered: 3-ATR trail, 30d cap", "trail", 3, 180), ("3-ATR trail, 7d cap", "trail", 3, 42), ("3-ATR trail, 3d cap", "trail", 3, 18),
                   ("2-ATR trail, 7d cap", "trail", 2, 42), ("fixed 7d, 3-ATR stop", "fixed", 3, 42), ("fixed 3d, 3-ATR stop", "fixed", 3, 18)],
         "golden": [("registered: fixed 3d, 3-ATR stop", "fixed", 3, 18), ("fixed 7d, 3-ATR stop", "fixed", 3, 42), ("3-ATR trail, 7d cap", "trail", 3, 42), ("2-ATR trail, 7d cap", "trail", 2, 42)]}
for s in UNIV:
    if s in ("BTCUSD", "ETHUSD"): continue
    d = four(f"/home/claude/qlab/data_15m/{s}.csv"); C, H, L, a, ef, es, e200 = ind(d)
    for i in death(C, a, ef, es):
        for nm, mode, k, cap in SPECS["death"]: D["death"].setdefault(nm, []).append((d.index[i], *exit_(C, H, L, a, i, -1, mode, k, cap)))
    for i in golden(C, a, ef, es):
        kb = btc_idx.searchsorted(d.index[i], side="right") - 1
        if kb < 0 or not btc[0][kb] > btc[6][kb]: continue
        for nm, mode, k, cap in SPECS["golden"]: D["golden"].setdefault(nm, []).append((d.index[i], *exit_(C, H, L, a, i, 1, mode, k, cap)))
for book in ("death", "golden"):
    print(f"\n== {book}-cross, 25 alts, 5 years")
    for nm, rows in D[book].items():
        r = pd.DataFrame(rows, columns=["t", "ret", "bars", "mfe"]).sort_values("t"); x = r.ret.values; h = len(x)//2
        days = r.bars.mean()/6; cap_ = (r.ret.clip(lower=0).sum() / r.mfe.sum())*100 if r.mfe.sum() > 0 else np.nan
        print(f"  {nm:34s} n {len(x):4d}  {x.mean()*100:+.2f}%/trade  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  win {100*(x>0).mean():.0f}%  "
              f"H1 {x[:h].mean()*100:+.2f} H2 {x[h:].mean()*100:+.2f}  held {days:.1f}d  per day held {x.mean()*100/max(days,0.17):+.3f}%  capture {cap_:.0f}%")
