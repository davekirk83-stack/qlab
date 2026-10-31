"""Doc 168 — the trend-line break-and-retest rebuilt as practitioners trade it (rule 188). DK 31 Oct: "Can you refine it to improve the
execution? Or find information online for this technique?" ... "Or consider timeframes?"  Pre-registered 31 Oct 2026 before any result.

WHY: the forward retest book (doc 42/43 spec) fails at -0.75R with 89% full stop-outs. Three suspects:
  (1) the stop is 0.4 ATR under the line on hourly crypto - inside normal noise;
  (2) entry on the first touch, with no confirmation that the retest held;
  (3) a LOOKAHEAD in the backtest that registered it: diagonal_setups() uses a pivot high from the bar it occurs, but a pivot is only
      known `window` (5) bars later, so the backtest could draw a line through a high that was not yet a confirmed high.
PRACTITIONER RULES (FXOpen, MQL5 trend-line guides, capital.com break-retest): line through meaningful swing highs, >=3 points;
  a decisive close through it; wait for price to come back and HOLD (confirmation candle) - do not enter on the touch; stop beyond the
  retest swing / confirmation candle; target the next swing high / resistance; check the higher-timeframe trend first; trade the
  break on a higher timeframe and refine the entry lower.
ARMS (all with the lookahead fixed: a pivot is usable only from its confirmation bar):
  A3 AS REGISTERED (>=3 touches after the two anchors); A the same on >=3 points in total: entry at the first-touch close above the line; stop line - 0.4 ATR; hold 40 bars, no target.
  P  PRACTITIONER: after the touch, enter on the first bar (within 5) that closes above the line, above its open and above the prior
     bar's high; void if a close falls 0.4 ATR under the line first. Stop = lowest low since the break - 0.2 ATR, at least 1 ATR below
     entry. Target = highest high of the 60 bars before the break (the last swing high above); skip if < 1.5R. Cap 120 bars.
  PH P + higher-timeframe trend: prior completed DAILY close above the daily EMA50 (weekly EMA20 for the daily timeframe).
TIMEFRAMES: 1h, 4h, 1d on the 27 registered coins (Coinbase 15m resampled, 2021-2026); 1d on the 59 clean ETFs.
COSTS: crypto 0.10%/side, ETFs 0.05%/side, charged in R. SPLIT: dev < 2025-01-01, holdout after.
CONTROL (point-in-time): random bars of the same symbol and timeframe (HTF-up bars only for PH), same entry/stop/target construction
  (stop = 10-bar low - 0.2 ATR, >= 1 ATR; target = 60-bar high, >= 1.5R; A-control = hold 40 with a 0.4 ATR... stop at 10-bar low),
  5 per trade.  Trials: 3 arms x 4 universes = 12 (rule 179)."""
