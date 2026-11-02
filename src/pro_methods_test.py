"""Doc 176 — how professionals trade oil, gold and FX, tested as their authors describe them (rule 188). Pre-registered 2 Nov 2026
before any result. 5-min Dukascopy bars Nov 2025 - Oct 2026 (data_ign), split dev Nov-Apr / holdout May-Oct; daily trend on Yahoo
daily history 2006-2026, split dev 2006-2015 / holdout 2016-2026. IG costs: full spread per round trip (oil 3c, gold 0.3, EUR/USD 0.6 pip,
GBP/USD 0.9, USD/JPY 0.7), funding 0.018%/night on commodities, 0.009%/night on FX (doc 175 assumption).
1 EIA MOMENTUM (Adelaide paper): on Wednesdays (EIA crude inventory, 10:30 NY), sign of the 10:30-11:00 NY return; trade WTI in that
  direction 14:00-14:30 NY (last half-hour before settlement). Control: the same rule on Mon/Tue/Thu/Fri (no release).
2 EIA FADE (J. Energy Markets: the reaction lasts ~25 min then reverts): doc 156's news fade (paperbook13.fade) on WTI at Wed 10:30 NY.
  Control: the same rule at 10:30 NY on non-release weekdays.
3 GOLD OVERNIGHT: long 16:00 NY close -> 09:30 NY next open (Friday -> Monday pays three nights); against the 09:30-16:00 day half.
4 LONDON-OPEN BREAKOUT of the Asian range (FX practitioner standard): range 00:00-07:00 London; 07:00-11:00 London first break of the
  high/low by 10% of the range enters in that direction; stop the other side of the range; target 1x range; exit 16:00 London;
  one trade a day; skip days whose range is above the 80th percentile of the prior 60 days. EUR/USD, GBP/USD, USD/JPY, gold.
  Control: same day, same entry time, random direction, same stop/target.
5 DAILY TREND (turtle system 2 / CTA standard): 55-day high/low breakout entry, 20-day opposite exit, 2-ATR(20) stop; long and short.
  Gold (GC=F), WTI (CL=F), EUR/USD, GBP/USD, USD/JPY (=X). Scored in R (risk = 2 ATR) after spread and nightly funding on notional.
  Control: random entry day, same direction and holding time."""
