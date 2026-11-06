"""Doc 190 — tools for trending, high-volatility days (DK 6 Nov 2026 17:45: "we lack the right tools ... to operate in all markets" /
"We'll work on it"). Pre-registered 6 Nov 2026 before any result.
Data: Dukascopy 5-min, Nov 2025 - Oct 2026: US Tech 100 (data_nq_cache), US 500 and FTSE 100 (data_ign). Dev Nov-Apr / hold May-Oct.
Costs (IG, round trip, in points): US Tech 100 1.0, US 500 0.4, FTSE 1.0; stops slip 0.5 x spread extra. Flat at the cash close.
A  TREND-DAY PULLBACK. After the first 60 min of the cash session the day is a TREND DAY if: first-hour range >= 1.2 x its 20-day mean,
   the 60-min close is beyond the session VWAP in the direction of (close60 - open), and 5-min EMA20 is on the same side of EMA50.
   Then (until 60 min before the close, max 3 trades/day, one at a time): a pullback bar touches EMA20 against the trend while price stays
   on the trend side of VWAP, and the next bar CLOSES back on the trend side of EMA20 -> enter at that close, in the trend direction.
   Stop: beyond the extreme of the last 6 bars + 0.25 ATR(14). Breakeven at +1R. Exit at stop or the cash close.
B  ORB ON VOLATILE DAYS. Opening range = first 30 min. Day qualifies if the prior-day VIX close >= 20 OR the OR >= 1.3 x its 20-day mean.
   First 5-min close beyond the OR (before 13:00 local) -> enter that way; stop at the opposite side of the OR; exit at the cash close.
   Control B0: the same ORB on ALL days.
CONTROL for both: the same entries with a random direction (seeded), identical stop distance and exits.
C  MEAN REVERSION AFTER A BIG MOVE (DK 17:46 "mean reversion from big moves ... we need to look into"; AuclairsDad's 4th algo type).
   Big move: the session's move from the open reaches >= 1.0 x the 20-day mean session range (before 60 min before the close).
   Trigger: the first 5-min close that has come back >= 0.25 x that mean range from the session extreme -> enter AGAINST the move.
   Stop: beyond the session extreme + 0.25 ATR(14). Target: 50% retrace of the open-to-extreme move; else exit at the cash close. One per day.
   Variant C2: same but only when the prior-day VIX close >= 20.
PASS: mean >= +0.10R net in BOTH halves, >= 30 trades per half, and above the random-direction control in both halves.
"""
import os, json, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.chdir("/home/claude/qlab")
OUT = open("runs/trend_day_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
SPLIT = pd.Timestamp("2026-05-01", tz="UTC"); RNG = np.random.default_rng(190)
MK = {"US Tech 100": ("/home/claude/qlab-git/data_nq_cache/nq_5m.csv", 1.0, "America/New_York", (9, 30), (16, 0)),
      "US 500": ("data_ign/USA500IDXUSD_5m.csv", 0.4, "America/New_York", (9, 30), (16, 0)),
      "FTSE 100": ("data_ign/GBRIDXGBP_5m.csv", 1.0, "Europe/London", (8, 0), (16, 30))}
vj = json.load(open("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/vix.json"))["chart"]["result"][0]
VIX = pd.Series(vj["indicators"]["quote"][0]["close"], index=pd.to_datetime(vj["timestamp"], unit="s").normalize().date).dropna()
VIX = VIX[~VIX.index.duplicated()]
def prior_vix(day):
    s = VIX[[d < day for d in VIX.index]]; return float(s.iloc[-1]) if len(s) else np.nan

def manage(seg, i, side, entry, stop, cost, be=True):
    """seg: session frame from bar i+1 on. returns R net"""
    risk = abs(entry - stop); st = stop; moved = False
    H, L, C = seg.high.values, seg.low.values, seg.close.values
    for k in range(i + 1, len(seg)):
        if (side == 1 and L[k] <= st) or (side == -1 and H[k] >= st):
            pts = side * (st - entry) - cost * (1.5 if not moved or st != entry else 1.0)
            return pts / risk
        if be and not moved and side * (C[k] - entry) >= risk: st = entry; moved = True
    return (side * (C[-1] - entry) - cost) / risk

def run(name, f, cost, tz, o, c):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated()].sort_index()
    d = d[d.index >= "2025-10-01"]
    lt = d.index.tz_convert(tz); m = lt.hour * 60 + lt.minute; om, cm = o[0] * 60 + o[1], c[0] * 60 + c[1]
    d = d[(m >= om) & (m < cm)].copy(); lt = d.index.tz_convert(tz); d["day"] = lt.date; d["m"] = lt.hour * 60 + lt.minute - om
    A, B, B0, Cc, C2 = [], [], [], [], []; fh_hist, or_hist, rng_hist = [], [], []
    for day, s in d.groupby("day"):
        s = s.reset_index()
        if len(s) < (cm - om) // 5 - 6: continue
        tp = (s.high + s.low + s.close) / 3; v = s.get("vol", pd.Series(1.0, index=s.index)).replace(0, 1.0)
        vwap = (tp * v).cumsum() / v.cumsum()
        e20 = s.close.ewm(span=20, adjust=False).mean(); e50 = s.close.ewm(span=50, adjust=False).mean()
        tr = pd.concat([s.high - s.low, (s.high - s.close.shift()).abs(), (s.low - s.close.shift()).abs()], axis=1).max(axis=1); atr = tr.rolling(14, min_periods=5).mean()
        fh = s[s.m < 60]; orr = s[s.m < 30]; t0 = s[s.columns[0]].iloc[0]
        fh_rng, or_rng = fh.high.max() - fh.low.min(), orr.high.max() - orr.low.min()
        fh_ok = len(fh_hist) >= 20 and fh_rng >= 1.2 * np.mean(fh_hist[-20:]); or_big = len(or_hist) >= 20 and or_rng >= 1.3 * np.mean(or_hist[-20:])
        hot = (prior_vix(day) >= 20) or or_big
        # --- B / B0: ORB
        oh, ol = orr.high.max(), orr.low.min()
        for k in range(len(orr), len(s)):
            if s.m[k] >= 13 * 60 - om + 0: break
            side = 1 if s.close[k] > oh else -1 if s.close[k] < ol else 0
            if side:
                stop = ol if side == 1 else oh; entry = s.close[k]
                if abs(entry - stop) > 0:
                    r = manage(s, k, side, entry, stop, cost, be=False); rs = RNG.choice([1, -1])
                    rc = manage(s, k, rs, entry, entry - rs * abs(entry - stop), cost, be=False)
                    B0.append((t0, r, rc))
                    if len(or_hist) >= 20 and hot: B.append((t0, r, rc))
                break
        # --- A: trend-day pullback
        k60 = int(np.searchsorted(s.m.values, 60))
        if fh_ok and k60 < len(s):
            dirn = 1 if s.close[k60 - 1] > s.open[0] else -1
            if dirn * (s.close[k60 - 1] - vwap[k60 - 1]) > 0 and dirn * (e20[k60 - 1] - e50[k60 - 1]) > 0:
                n = 0; busy = -1
                for k in range(k60, len(s) - 1):
                    if s.m[k] >= (cm - om) - 60 or n >= 3: break
                    if k <= busy: continue
                    touched = (s.high[k] >= e20[k]) if dirn == -1 else (s.low[k] <= e20[k])
                    trend_side = dirn * (s.close[k] - vwap[k]) > 0
                    if touched and trend_side and dirn * (s.close[k + 1] - e20[k + 1]) > 0:
                        j = k + 1; entry = s.close[j]; w = s.iloc[max(0, j - 5):j + 1]
                        stop = (w.high.max() + 0.25 * atr[j]) if dirn == -1 else (w.low.min() - 0.25 * atr[j])
                        if dirn * (entry - stop) <= 0: continue
                        r = manage(s, j, dirn, entry, stop, cost); rs = RNG.choice([1, -1])
                        rc = manage(s, j, rs, entry, entry - rs * abs(entry - stop), cost)
                        A.append((t0, r, rc)); n += 1
                        # busy until exit: approximate by skipping 6 bars
                        busy = j + 6
        # --- C: mean reversion after a big move
        if len(rng_hist) >= 20:
            mr = np.mean(rng_hist[-20:]); op = s.open[0]; hi = lo = op; done = False
            for k in range(len(s) - 1):
                if s.m[k] >= (cm - om) - 60 or done: break
                hi = max(hi, s.high[k]); lo = min(lo, s.low[k])
                up_big, dn_big = hi - op >= mr, op - lo >= mr
                side = 0
                if up_big and s.close[k] <= hi - 0.25 * mr: side, ext = -1, hi
                elif dn_big and s.close[k] >= lo + 0.25 * mr: side, ext = 1, lo
                if side:
                    entry = s.close[k]; stop = ext + 0.25 * atr[k] if side == -1 else ext - 0.25 * atr[k]
                    tgt = ext + side * 0.5 * abs(ext - op); risk = abs(entry - stop); done = True
                    if risk <= 0 or side * (tgt - entry) <= 0: break
                    def mgo(sd, st, tg):
                        for q in range(k + 1, len(s)):
                            if (sd == 1 and s.low[q] <= st) or (sd == -1 and s.high[q] >= st): return (sd * (st - entry) - 1.5 * cost) / risk
                            if (sd == 1 and s.high[q] >= tg) or (sd == -1 and s.low[q] <= tg): return (sd * (tg - entry) - cost) / risk
                        return (sd * (s.close.iloc[-1] - entry) - cost) / risk
                    r = mgo(side, stop, tgt); rs = RNG.choice([1, -1]); rc = mgo(rs, entry - rs * risk, entry + rs * abs(tgt - entry))
                    Cc.append((t0, r, rc))
                    if prior_vix(day) >= 20: C2.append((t0, r, rc))
        fh_hist.append(fh_rng); or_hist.append(or_rng); rng_hist.append(s.high.max() - s.low.min())
    return [pd.DataFrame(x, columns=["t", "R", "ctl"]) for x in (A, B, B0, Cc, C2)]

log("TREND-DAY TOOLS — net of IG costs; R per trade; random-direction control alongside")
for name, (f, cost, tz, o, c) in MK.items():
    A, B, B0, Cc, C2 = run(name, f, cost, tz, o, c)
    log(f"\n{name}")
    for lab, T in (("A trend-day pullback", A), ("B ORB volatile days", B), ("B0 ORB all days", B0), ("C mean-rev big move", Cc), ("C2 same, VIX>=20", C2)):
        cells = []
        for seg, msk in (("dev", T.t < SPLIT), ("hold", T.t >= SPLIT)):
            x = T[msk]
            cells.append(f"{seg} n{len(x):3} {x.R.mean():+.3f}R (ctl {x.ctl.mean():+.3f}) win {100*(x.R>0).mean():.0f}%" if len(x) else f"{seg} none")
        log(f"  {lab:22} " + " || ".join(cells))
log("done")
