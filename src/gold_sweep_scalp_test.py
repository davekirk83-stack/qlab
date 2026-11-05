"""Doc 187 — Brad Goh's gold scalping framework, tested as he describes it (rule 188). DK 5 Nov 2026 05:28 "Yes".
Pre-registered 5 Nov 2026 before any result.
Source: @Bradgohtrades thread, 4 Nov 2026: (1) 1H and 15M trends must align, misaligned = no trade; (2) mark 15M supply/demand zones +
liquidity, no entry outside a zone; (3) wait for a liquidity sweep + confirmation; (4) target the nearest 15M swing high/low, conservative;
stop directly beyond the candle that swept liquidity.
Data: Dukascopy XAU/USD 5-min, Nov 2025 - Oct 2026 (data_ign). Dev Nov-Apr, holdout May-Oct.
Costs: IG spot gold spread 0.5 pt round trip (live check 4 Nov 17:35: 4068.48/4068.98) + 0.1 pt slippage on stop exits. No overnight
holds (flat at 20:55 UTC), so no funding.
DEFINITIONS (the common SMC reading of each step; one primary version fixed before results):
  swings      fractal pivots, k=2 bars each side, usable only once confirmed (k bars later)
  trend       per timeframe (15M, 1H): last two confirmed swing highs AND lows rising = bull, both falling = bear, else none
  zone        demand = the last bearish 15M candle (its low-high) before a 15M close above the latest swing high (break of structure);
              supply mirrored. Active from the BOS close, dead after a 15M close beyond its far edge, after 3 days, or once traded.
  sweep       (long) a 5M bar inside an active demand zone (low <= zone high, close >= zone low) whose low takes out the latest confirmed 5M swing low
  confirm     PRIMARY: within 12 5M bars, a 5M close above the latest confirmed 5M swing high (change of character). Entry at that close.
              ALT (reported, not the verdict): the sweep bar itself closes bullish back above the swept low; entry at its close.
  stop        lowest low from the sweep to entry, minus 0.1
  target      nearest confirmed 15M swing high above entry (skip the trade if none or if it is under 0.5R away... NOT applied: he sets no
              minimum; reported both ways)
  hours       entries 07:00-19:00 UTC (London + New York)
CONTROLS: the same engine with no trend filter; and trend + zone with entry at the first touch (no sweep), stop beyond the zone.
PASS: primary net mean >= +0.10R in BOTH halves with >= 40 trades each, and better than the no-trend control in both halves.
"""
import numpy as np, pandas as pd, os
os.chdir("/home/claude/qlab")
OUT = open("runs/gold_sweep_scalp_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
SPREAD, SLIP, K = 0.5, 0.1, 2
SPLIT = pd.Timestamp("2026-05-01", tz="UTC")

d5 = pd.read_csv("data_ign/XAUUSD_5m.csv", index_col=0); d5.index = pd.to_datetime(d5.index, utc=True)
d5 = d5[~d5.index.duplicated()].sort_index()[["open", "high", "low", "close"]].dropna()
def rs(d, rule):
    r = d.resample(rule, label="left", closed="left")
    return pd.DataFrame({"open": r.open.first(), "high": r.high.max(), "low": r.low.min(), "close": r.close.last()}).dropna()
d15, d60 = rs(d5, "15min"), rs(d5, "60min")

def pivots(d, k=K):
    """confirmed pivots: arrays of (confirm_time, price) for highs and lows"""
    H, L = d.high.values, d.low.values; n = len(d); ix = d.index
    ph, pl = [], []
    for i in range(k, n - k):
        if H[i] == H[i - k:i + k + 1].max() and H[i] > H[i - k:i].max(): ph.append((i + k, H[i]))
        if L[i] == L[i - k:i + k + 1].min() and L[i] < L[i - k:i].min(): pl.append((i + k, L[i]))
    return ph, pl

def trend_series(d, close_offset):
    """trend known at the CLOSE of each bar: +1/-1/0. close_offset = bar length (to index by close time)."""
    ph, pl = pivots(d); n = len(d); tr = np.zeros(n, int); hs, ls = [], []
    pi = qi = 0
    for i in range(n):
        while pi < len(ph) and ph[pi][0] <= i: hs.append(ph[pi][1]); pi += 1
        while qi < len(pl) and pl[qi][0] <= i: ls.append(pl[qi][1]); qi += 1
        if len(hs) >= 2 and len(ls) >= 2:
            if hs[-1] > hs[-2] and ls[-1] > ls[-2]: tr[i] = 1
            elif hs[-1] < hs[-2] and ls[-1] < ls[-2]: tr[i] = -1
    return pd.Series(tr, index=d.index + close_offset)

t15 = trend_series(d15, pd.Timedelta("15min")); t60 = trend_series(d60, pd.Timedelta("60min"))
# map to 5-min bar CLOSE times: the latest completed 15M/1H bar
c5 = d5.index + pd.Timedelta("5min")
T15 = t15.reindex(c5, method="ffill").fillna(0).values.astype(int); T60 = t60.reindex(c5, method="ffill").fillna(0).values.astype(int)

# 15M swing levels (confirmed) for targets and BOS; zones
ph15, pl15 = pivots(d15); O15, H15, L15, C15 = (d15[c].values for c in ("open", "high", "low", "close"))
zones = []   # dict(side, lo, hi, start (time active), end (time dead))
lastH = lastL = None; pi = qi = 0; i15 = d15.index
for i in range(len(d15)):
    while pi < len(ph15) and ph15[pi][0] <= i: lastH = ph15[pi][1]; pi += 1
    while qi < len(pl15) and pl15[qi][0] <= i: lastL = pl15[qi][1]; qi += 1
    for side in (1, -1):
        lvl = lastH if side == 1 else lastL
        if lvl is None: continue
        if (side == 1 and C15[i] > lvl and (i == 0 or C15[i - 1] <= lvl)) or (side == -1 and C15[i] < lvl and (i == 0 or C15[i - 1] >= lvl)):
            for j in range(i - 1, max(i - 11, -1), -1):
                if (side == 1 and C15[j] < O15[j]) or (side == -1 and C15[j] > O15[j]):
                    lo, hi = L15[j], H15[j]; start = i15[i] + pd.Timedelta("15min"); end = start + pd.Timedelta(days=3)
                    for m in range(i + 1, min(len(d15), i + 300)):
                        if (side == 1 and C15[m] < lo) or (side == -1 and C15[m] > hi): end = min(end, i15[m] + pd.Timedelta("15min")); break
                    zones.append(dict(side=side, lo=lo, hi=hi, start=start, end=end)); break
log(f"XAU/USD 5-min {d5.index[0]:%d %b %Y} - {d5.index[-1]:%d %b %Y}: {len(d5)} bars, {len(zones)} 15M zones (demand {sum(z['side']==1 for z in zones)}, supply {sum(z['side']==-1 for z in zones)})")

# 15M confirmed swing highs/lows by confirm time, for targets
sh15 = [(i15[c] + pd.Timedelta("15min"), p) for c, p in ph15]; sl15 = [(i15[c] + pd.Timedelta("15min"), p) for c, p in pl15]
ph5, pl5 = pivots(d5)
O, H, L, C = (d5[c].values for c in ("open", "high", "low", "close")); n = len(d5); hr = d5.index.hour.values
conf_h5 = np.full(n, np.nan); conf_l5 = np.full(n, np.nan)   # latest confirmed 5M swing high/low known at close of bar i
for c, p in ph5:
    if c < n: conf_h5[c] = p
for c, p in pl5:
    if c < n: conf_l5[c] = p
conf_h5 = pd.Series(conf_h5).ffill().values; conf_l5 = pd.Series(conf_l5).ffill().values
tpos = {t: k for k, t in enumerate(c5)}

def nearest_target(side, t, entry):
    best = None
    for ct, p in (sh15 if side == 1 else sl15):
        if ct > t: break
        if (side == 1 and p > entry) or (side == -1 and p < entry):
            if best is None or abs(p - entry) < abs(best - entry): best = p
    return best
# speed: only the last ~200 swings matter
MIN_R = 0.0
def nearest_target_fast(side, t, entry, arr_t, arr_p, mind=0.0):
    k = np.searchsorted(arr_t, t, side="right"); lo = max(0, k - 400)
    p = arr_p[lo:k]; p = p[p > entry + mind] if side == 1 else p[p < entry - mind]
    if not len(p): return None
    return p.min() if side == 1 else p.max()
SH_T = np.array([x[0].value for x in sh15]); SH_P = np.array([x[1] for x in sh15]); SL_T = np.array([x[0].value for x in sl15]); SL_P = np.array([x[1] for x in sl15])

def manage(side, k, entry, stop, tgt):
    """from bar k+1: stop/target intrabar (stop first if both), flat at 20:55 UTC. Returns (net pts, R, how, bars)."""
    risk = abs(entry - stop)
    for m in range(k + 1, n):
        if d5.index[m].hour >= 21 or d5.index[m].normalize() != d5.index[k].normalize():
            px = C[m - 1]; return side * (px - entry) - SPREAD, risk, "time", m - k
        if (side == 1 and L[m] <= stop) or (side == -1 and H[m] >= stop): return side * (stop - entry) - SPREAD - SLIP, risk, "stop", m - k
        if (side == 1 and H[m] >= tgt) or (side == -1 and L[m] <= tgt): return abs(tgt - entry) - SPREAD, risk, "target", m - k
        if d5.index[m].hour == 20 and d5.index[m].minute == 55: return side * (C[m] - entry) - SPREAD, risk, "time", m - k
    return None

def run(trend_on=True, confirm="choch", sweep_on=True):
    trades = []; zi = sorted(zones, key=lambda z: z["start"]); active = []; zp = 0; used = set()
    busy_until = -1
    for i in range(300, n - 1):
        t = c5[i]
        while zp < len(zi) and zi[zp]["start"] <= t: active.append(zp); zp += 1
        active = [a for a in active if zi[a]["end"] > t and a not in used]
        if i <= busy_until or not (7 <= hr[i] < 19): continue
        for a in active:
            z = zi[a]; s = z["side"]
            if trend_on and not (T15[i] == s and T60[i] == s): continue
            inside = (L[i] <= z["hi"] and C[i] >= z["lo"]) if s == 1 else (H[i] >= z["lo"] and C[i] <= z["hi"])
            if not inside: continue
            if not sweep_on:   # control: enter at the first touch, stop beyond the zone
                entry = C[i]; stop = (z["lo"] - 0.1) if s == 1 else (z["hi"] + 0.1)
                if (s == 1 and entry <= stop) or (s == -1 and entry >= stop): continue
                k = i
            else:
                lvl = conf_l5[i - 1] if s == 1 else conf_h5[i - 1]
                if np.isnan(lvl): continue
                swept = (L[i] < lvl) if s == 1 else (H[i] > lvl)
                if not swept: continue
                k = None; ext = L[i] if s == 1 else H[i]
                if confirm == "close":
                    if (s == 1 and C[i] > lvl and C[i] > O[i]) or (s == -1 and C[i] < lvl and C[i] < O[i]): k = i
                else:
                    for m in range(i, min(n - 1, i + 12)):
                        ext = min(ext, L[m]) if s == 1 else max(ext, H[m])
                        if (s == 1 and C[m] < z["lo"]) or (s == -1 and C[m] > z["hi"]): break
                        ref = conf_h5[i - 1] if s == 1 else conf_l5[i - 1]
                        if not np.isnan(ref) and ((s == 1 and C[m] > ref) or (s == -1 and C[m] < ref)): k = m; break
                if k is None: continue
                entry = C[k]; stop = (ext - 0.1) if s == 1 else (ext + 0.1)
            tgt = nearest_target_fast(s, c5[k].value, entry, SH_T if s == 1 else SL_T, SH_P if s == 1 else SL_P, MIN_R * abs(entry - stop))
            if tgt is None or abs(entry - stop) < 0.3: continue
            r = manage(s, k, entry, stop, tgt)
            if r is None: continue
            pts, risk, how, bars = r
            trades.append(dict(t=d5.index[k], side=s, R=pts / risk, pts=pts, risk=risk, rr=abs(tgt - entry) / risk, how=how, bars=bars))
            used.add(a); busy_until = k + bars; break
    return pd.DataFrame(trades)

def report(lab, T):
    if not len(T): log(f"  {lab}: no trades"); return
    cells = []
    for seg, m in (("dev", T.t < SPLIT), ("hold", T.t >= SPLIT)):
        x = T[m]
        if not len(x): cells.append(f"{seg} none"); continue
        cells.append(f"{seg} n{len(x):4} mean {x.R.mean():+.3f}R win {100*(x.R>0).mean():3.0f}% tgt {100*(x.how=='target').mean():3.0f}% med RR {x.rr.median():.2f} risk {x.risk.median():.1f}pt")
    log(f"  {lab:46} " + " || ".join(cells))
    return T

log("\nNet of 0.5 pt spread + 0.1 pt stop slippage. R = net points / risk (entry to stop).")
P = report("PRIMARY: trend + zone + sweep + 5M CHoCH", run())
report("  same, only trades with target >= 1R away", P[P.rr >= 1] if len(P) else P)
report("ALT: trend + zone + sweep, sweep bar closes back", run(confirm="close"))
report("CONTROL A: no trend filter (zone + sweep + CHoCH)", run(trend_on=False))
report("CONTROL B: trend + zone, enter on first touch", run(sweep_on=False))
if len(P):
    log(f"\n  primary gross (before costs) mean {((P.pts + SPREAD + SLIP*(P.how=='stop')) / P.risk).mean():+.3f}R; median risk {P.risk.median():.2f} pt = {100*P.risk.median()/C.mean():.3f}% of price; spread is {SPREAD/P.risk.median():.2f}R of a median trade")
    for s, lab in ((1, "longs"), (-1, "shorts")):
        x = P[P.side == s]; log(f"  {lab}: n{len(x)} mean {x.R.mean():+.3f}R")
log("\nADDENDUM (added after the first result, flagged as such): the nearest 15M swing is usually almost at the entry (median target 0.05-0.10R),")
log("which no scalper would take. Same engine, target = the nearest 15M swing at least X R away:")
for mr in (0.5, 1.0, 1.5, 2.0):
    MIN_R = mr
    report(f"PRIMARY, nearest swing >= {mr}R away", run())
    report(f"CONTROL A (no trend), nearest swing >= {mr}R", run(trend_on=False))
log("done")