import sys, os, json, urllib.request, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
from paperbook13 import fade
OUT = open("runs/pro_methods_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
RNG = np.random.default_rng(176); SPLIT = pd.Timestamp("2026-05-01", tz="UTC"); NY, LDN = "America/New_York", "Europe/London"
def load(i):
    d = pd.read_csv(f"data_ign/{i}_5m.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[~d.index.duplicated()].sort_index()
def summ(lab, df, ctl=None, unit="R", split=SPLIT):
    cells = []
    for seg, m in (("dev", df.t < split), ("hold", df.t >= split)):
        x = df[m].r
        if len(x) < 5: cells.append(f"{seg} n{len(x)}"); continue
        tt = x.mean() / (x.std() / np.sqrt(len(x))) if x.std() > 0 else 0
        c = ""
        if ctl is not None:
            y = ctl[(ctl.t < split) if seg == "dev" else (ctl.t >= split)].r; c = f" | control {y.mean():+.3f}{unit} (n{len(y)})"
        cells.append(f"{seg} n{len(x):3} {x.mean():+.3f}{unit} (t {tt:+.1f}) win {100*(x>0).mean():.0f}%{c}")
    log(f"  {lab:34} " + " || ".join(cells))

# ---------- 1 and 2: oil on EIA day ----------
log("1-2 OIL ON EIA DAY (WTI, Wednesday 10:30 NY release)")
oil = load("LIGHTCMDUSD"); ny = oil.index.tz_convert(NY); oil["d"] = ny.normalize().tz_localize(None); oil["m"] = ny.hour * 60 + ny.minute; oil["wd"] = ny.weekday
SP = 0.03
def px_at(g, mm):
    x = g[g.m < mm]; return float(x.close.iloc[-1]) if len(x) else np.nan
mom, momc, fd, fdc = [], [], [], []
for day, g in oil.groupby("d"):
    if g.wd.iloc[0] > 4 or len(g[(g.m >= 600) & (g.m < 870)]) < 50: continue
    p1030, p1100, p1400, p1430 = px_at(g, 630), px_at(g, 660), px_at(g, 840), px_at(g, 870)
    if np.isnan([p1030, p1100, p1400, p1430]).any() or p1100 == p1030: continue
    s = np.sign(p1100 - p1030); r = (s * (p1430 - p1400) - SP) / p1400 * 100; T = g.index[g.m >= 630][0]
    (mom if g.wd.iloc[0] == 2 else momc).append((T, r))
    f = fade(oil[["open", "high", "low", "close"]], T, cost=SP / 2)
    if f: (fd if g.wd.iloc[0] == 2 else fdc).append((T, f[0]))
D = lambda L: pd.DataFrame(L, columns=["t", "r"])
summ("1 EIA momentum (% per trade, net)", D(mom), D(momc), "%")
summ("2 EIA fade (R per trade, net)", D(fd), D(fdc), "R")

# ---------- 3: gold overnight ----------
log("\n3 GOLD OVERNIGHT (long 16:00 NY -> 09:30 NY, % net of spread and funding) vs DAY HALF")
g = load("XAUUSD"); ny = g.index.tz_convert(NY); g["d"] = ny.normalize().tz_localize(None); g["m"] = ny.hour * 60 + ny.minute
days = sorted(g.d.unique()); on, dy = [], []
for k in range(len(days) - 1):
    a = g[g.d == days[k]]; b = g[g.d == days[k + 1]]
    c = a[a.m < 960]; o = b[b.m >= 570]
    if len(c) < 50 or not len(o): continue
    pc, po = float(c.close.iloc[-1]), float(o.open.iloc[0]); nights = max(1, (days[k + 1] - days[k]).days)
    on.append((c.index[-1], (po / pc - 1 - 0.3 / pc - nights * 0.00018) * 100))
    ses = a[(a.m >= 570) & (a.m < 960)]
    if len(ses) > 50: dy.append((ses.index[0], (float(ses.close.iloc[-1]) / float(ses.open.iloc[0]) - 1 - 0.3 / pc) * 100))
summ("gold overnight", D(on), D(dy), "%")
log("  (control column = the 09:30-16:00 day half, same costs)")

# ---------- 4: London-open breakout ----------
log("\n4 LONDON-OPEN BREAKOUT OF THE ASIAN RANGE (R per trade, net; control = random direction, same entry and stop/target)")
for inst, sp in (("EURUSD", 0.00006), ("GBPUSD", 0.00009), ("USDJPY", 0.007), ("XAUUSD", 0.3)):
    d = load(inst); lt = d.index.tz_convert(LDN); d["d"] = lt.normalize().tz_localize(None); d["m"] = lt.hour * 60 + lt.minute
    rows, ctl, widths = [], [], []
    for day, x in d.groupby("d"):
        if x.index[0].tz_convert(LDN).weekday() > 4: continue
        asia = x[x.m < 420]; ses = x[(x.m >= 420) & (x.m < 960)]
        if len(asia) < 60 or len(ses) < 90: continue
        hi, lo = asia.high.max(), asia.low.min(); w = hi - lo; prior = widths[-60:]; widths.append(w)
        if len(prior) < 20 or w > np.percentile(prior, 80) or w <= 0: continue
        bu, bd = hi + 0.1 * w, lo - 0.1 * w; H, L, C, m, ix = ses.high.values, ses.low.values, ses.close.values, ses.m.values, ses.index
        j = None
        for k in range(len(H)):
            if m[k] >= 660: break
            if H[k] >= bu: j, s, e = k, 1, bu; break
            if L[k] <= bd: j, s, e = k, -1, bd; break
        if j is None: continue
        def run(side, e, k0):
            stop = lo if side == 1 else hi; risk = abs(e - stop); tgt = e + side * w
            for k in range(k0 + (0 if side == s else 1), len(H)):
                if (side == 1 and L[k] <= stop) or (side == -1 and H[k] >= stop): return (stop - e) * side, risk
                if (side == 1 and H[k] >= tgt) or (side == -1 and L[k] <= tgt): return (tgt - e) * side, risk
            return (C[-1] - e) * side, risk
        pts, risk = run(s, e, j); rows.append((ix[j], (pts - sp) / risk))
        rs = int(RNG.choice([1, -1])); e2 = C[j]; stop = lo if rs == 1 else hi
        if (e2 - stop) * rs > 0:
            pts2, r2 = run(rs, e2, j); ctl.append((ix[j], (pts2 - sp) / r2))
    summ(f"{inst}", D(rows), D(ctl), "R")

# ---------- 5: daily trend ----------
log("\n5 DAILY TREND (55-day breakout, 20-day exit, 2-ATR stop; R per trade net of spread and funding; Yahoo daily 2006-2026)")
def ymax(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=1136073600&period2=1793000000&interval=1d"
    j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
    r = j["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    d = pd.DataFrame({"high": q["high"], "low": q["low"], "close": q["close"]}, index=pd.to_datetime(r["timestamp"], unit="s", utc=True)).dropna()
    return d[(d.high >= d.low) & (d.close > 0)]
TS = pd.Timestamp("2016-01-01", tz="UTC"); allR = []
for name, sym, sp, fund in (("Gold", "GC=F", 0.3, 0.00018), ("Oil (WTI)", "CL=F", 0.03, 0.00018), ("EUR/USD", "EURUSD=X", 0.00006, 0.00009),
                            ("GBP/USD", "GBPUSD=X", 0.00009, 0.00009), ("USD/JPY", "JPY=X", 0.007, 0.00009)):
    try: d = ymax(sym)
    except Exception as ex: log(f"  {name}: no data ({ex})"); continue
    H, L, C, ix = d.high.values, d.low.values, d.close.values, d.index
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(20).mean().values
    hi55 = pd.Series(H).rolling(55).max().shift(1).values; lo55 = pd.Series(L).rolling(55).min().shift(1).values
    hi20 = pd.Series(H).rolling(20).max().shift(1).values; lo20 = pd.Series(L).rolling(20).min().shift(1).values
    rows, ctl = [], []; k = 60
    while k < len(C) - 1:
        s = 1 if C[k] > hi55[k] else (-1 if C[k] < lo55[k] else 0)
        if s == 0 or np.isnan(atr[k]): k += 1; continue
        e = C[k]; stop = e - s * 2 * atr[k]; risk = 2 * atr[k]; x = len(C) - 1; px = C[-1]
        for q in range(k + 1, len(C)):
            if (s == 1 and L[q] <= stop) or (s == -1 and H[q] >= stop): x, px = q, stop; break
            if (s == 1 and C[q] < lo20[q]) or (s == -1 and C[q] > hi20[q]): x, px = q, C[q]; break
        nights = (ix[x] - ix[k]).days
        rows.append((ix[k], ((px - e) * s - sp - nights * fund * e) / risk))
        for _ in range(5):
            j = int(RNG.integers(60, len(C) - 1 - max(1, x - k)))
            if np.isnan(atr[j]): continue
            j2 = j + (x - k); e2 = C[j]; st2 = e2 - s * 2 * atr[j]; px2 = C[j2]
            for q in range(j + 1, j2 + 1):
                if (s == 1 and L[q] <= st2) or (s == -1 and H[q] >= st2): px2 = st2; break
            ctl.append((ix[j], ((px2 - e2) * s - sp - (ix[j2] - ix[j]).days * fund * e2) / (2 * atr[j])))
        k = x + 1
    df = D(rows); allR.append(df.assign(m=name))
    summ(f"{name} ({len(df)/20:.1f} trades/yr)", df, D(ctl), "R", TS)
A = pd.concat(allR)
summ("ALL FIVE pooled", A, None, "R", TS)
log("done")
