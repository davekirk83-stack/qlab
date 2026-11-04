"""Doc 181 — putting doc 180 into the IG engines (DK 4 Nov 09:25 "Yes"). Pre-registered 4 Nov 2026 before any result.
Data: Dukascopy 5-min bars (with tick volume) Nov 2025 - Oct 2026: US Tech 100 (data_nq_cache), US 500, FTSE 100 (data_ign).
Split dev Nov-Apr / holdout May-Oct. IG costs as doc 175 (spread per market, 0.018%/night funding).
LEVELS: prior day high/low and prior week high/low, days and weeks in the market's own time zone; all known before the day starts.
HEAVY BREAK: a 15-min bar trading beyond a prior-day or prior-week high (low) with volume >= 2x the mean of the previous 96 bars.
PART 1 — RANGE v3 LADDER, own-session (the book 13 v2 engine, paperbook6 unchanged except one line):
  F0 baseline (as registered)
  F1 after a heavy DOWN-break, place no long rungs for 4h (new or existing episodes); mirror for shorts after a heavy UP-break
  F2 as F1 but any break (no volume condition)
  F3 as F1 but blocked for the rest of the market's day
  Scored: episodes, sum of episode returns (P&L at fixed allocation), mean, share of 'stop'/'break' exits, worst episode.
  Pass = F1 (the registered candidate) raises the sum in both halves on at least 2 of 3 markets without cutting episodes by >25%.
PART 2 — IGNITION v1.1 on the US Tech 100 (US hours, the book 13 engine): split trades by whether the signal bar (or the 2 before it)
  broke a prior-day / prior-week high (longs) or low (shorts) - i.e. the breakout is THROUGH structure. Compare mean R, dev and holdout.
  Pass = 'through structure' trades beat the rest by >= 0.15R in both halves."""
