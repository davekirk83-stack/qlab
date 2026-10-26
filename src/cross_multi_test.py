"""Death-cross short v1 and Golden-cross long v1 (docs 82/83) on non-crypto markets, 4-hour bars from the 5-min caches (Apr-Oct 2026),
plus the 20-year daily ETFs. Same rules: death = EMA20>EMA50, gap<0.25 ATR14, shrinking 3 bars, short, 3-ATR trail from the low, 180-bar cap;
golden = 20/50 cross then within 20 bars ribbon >0.5 ATR and close>EMA20, long, hold 18 bars, 3-ATR safety stop (gate: the instrument's
own EMA200, since BTC is irrelevant here). Control: random entries with the same exit. Costs: IG half-spread each way (indices/FX), 0.04% ETFs."""
import glob, os, numpy as np, pandas as pd
rng = np.random.default_rng(3)
def ind(d):
    C, H, L = d.close.values, d.high.values, d.low.values
    pc = np.roll(C, 1); pc[0] = C[0]; tr = np.maximum(H-L, np.maximum(abs(H-pc), abs(L-pc))); a = pd.Series(tr).rolling(14).mean().values
    e20 = pd.Series(C).ewm(span=20, adjust=False).mean().values; e50 = pd.Series(C).ewm(span=50, adjust=False).mean().values; e200 = pd.Series(C).ewm(span=200, adjust=False).mean().values
    return C, H, L, a, e20, e50, e200
def death_sigs(C, a, e20, e50):
    g = e20 - e50; out = []; armed = True
    for i in range(53, len(C)):
        q = g[i] > 0 and g[i] < 0.25*a[i] and g[i] < g[i-1] < g[i-2] < g[i-3]
        if q and armed: out.append(i); armed = False
        if g[i] > 0.5*a[i] or g[i] < 0: armed = True
    return out
def golden_sigs(C, a, e20, e50, e200):
    out = []; last_cross = -999
    for i in range(201, len(C)):
        if e20[i] > e50[i] and e20[i-1] <= e50[i-1]: last_cross = i
        if 0 < i - last_cross <= 20 and e20[i] - e50[i] > 0.5*a[i] and C[i] > e20[i] and C[i] > e200[i]:
            out.append(i); last_cross = -999
    return out
def trail_short(C, H, L, a, i, cap=180):
    e = C[i]; low = e; atr = a[i]
    for j in range(i+1, min(i+cap+1, len(C))):
        if H[j] >= low + 3*atr: return e/(low + 3*atr) - 1
        low = min(low, L[j])
    return e/C[min(i+cap, len(C)-1)] - 1
def hold_long(C, H, L, a, i, n=18):
    e = C[i]; stop = e - 3*a[i]
    for j in range(i+1, min(i+n+1, len(C))):
        if L[j] <= stop: return stop/e - 1
    return C[min(i+n, len(C)-1)]/e - 1
def run(name, d, cost):
    C, H, L, a, e20, e50, e200 = ind(d); res = {}
    for kind, sigs, fn in (("death", death_sigs(C, a, e20, e50), trail_short), ("golden", golden_sigs(C, a, e20, e50, e200), hold_long)):
        r = [fn(C, H, L, a, i) - 2*cost for i in sigs]
        ctrl = [fn(C, H, L, a, int(j)) - 2*cost for j in rng.integers(200, len(C)-20, size=max(len(sigs)*5, 1))]
        res[kind] = (len(r), np.mean(r)*100 if r else np.nan, np.mean(ctrl)*100)
    return res
rows = []
four = lambda d: pd.DataFrame({"open": d.open.resample("4h").first(), "high": d.high.resample("4h").max(), "low": d.low.resample("4h").min(), "close": d.close.resample("4h").last()}).dropna()
caches = {"Wall St": ("data_ig_cache/USA30IDXUSD_5m.csv", 1.0/52900), "Germany 40": ("data_ig_cache/DEUIDXEUR_5m.csv", 0.6/25400), "US Tech 100": ("data_nq_cache/nq_5m.csv", 0.5/29000),
          "Gold": ("data_ig_cache/XAUUSD_5m.csv", 0.15/4000), "EUR/USD": ("data_ig_cache/EURUSD_5m.csv", 0.00003/1.12), "GBP/USD": ("data_ig_cache/GBPUSD_5m.csv", 0.000045/1.34),
          "USD/CAD": ("data_ig_cache/USDCAD_5m.csv", 0.000085/1.40), "USD/CHF": ("data_ig_cache/USDCHF_5m.csv", 0.000075/0.82), "WTI": ("data_ig_cache/LIGHTCMDUSD_5m.csv", 0.014/95), "Copper": ("data_ig_cache/COPPERCMDUSD_5m.csv", 0.015/65)}
print("4-hour bars, Apr-Oct 2026 (n / mean per trade % / random control %)")
for nm, (f, c) in caches.items():
    if not os.path.exists(f): continue
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = four(d[d.index >= "2026-04-15"]); r = run(nm, d, c)
    print(f"  {nm:12s} death {r['death'][0]:2d} {r['death'][1]:+.2f}% (ctrl {r['death'][2]:+.2f})   golden {r['golden'][0]:2d} {r['golden'][1]:+.2f}% (ctrl {r['golden'][2]:+.2f})")
print("\nDaily bars, 20-year ETFs (equity indices and sectors, metals, energy, bonds)")
tot = {"death": [], "golden": [], "cd": [], "cg": []}
for f in sorted(glob.glob("data_etf20/*.csv")):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    if len(d) < 800: continue
    C, H, L, a, e20, e50, e200 = ind(d)
    for i in death_sigs(C, a, e20, e50): tot["death"].append(trail_short(C, H, L, a, i) - 0.0008)
    for i in golden_sigs(C, a, e20, e50, e200): tot["golden"].append(hold_long(C, H, L, a, i) - 0.0008)
    for j in rng.integers(200, len(C)-20, size=40): tot["cd"].append(trail_short(C, H, L, a, int(j)) - 0.0008); tot["cg"].append(hold_long(C, H, L, a, int(j)) - 0.0008)
for k, c in (("death", "cd"), ("golden", "cg")):
    x = np.array(tot[k]); h = len(x)//2
    print(f"  {k:6s} n {len(x)}  {x.mean()*100:+.2f}%/trade  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  win {100*(x>0).mean():.0f}%  | control {np.mean(tot[c])*100:+.2f}%")
