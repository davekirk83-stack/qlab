"""Doc 180 — stops at structure as a magnet (the untested leg of doc 60; DK 4 Nov 2026 "Yes please").
Pre-registered 4 Nov 2026 before any result.
Data: Coinbase hourly BTC, ETH, SOL, Nov 2023 - Nov 2026. Split dev = first half, holdout = second half.
LEVELS (all causal - known at the time they are used, and 'untaken': dropped once price trades through them):
  swing   confirmed pivot high/low (highest high / lowest low of a +-12-bar window), usable 12 bars after the pivot
  day     prior UTC day's high and low
  week    prior ISO week's high and low
  (round numbers are NOT used in this run - always present, so they need their own design; noted before results)
A RACE: every 4 hours, nearest untaken structural level above vs below (swing/day/week; both 0.3%-6% away). Which is touched first
  within 7 days? Null = distance-implied p(up) = d_dn / (d_up + d_dn). Excess = actual - null. Also split by which side is
  'heavier' (more untaken levels within 0.5% of the nearest one) and by level type.
B SWEEP-AND-REVERSE (the tradable version, doc 60's best prior): first touch of an untaken structural level. Outcome: close of the
  touch bar back on the near side, and the return over the next 12 bars measured from the level in the reversal direction.
  Control: the same statistics at pseudo-levels = each real level shifted by a random +-0.5-2% (same market, same era).
Verdict needs the effect in both halves and on at least 2 of 3 coins."""
import json, os, time, urllib.request, numpy as np, pandas as pd
OUT_DIR = "/home/claude/qlab/runs"; os.makedirs(OUT_DIR, exist_ok=True)
OUT = open(f"{OUT_DIR}/stops_at_structure_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
RNG = np.random.default_rng(180); CACHE = "/home/claude/qlab/data_cb_hourly"; os.makedirs(CACHE, exist_ok=True)
def hourly(p):
    f = f"{CACHE}/{p}.csv"
    if os.path.exists(f) and time.time() - os.path.getmtime(f) < 6 * 3600:
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d
    rows = []; end = pd.Timestamp.now("UTC").floor("h")
    while end > pd.Timestamp("2023-11-01", tz="UTC"):
        st = end - pd.Timedelta(hours=300)
        u = f"https://api.exchange.coinbase.com/products/{p}/candles?granularity=3600&start={st.isoformat()}&end={end.isoformat()}"
        for _ in range(3):
            try: rows += json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "qlab"}), timeout=30)); break
            except Exception: time.sleep(2)
        end = st; time.sleep(0.15)
    d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "v"]).drop_duplicates("t")
    d.index = pd.to_datetime(d.t, unit="s", utc=True); d = d.sort_index()[["open", "high", "low", "close"]]
    d = d[d.index >= "2023-11-01"]; d.to_csv(f); return d
STEP = {"BTC-USD": 1000, "ETH-USD": 50, "SOL-USD": 5}; W = 12

def levels_timeline(d):
    """Yield, for every bar i, the untaken structural levels known at the open of bar i: list of (price, type)."""
    H, L = d.high.values, d.low.values; n = len(d); ix = d.index
    piv_h = {i + W: (H[i], "swing") for i in range(W, n - W) if H[i] == H[i - W:i + W + 1].max()}
    piv_l = {i + W: (L[i], "swing") for i in range(W, n - W) if L[i] == L[i - W:i + W + 1].min()}
    day = ix.normalize(); wk = ix.to_period("W")
    dH = d.high.groupby(day).max(); dL = d.low.groupby(day).min(); wH = d.high.groupby(wk).max(); wL = d.low.groupby(wk).min()
    above, below = [], []           # untaken levels: above = resistance (stops of shorts), below = support (stops of longs)
    for i in range(n):
        new = []
        if i in piv_h: new.append(("h",) + piv_h[i])
        if i in piv_l: new.append(("l",) + piv_l[i])
        if i == 0 or day[i] != day[i - 1]:
            pd_ = day[i] - pd.Timedelta(days=1)
            if pd_ in dH.index: new += [("h", dH[pd_], "day"), ("l", dL[pd_], "day")]
        if i == 0 or wk[i] != wk[i - 1]:
            pw = wk[i] - 1
            if pw in wH.index: new += [("h", wH[pw], "week"), ("l", wL[pw], "week")]
        px = d.open.values[i]
        for side, lv, ty in new:          # a level sits above or below where price is now
            (above if lv > px else below).append((lv, ty))
        yield i, above, below
        # remove levels traded through during bar i
        above[:] = [x for x in above if x[0] > H[i]]; below[:] = [x for x in below if x[0] < L[i]]