import sys, os, inspect, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
import paperbook6 as P6, paperbook8 as P8, paperbook7 as P7
OUT = open("runs/level_filters_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
SPLIT = pd.Timestamp("2026-05-01", tz="UTC"); FUND = 0.00018
def load5(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[~d.index.duplicated()].sort_index()
def to15(d):
    r = d.resample("15min")
    return pd.DataFrame({"open": r.open.first(), "high": r.high.max(), "low": r.low.min(), "close": r.close.last(), "vol": r.vol.sum()}).dropna()

# one-line change to the engine: rungs skip a blocked side. Everything else in step() is the registered code.
src = inspect.getsource(P6.step).replace('def step(sym, d, pos, since, slots_free, hold_regime=False):', 'def step_blk(sym, d, pos, since, slots_free, hold_regime=False, BLK=None):')
src = src.replace('''        if not ok: continue
        for side in ("L", "S"):
            p = pos.get(side)''', '''        if not ok: continue
        for side in ("L", "S"):
            if BLK is not None and BLK[side][i]: continue
            p = pos.get(side)''')
assert "BLK[side][i]" in src
exec(src, P6.__dict__); step_blk = P6.step_blk

def breaks(b, tz):
    lt = b.index.tz_convert(tz); day = pd.Series(lt.normalize().tz_localize(None), index=b.index); wk = pd.Series(lt.tz_localize(None).to_period("W"), index=b.index)
    dH = b.high.groupby(day.values).max(); dL = b.low.groupby(day.values).min(); wH = b.high.groupby(wk.values).max(); wL = b.low.groupby(wk.values).min()
    days = list(dH.index); prevd = {days[k]: days[k - 1] for k in range(1, len(days))}
    pdH = day.map(lambda x: dH.get(prevd.get(x), np.nan)).values; pdL = day.map(lambda x: dL.get(prevd.get(x), np.nan)).values
    pwH = wk.map(lambda x: wH.get(x - 1, np.nan)).values; pwL = wk.map(lambda x: wL.get(x - 1, np.nan)).values
    upb = (b.high.values > np.fmin(pdH, pwH)) & ~np.isnan(pdH); dnb = (b.low.values < np.fmax(pdL, pwL)) & ~np.isnan(pdL)
    # 'beyond a prior high' = above the NEARER of the two highs (the first one in the way)
    vr = (b.vol / b.vol.rolling(96).mean().shift(1)).values
    return upb, dnb, vr, day.values, pdH, pdL, pwH, pwL

log("PART 1 — RANGE v3 LADDER WITH A BREAK FILTER (own session, IG costs; episode returns are on the episode's intended size)")
MK = {"US Tech 100": ("data_nq_cache/nq_5m.csv", 1.0, ("America/New_York", 9.5, 16)),
      "US 500": ("data_ign/USA500IDXUSD_5m.csv", 0.4, ("America/New_York", 9.5, 16)),
      "FTSE 100": ("data_ign/GBRIDXGBP_5m.csv", 1.0, ("Europe/London", 8, 16.5))}
def gate(tz, h0, h1):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = P8._orig_ind(d, sym); t = d.index.tz_convert(tz); h = t.hour + t.minute / 60
        return ema, lob, hib, a, allow & ((h >= h0) & (h < h1))
    return ind
summary = {}
for name, (f, sp, (tz, h0, h1)) in MK.items():
    b = to15(load5(f)); b = b[b.index >= "2025-10-20"]; px = float(b.close.median())
    P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
    upb, dnb, vr, day, *_ = breaks(b, tz); n = len(b)
    heavy_up, heavy_dn = upb & (vr >= 2), dnb & (vr >= 2)
    def block(ev, bars=None, rest_of_day=False):
        out = np.zeros(n, bool)
        for k in np.flatnonzero(ev):
            if rest_of_day: out[k:k + 1 + int(np.sum(day[k:k + 120] == day[k]))] = True
            else: out[k:k + 1 + bars] = True
        return out[:n]
    variants = {"F0 baseline": None,
                "F1 heavy break, 4h": {"L": block(heavy_dn, 16), "S": block(heavy_up, 16)},
                "F2 any break, 4h": {"L": block(dnb, 16), "S": block(upb, 16)},
                "F3 heavy break, rest of day": {"L": block(heavy_dn, rest_of_day=True), "S": block(heavy_up, rest_of_day=True)}}
    log(f"\n{name}: {int(heavy_dn.sum())} heavy down-break bars, {int(heavy_up.sum())} heavy up-break bars, {int(dnb.sum()+upb.sum())} break bars in all")
    P6.indicators = gate(tz, h0, h1); res = {}
    for lab, BLK in variants.items():
        P6._MED = {}
        closed, _ = step_blk(name, b, {}, str(b.index[250]), [10**6], BLK=BLK)
        rows = []
        for c in closed:
            o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
            if o < pd.Timestamp("2025-11-01", tz="UTC"): continue
            rows.append((o, c[4] - max(0, (cl.normalize() - o.normalize()).days) * FUND, c[5]))
        E = pd.DataFrame(rows, columns=["t", "r", "how"]); res[lab] = E
        cells = []
        for seg, m in (("dev", E.t < SPLIT), ("hold", E.t >= SPLIT)):
            x = E[m]; cells.append(f"{seg} n{len(x):3} sum {100*x.r.sum():+6.2f}% mean {100*x.r.mean():+.3f}% stop/break {100*x.how.isin(['stop','break']).mean():3.0f}% worst {100*x.r.min():+.2f}%")
        log(f"  {lab:28} " + " || ".join(cells))
    P6.indicators = P8._orig_ind; summary[name] = res

log("\nPART 2 — IGNITION v1.1, US Tech 100, US hours: trades whose breakout goes THROUGH a prior-day / prior-week level vs the rest")
d = load5("data_nq_cache/nq_5m.csv"); d = d[d.index >= "2025-10-20"]
f = P7.features(d); t = f.index.tz_convert("America/New_York"); m = t.hour * 60 + t.minute
ins = (m >= 9 * 60 + 30) & (m < 16 * 60); skip = np.isin(t.hour, P7.V11_SKIP_HOURS); f["cost"] = np.where(ins, 0.5, 1.0)
O, H, L, C, cost, atr, sig, dd, idx = f.open.values, f.high.values, f.low.values, f.close.values, f.cost.values, f.atr.values, f.sig.values, f.day.values, f.index
# prior levels on the 5-min frame, NY days / weeks
lt = idx.tz_convert("America/New_York"); dser = pd.Series(lt.normalize().tz_localize(None)); wser = pd.Series(lt.tz_localize(None).to_period("W"))
dH = pd.Series(H).groupby(dser).max(); dL = pd.Series(L).groupby(dser).min(); wH = pd.Series(H).groupby(wser).max(); wL = pd.Series(L).groupby(wser).min()
days = list(dH.index); prevd = {days[k]: days[k - 1] for k in range(1, len(days))}
pdH = dser.map(lambda x: dH.get(prevd.get(x), np.nan)).values; pdL = dser.map(lambda x: dL.get(prevd.get(x), np.nan)).values
pwH = wser.map(lambda x: wH.get(x - 1, np.nan)).values; pwL = wser.map(lambda x: wL.get(x - 1, np.nan)).values
ok = ins & ~skip; T = []; last = -10**9; cur = None; ntr = 0; dpl = 0
for i in range(300, len(C) - 1):
    if dd[i] != cur: cur = dd[i]; ntr = 0; dpl = 0
    s = int(sig[i])
    if s == 0 or not ok[i] or np.isnan(atr[i]) or i < last + P7.COOL or ntr >= P7.MAXT or dpl <= -P7.LOSSCAP: continue
    sp = max(P7.STOP, P7.V11_STOP_ATR * atr[i]); r = P7.manage(O, H, L, C, cost, atr, i, s, len(C), sp)
    if r is None: break
    last = i + r[1]; ntr += 1; dpl += r[0]
    w = slice(max(0, i - 2), i + 1)
    if s == 1: thr_d, thr_w = H[w].max() > pdH[i], H[w].max() > pwH[i]; pre = C[max(0, i - 3)] <= np.nanmin([pdH[i], pwH[i]])
    else: thr_d, thr_w = L[w].min() < pdL[i], L[w].min() < pwL[i]; pre = C[max(0, i - 3)] >= np.nanmax([pdL[i], pwL[i]])
    through = bool((thr_d or thr_w) and pre)
    T.append((idx[i], r[0] / sp, through, bool(thr_w and pre)))
T = pd.DataFrame(T, columns=["t", "R", "through", "week"]); T = T[T.t >= pd.Timestamp("2025-11-01", tz="UTC")]
for seg, mm in (("dev", T.t < SPLIT), ("hold", T.t >= SPLIT)):
    x = T[mm]; a, b_ = x[x.through], x[~x.through]; w_ = x[x.week]
    log(f"  {seg:4}: through a level n{len(a):3} {a.R.mean():+.3f}R win {100*(a.R>0).mean():.0f}% | the rest n{len(b_):3} {b_.R.mean():+.3f}R win {100*(b_.R>0).mean():.0f}% | gap {a.R.mean()-b_.R.mean():+.3f}R | through a WEEK level n{len(w_)} {w_.R.mean():+.3f}R")
log("done")
