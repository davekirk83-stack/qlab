"""
FLOW-SCORE v1 — the AuclairsDad book, reverse-engineered (DK, 19 Oct 2026).

What his posts show: NQ futures, one lot, the overnight Globex session, ~7 trades
a night, 67% win rate, PF 1.68, 50-point stops, 20-35 point targets with a trail,
"based on a scoring mechanism", and the decisive input "the delta didn't go off
balance once, that's why there's no trades tonight" - order-flow delta, taken
with the higher-timeframe fast EMA ("goes with flow"), VWAP and drawn levels.

Translated to what we hold: 18 perps, 5-minute bars (from data_1m), with the
5-minute taker buy/sell volume ratio from data_oi (Binance metrics) as the delta.

SCORE (long; short is the mirror), 0-5:
  trend   15-minute EMA20 above EMA50 (the HTF fast EMA)
  vwap    close above the session (UTC-day) VWAP
  delta   15-minute taker imbalance z-score (vs last 24h) > +1.5
  level   within 0.5 ATR of the session VWAP or the prior day's high/low
          (his purple lines) - the pullback-to-level entry
  session Asia 00-08 UTC (his Globex: thin book, imbalances travel)
Trade when score >= 4. Also reported: delta OFF (other four >= 3), delta ONLY.

MANAGEMENT (his): stop 1.5 ATR14(5m); TP1 at +1 ATR takes half and moves the
stop to breakeven; the rest trails 1.5 ATR from the best price; cap 24 bars (2h).
Costs 4.5bp taker in and out. One row per episode, next-bar entry at the open.
CONTROL: random bar, same side, same management, 3 per trade.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
COST = 4.5/10000; RNG = np.random.default_rng(42)
D1M = "/home/claude/qlab/data_1m"; DOI = "/home/claude/qlab/data_oi"


def load(sym):
    d = pd.read_csv(f"{D1M}/{sym}.csv"); d.index = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d[["open","high","low","close","volume"]].astype(float)
    b = d.resample("5min").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    oi = pd.read_csv(f"{DOI}/{sym}.csv"); oi.index = pd.to_datetime(oi.create_time, utc=True)
    r = oi["sum_taker_long_short_vol_ratio"].astype(float)
    b["delta"] = ((r - 1)/(r + 1)).reindex(b.index)           # buy share minus sell share, -1..1
    b = b.dropna(subset=["delta"])
    return b


def features(b):
    C, H, L = b.close.values, b.high.values, b.low.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    b["atr"] = pd.Series(tr, index=b.index).rolling(14).mean().bfill().values
    c15 = b.close.resample("15min").last().dropna()
    ef = c15.ewm(span=20, adjust=False).mean(); es = c15.ewm(span=50, adjust=False).mean()
    trend = (ef > es).astype(int).shift(1)                      # shifted: the 15m bar must be complete
    b["trend"] = trend.reindex(b.index, method="ffill").values
    day = b.index.floor("D")
    tp = (b.high + b.low + b.close)/3
    b["vwap"] = (tp*b.volume).groupby(day).cumsum()/b.volume.groupby(day).cumsum()
    d3 = b.delta.rolling(3).mean()
    b["dz"] = (d3 - d3.rolling(288).mean())/d3.rolling(288).std()
    pdh = b.high.groupby(day).max().shift(1); pdl = b.low.groupby(day).min().shift(1)
    b["pdh"] = pdh.reindex(day).values; b["pdl"] = pdl.reindex(day).values
    b["hour"] = b.index.hour
    return b.dropna()


def scores(b, side):
    s = side
    trend = (b.trend == 1) if s == 1 else (b.trend == 0)
    vwap = (b.close > b.vwap) if s == 1 else (b.close < b.vwap)
    delta = (b.dz > 1.5) if s == 1 else (b.dz < -1.5)
    near = (np.minimum(np.abs(b.close-b.vwap), np.minimum(np.abs(b.close-b.pdh), np.abs(b.close-b.pdl))) < 0.5*b.atr)
    asia = (b.hour < 8)
    return pd.DataFrame({"trend": trend, "vwap": vwap, "delta": delta, "level": near, "asia": asia}, index=b.index).astype(int)


def manage(O, H, L, C, a, i, s):
    """Enter at the open of bar i+1. Returns (ret, bars, how)."""
    e = O[i+1]; atr = a[i]; stop = e - s*1.5*atr; tp1 = e + s*1.0*atr
    rem, pnl, be, best = 1.0, 0.0, False, e
    pr = lambda px: s*(px/e - 1) - COST
    for j in range(i+1, min(i+25, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop):
            return pnl + rem*pr(stop), j-i, "be" if be else "stop"
        if not be and ((s == 1 and fav >= tp1) or (s == -1 and fav <= tp1)):
            pnl += 0.5*pr(tp1); rem = 0.5; be = True; stop = e*(1 + s*2*COST)
        if be:
            best = max(best, fav) if s == 1 else min(best, fav)
            t = best - s*1.5*atr
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+24, len(C)-1)
    return pnl + rem*pr(C[j]), j-i, "cap"


def run(B, variant, gap=6):
    rows, ctrl = [], []
    for sym, b in B.items():
        O, H, L, C, a = b.open.values, b.high.values, b.low.values, b.close.values, b.atr.values
        for s in (1, -1):
            sc = scores(b, s)
            if variant == "score>=4": sig = sc.sum(axis=1) >= 4
            elif variant == "score=5": sig = sc.sum(axis=1) == 5
            elif variant == "delta off (4 of other 4 >=3)": sig = sc[["trend","vwap","level","asia"]].sum(axis=1) >= 3
            elif variant == "delta only": sig = sc.delta == 1
            elif variant == "delta+trend": sig = (sc.delta == 1) & (sc.trend == 1)
            elif variant == "delta+trend+vwap": sig = (sc.delta == 1) & (sc.trend == 1) & (sc.vwap == 1)
            elif variant == "score>=4, any session": sig = sc[["trend","vwap","delta","level"]].sum(axis=1) >= 4
            elif variant == "score>=4, US session": sig = (sc[["trend","vwap","delta","level"]].sum(axis=1) >= 4) & (b.hour >= 13) & (b.hour < 21)
            idx = np.where(sig.values)[0]; idx = idx[(idx > 300) & (idx < len(C)-30)]
            last = -10**9
            for i in idx:
                if i - last < gap: continue
                last = i
                r, k, how = manage(O, H, L, C, a, i, s); rows.append((sym, s, b.index[i], r, k, how))
                for _ in range(3):
                    j = int(RNG.integers(300, len(C)-30)); r2, k2, _ = manage(O, H, L, C, a, j, s); ctrl.append((sym, s, b.index[j], r2, k2, ""))
    return (pd.DataFrame(rows, columns=["sym","side","ts","ret","bars","how"]),
            pd.DataFrame(ctrl, columns=["sym","side","ts","ret","bars","how"]))


def line(lbl, R, Cc):
    if len(R) < 80: print(f"  {lbl:<32}{len(R):>7} too few"); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    by = R.groupby("sym").ret.mean() - Cc.groupby("sym").ret.mean()
    gw = R.ret[R.ret > 0].sum(); gl = -R.ret[R.ret < 0].sum(); pf = gw/gl if gl > 0 else float("inf")
    print(f"  {lbl:<32}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{pf:>6.2f}{R.bars.median():>5.0f}"
          f"{Cc.ret.mean()*100:>+8.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>7.0f}%"
          f"{len(R)/((R.ts.max()-R.ts.min()).days or 1):>7.1f}", flush=True)


if __name__ == "__main__":
    syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{D1M}/*.csv")) if os.path.exists(f"{DOI}/{os.path.basename(f)[:-4]}.csv")]
    B = {}
    for s in syms:
        try: B[s] = features(load(s))
        except Exception as e: print("skip", s, e)
    n_bars = sum(len(b) for b in B.values())
    print(f"{len(B)} perps, 5-minute bars with taker imbalance, {n_bars:,} bars ({min(b.index.min() for b in B.values()).date()} to {max(b.index.max() for b in B.values()).date()}).")
    print("His management on every row: stop 1.5 ATR, half at +1 ATR then breakeven, trail 1.5 ATR, 2h cap. 3 random controls per trade.\n")
    print(f"  {'variant':<32}{'n':>7}{'per ep':>9}{'t':>6}{'win':>6}{'PF':>6}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>8}{'/day':>7}")
    for v in ("score>=4", "score=5", "delta off (4 of other 4 >=3)", "delta only", "delta+trend", "delta+trend+vwap", "score>=4, any session", "score>=4, US session"):
        R, Cc = run(B, v); line(v, R, Cc)
        if v == "score>=4":
            for s, lbl in ((1, "   longs"), (-1, "   shorts")): line(lbl, R[R.side == s], Cc[Cc.side == s])
            R["m"] = R.ts.dt.to_period("M"); Cc["m"] = Cc.ts.dt.to_period("M")
            print("   by month (real/ctrl %):", " ".join(f"{m}:{R[R.m==m].ret.mean()*100:+.2f}/{Cc[Cc.m==m].ret.mean()*100:+.2f}" for m in sorted(R.m.unique())))
            print("   exits:", R.how.value_counts().to_dict())