import sys, os, glob, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab-git/src"); os.chdir("/home/claude/qlab")
import structure as ST, patterns_proper as PP
from levels_general import CLEAN_ETF
SPLIT = pd.Timestamp("2025-01-01"); RNG = np.random.default_rng(31)
OUT = open("runs/retest_faithful_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
AGG = {"open": "first", "high": "max", "low": "min", "close": "last"}

def htf_flag(d, tf):
    dy = d.resample("1D").agg(AGG).dropna() if tf != "1d" else d
    if tf == "1d":
        wk = d.resample("W-SUN").agg(AGG).dropna(); ok = (wk.close > wk.close.ewm(span=20, adjust=False).mean()).shift(1)
        return ok.reindex(d.index, method="ffill").fillna(False).values.astype(bool)
    ok = (dy.close > dy.close.ewm(span=50, adjust=False).mean()).shift(1)
    return ok.reindex(d.index.floor("1D")).fillna(False).values.astype(bool)

def setups(d):
    H, L, C, O = d.high.values, d.low.values, d.close.values, d.open.values; n = len(C)
    a = ST.atr(d).bfill().values
    try: _, highs = PP.confirmed_pivots(d)
    except Exception: return [], a
    out = []
    for ai in range(len(highs) - 1):
        for bi in range(ai + 1, min(ai + 6, len(highs))):
            (i1, _), (i2, k2) = highs[ai], highs[bi]
            if i2 - i1 < 10 or H[i2] >= H[i1]: continue
            slope = (H[i2] - H[i1]) / (i2 - i1); line = lambda j: H[i1] + slope * (j - i1)
            touches, brk = 0, None
            for j in range(k2, min(n - 2, i2 + 400)):          # usable only once the second pivot is CONFIRMED
                lv = line(j)
                if lv <= 0: break
                if C[j] > lv + 0.4 * a[j]: brk = j; break
                if abs(H[j] - lv) <= 0.4 * a[j]: touches += 1
            if brk is None or touches + 2 < 3: continue          # >=3 points incl. the two anchors (practitioner count)
            touch = None
            for j in range(brk + 1, min(brk + 21, n - 1)):
                lv = line(j)
                if C[j] < lv - 0.4 * a[j]: break
                if L[j] <= lv + 0.4 * a[j] and C[j] > lv: touch = j; break
            if touch is None: continue
            rec = {"brk": brk, "touch": touch, "tc": touches, "A_stop": line(touch) - 0.4 * a[touch], "conf": None}
            for j in range(touch, min(touch + 6, n - 1)):
                lv = line(j)
                if C[j] < lv - 0.4 * a[j]: break
                if C[j] > lv and C[j] > O[j] and C[j] > H[j - 1]: rec["conf"] = j; break
            if rec["conf"] is not None:
                c = rec["conf"]; e = C[c]; st = min(L[brk:c + 1].min() - 0.2 * a[c], e - a[c])
                tg = H[max(0, brk - 60):brk].max(); rec["P"] = (e, st, tg)
            out.append(rec); break
    return out, a

def sim(d, a, i, e, st, tg, cost, hold=None):
    H, L, C = d.high.values, d.low.values, d.close.values; n = len(C); risk = e - st
    if risk <= 0: return None
    cR = 2 * cost * e / risk
    if hold:                                                   # arm A: stop only, exit at the hold-bar close
        for j in range(i + 1, min(i + hold + 1, n)):
            if L[j] <= st: return -1 - cR
        j = min(i + hold, n - 1); return (C[j] - e) / risk - cR
    if (tg - e) / risk < 1.5: return None
    for j in range(i + 1, min(i + 121, n)):
        if L[j] <= st: return -1 - cR
        if H[j] >= tg: return (tg - e) / risk - cR
    return (C[min(i + 120, n - 1)] - e) / risk - cR

def ctrl(d, a, i, cost, hold):
    H, L, C = d.high.values, d.low.values, d.close.values; e = C[i]
    st = min(L[i - 9:i + 1].min() - 0.2 * a[i], e - a[i])
    if hold: return sim(d, a, i, e, st, None, cost, hold)
    return sim(d, a, i, e, st, H[i - 60:i].max(), cost)

def universe(kind):
    if kind == "etf":
        for s in sorted(CLEAN_ETF):
            p = f"data_wide/{s}.csv"
            if os.path.exists(p):
                d = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()[["open", "high", "low", "close"]].astype(float)
                if len(d) > 600: yield s, d, "1d", 0.0005
        return
    syms = json.load(open("runs/range_universe.json"))["registered_universe"]
    for s in syms:
        d = pd.read_csv(f"data_15m/{s}.csv"); d["t"] = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601")
        d = d.set_index("t")[["open", "high", "low", "close"]].astype(float); d.index = d.index.tz_localize(None)
        rule = {"1h": "1h", "4h": "4h", "1d": "1D"}[kind]
        yield s, d.resample(rule).agg(AGG).dropna(), kind, 0.001

res = {}
for kind in ("1h", "4h", "1d", "etf"):
    rows = []
    for s, d, tf, cost in universe(kind):
        if len(d) < 400: continue
        U, a = setups(d); up = htf_flag(d, tf); n = len(d); idx = d.index
        pool_all = np.arange(70, n - 2); pool_up = pool_all[up[pool_all]]
        for u in U:
            t = u["touch"]; seg = "dev" if idx[t] < SPLIT else "hold"
            rA = sim(d, a, t, d.close.values[t], u["A_stop"], None, cost, hold=40)
            if rA is not None:
                cs = [ctrl(d, a, int(RNG.choice(pool_all)), cost, 40) for _ in range(5)]
                rows.append(("A", seg, s, rA, np.nanmean([c for c in cs if c is not None] or [np.nan])))
                if u["tc"] >= 3: rows.append(("A3", seg, s, rA, rows[-1][4]))
            if "P" in u:
                c = u["conf"]; e, st, tg = u["P"]; rP = sim(d, a, c, e, st, tg, cost)
                if rP is not None:
                    cs = [ctrl(d, a, int(RNG.choice(pool_all)), cost, None) for _ in range(15)]; cs = [x for x in cs if x is not None][:5]
                    rows.append(("P", seg, s, rP, np.nanmean(cs) if cs else np.nan))
                    if up[c]:
                        cs = [ctrl(d, a, int(RNG.choice(pool_up)), cost, None) for _ in range(15)] if len(pool_up) else []
                        cs = [x for x in cs if x is not None][:5]
                        rows.append(("PH", seg, s, rP, np.nanmean(cs) if cs else np.nan))
        print(kind, s, len(U), flush=True)
    R = pd.DataFrame(rows, columns=["arm", "seg", "sym", "r", "c"])
    log(f"\n=== {kind.upper()} {'(27 coins)' if kind != 'etf' else '(59 clean ETFs, daily)'} ===")
    for arm in ("A3", "A", "P", "PH"):
        cell = []
        for seg in ("dev", "hold"):
            x = R[(R.arm == arm) & (R.seg == seg)]
            if len(x) < 5: cell.append(f"{seg} n{len(x)}"); continue
            t = x.r.mean() / (x.r.std() / np.sqrt(len(x)))
            cell.append(f"{seg} n{len(x):4} {x.r.mean():+.3f}R (t {t:+.1f}) win {100*(x.r>0).mean():.0f}% stop-outs {100*(x.r<=-1).mean():.0f}% | ctrl {x.c.mean():+.3f}R edge {x.r.mean()-x.c.mean():+.3f}R")
        log(f"  {arm:2}: " + "  ||  ".join(cell))
log("done")