def run(p):
    d = hourly(p); H, L, C, O = d.high.values, d.low.values, d.close.values, d.open.values; ix = d.index; n = len(d)
    mid = ix[n // 2]; race, touch = [], []
    snap = {}
    for i, ab, be in levels_timeline(d):
        if i % 4 == 0 and i + 168 < n: snap[i] = (list(ab), list(be))
        # B: touches during bar i of levels known at its open
        for lv, ty in ab:
            if H[i] >= lv and O[i] < lv and i + 13 < n: touch.append((ix[i], "above", ty, lv, C[i] < lv, (lv - C[i + 12]) / lv))
        for lv, ty in be:
            if L[i] <= lv and O[i] > lv and i + 13 < n: touch.append((ix[i], "below", ty, lv, C[i] > lv, (C[i + 12] - lv) / lv))
    # A: races
    for i, (ab, be) in snap.items():
        px = C[i - 1] if i else O[i]
        ab = [x for x in ab if 0.003 <= x[0] / px - 1 <= 0.06]; be = [x for x in be if 0.003 <= 1 - x[0] / px <= 0.06]
        if not ab or not be: continue
        up = min(ab, key=lambda x: x[0]); dn = max(be, key=lambda x: x[0])
        du, dd = up[0] / px - 1, 1 - dn[0] / px
        heavy_up = sum(1 for x in ab if x[0] <= up[0] * 1.005); heavy_dn = sum(1 for x in be if x[0] >= dn[0] * 0.995)
        res = None
        for k in range(i, i + 168):
            hu, hd = H[k] >= up[0], L[k] <= dn[0]
            if hu and hd: res = None; break
            if hu: res = 1; break
            if hd: res = 0; break
        if res is None: continue
        race.append((ix[i], res, dd / (du + dd), heavy_up - heavy_dn, up[1], dn[1]))
    R = pd.DataFrame(race, columns=["t", "up", "null", "heavy", "tu", "td"]); T = pd.DataFrame(touch, columns=["t", "side", "ty", "lv", "rev", "ret"])
    # control touches: pseudo-levels = real untaken levels shifted by random +-0.5-2%, evaluated the same way (first touch from the open side)
    ctl = []
    for t0, side, ty, lv, _, _ in T.sample(min(len(T), 4000), random_state=180).itertuples(index=False):
        j0 = ix.get_loc(t0); sh = RNG.uniform(0.005, 0.02) * RNG.choice([1, -1]); pl = lv * (1 + sh)
        for k in range(max(1, j0 - 72), min(n - 13, j0 + 72)):
            if side == "above" and O[k] < pl <= H[k]: ctl.append((ix[k], C[k] < pl, (pl - C[k + 12]) / pl)); break
            if side == "below" and O[k] > pl >= L[k]: ctl.append((ix[k], C[k] > pl, (C[k + 12] - pl) / pl)); break
    Cc = pd.DataFrame(ctl, columns=["t", "rev", "ret"])
    return R, T, Cc, mid

def seg(df, mid): return (("dev", df[df.t < mid]), ("hold", df[df.t >= mid]))
log("STOPS AT STRUCTURE — Coinbase hourly Nov 2023 - Nov 2026 (dev = first half, holdout = second half)")
for p in STEP:
    R, T, Cc, mid = run(p)
    log(f"\n{p}  ({len(R)} races, {len(T)} level touches, {len(Cc)} control touches)")
    for lab, df in seg(R, mid):
        ex = df.up - df.null; se = ex.std() / np.sqrt(len(df))
        log(f"  A race {lab:4}: up first {100*df.up.mean():.1f}% vs distance null {100*df.null.mean():.1f}% -> excess {100*ex.mean():+.1f}pp (+-{196*se:.1f})")
        for hl, m in (("heavier side above", df.heavy > 0), ("heavier side below", df.heavy < 0)):
            x = df[m]
            if len(x) > 30: log(f"      {hl:20} n{len(x):4}: up {100*x.up.mean():.1f}% vs null {100*x.null.mean():.1f}% -> {100*(x.up-x.null).mean():+.1f}pp")
        for ty in ("swing", "day", "week"):
            x = df[df.tu == ty]
            if len(x) > 30: log(f"      nearest above is {ty:5} n{len(x):4}: excess {100*(x.up-x.null).mean():+.1f}pp")
    for lab, df in seg(T, mid):
        c = Cc[(Cc.t < mid) if lab == "dev" else (Cc.t >= mid)]
        log(f"  B sweep {lab:4}: touch bar closes back {100*df.rev.mean():.1f}% (control {100*c.rev.mean():.1f}%) | 12h reversal return {100*df.ret.mean():+.3f}% (control {100*c.ret.mean():+.3f}%)")
        for ty in ("swing", "day", "week"):
            x = df[df.ty == ty]
            if len(x) > 30: log(f"      {ty:5} n{len(x):5}: closes back {100*x.rev.mean():.1f}% | 12h {100*x.ret.mean():+.3f}%")
log("done")
