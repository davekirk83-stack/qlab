"""
AUCLAIRSDAD ON HIS OWN MARKET — Nasdaq-100 (Dukascopy USATECHIDXUSD ticks -> 1-minute),
his three-month window, 2026-07-15 .. 2026-10-17. DK, 19 Oct: "Why did you apply his
method to coins and not to his actual markets?"

His engine as observable (doc 84): a score over HTF fast EMA direction, VWAP side,
drawn levels, the overnight Globex session and ORDER-FLOW DELTA, with a ~50-point
stop, 20-35-point targets and a trail. Delta here = tick rule (uptick buy / downtick
sell), the standard stand-in when aggressor side is not recorded.

In NQ points (his units):
  trend    15-minute EMA20 vs EMA50 (completed bar), the "HTF fast EMA"
  vwap     close vs the session VWAP (tick-count weighted; Dukascopy has no volume),
           session = 22:00 UTC to 22:00 UTC (the Globex day, 6pm ET in summer)
  delta    15-minute tick-rule delta z-score (vs the trailing 24h) > 1.5
  level    within 10 points of the prior-day high/low, the overnight high/low or VWAP
  session  overnight: 22:00-13:30 UTC (6pm-9:30am ET, summer)
Trade at score >= 4; also delta-only, delta-off, day-session, and the raw ingredients
exit-free (barrier race). MANAGEMENT (his): stop 50 pts; TP1 +20 pts takes half and
moves the stop to breakeven; the rest trails 30 pts; cap 120 minutes. Cost: half the
quoted spread each way (CFD mid; the NQ future's cost is ~0.25-0.5 pt + commission,
so this is if anything generous). Random control with identical management, 5 per trade.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
RNG = np.random.default_rng(7)
F = "/home/claude/qlab/data_nq/nq_1m.csv"
STOP, TP1, TRAIL, CAP = 50.0, 20.0, 30.0, 120


def features():
    b = pd.read_csv(F, index_col=0); b.index = pd.to_datetime(b.index, utc=True)
    b = b[b.n_ticks > 0].copy()
    c15 = b.close.resample("15min").last().dropna()
    ef = c15.ewm(span=20, adjust=False).mean(); es = c15.ewm(span=50, adjust=False).mean()
    b["trend"] = (ef > es).astype(int).shift(1).reindex(b.index, method="ffill").values
    gday = (b.index - pd.Timedelta(hours=22)).floor("D")           # Globex day starts 22:00 UTC
    b["gday"] = gday
    b["vwap"] = (b.close*b.n_ticks).groupby(gday).cumsum()/b.n_ticks.groupby(gday).cumsum()
    d15 = b.delta.rolling(15).sum()
    b["dz"] = (d15 - d15.rolling(1440).mean())/d15.rolling(1440).std()
    pdh = b.high.groupby(gday).max().shift(1); pdl = b.low.groupby(gday).min().shift(1)
    b["pdh"] = pdh.reindex(gday).values; b["pdl"] = pdl.reindex(gday).values
    onh = b.high.groupby(gday).cummax(); onl = b.low.groupby(gday).cummin()
    b["onh"] = onh.shift(1).values; b["onl"] = onl.shift(1).values
    b["hour"] = b.index.hour + b.index.minute/60
    b["overnight"] = (b.hour >= 22) | (b.hour < 13.5)
    b["cost"] = b.spread/2
    return b.dropna()


def scores(b, s):
    trend = (b.trend == 1) if s == 1 else (b.trend == 0)
    vwap = (b.close > b.vwap) if s == 1 else (b.close < b.vwap)
    delta = (b.dz > 1.5) if s == 1 else (b.dz < -1.5)
    lv = np.minimum.reduce([np.abs(b.close-b.vwap), np.abs(b.close-b.pdh), np.abs(b.close-b.pdl), np.abs(b.close-b.onh), np.abs(b.close-b.onl)])
    level = lv < 10
    return pd.DataFrame({"trend": trend, "vwap": vwap, "delta": delta, "level": level, "overnight": b.overnight}, index=b.index).astype(int)


def manage(O, H, L, C, cost, i, s):
    e = O[i+1] + s*cost[i+1]; stop = e - s*STOP; tp1 = e + s*TP1
    rem, pnl, be, best = 1.0, 0.0, False, e
    pts = lambda px: s*(px - e) - cost[i+1]
    for j in range(i+1, min(i+CAP+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pnl + rem*pts(stop), j-i, "be" if be else "stop"
        if not be and ((s == 1 and fav >= tp1) or (s == -1 and fav <= tp1)):
            pnl += 0.5*pts(tp1); rem = 0.5; be = True; stop = e + s*cost[i+1]*2
        if be:
            best = max(best, fav) if s == 1 else min(best, fav)
            t = best - s*TRAIL
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+CAP, len(C)-1); return pnl + rem*pts(C[j]), j-i, "cap"


def race(H, L, C, i, s, k=30, horizon=120):
    e = C[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= e+k) if s == 1 else (L[j] <= e-k); dn = (L[j] <= e-k) if s == 1 else (H[j] >= e+k)
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan


def run(b, sig_fn, gap=10, nctrl=5):
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    rows, ctrl = [], []
    for s in (1, -1):
        sc = scores(b, s); sig = sig_fn(sc, b, s).values
        idx = np.where(sig)[0]; idx = idx[(idx > 1500) & (idx < len(C)-130)]; last = -10**9
        for i in idx:
            if i - last < gap: continue
            last = i
            r, k, how = manage(O, H, L, C, cost, i, s); rows.append((s, b.index[i], r, k, how, race(H, L, C, i, s)))
            for _ in range(nctrl):
                j = int(RNG.integers(1500, len(C)-130))
                if sig_fn.__name__ == "overnight_ctrl" or True:
                    pass
                r2, k2, _ = manage(O, H, L, C, cost, j, s); ctrl.append((s, b.index[j], r2, k2, "", race(H, L, C, j, s)))
    return (pd.DataFrame(rows, columns=["side","ts","pts","bars","how","race"]), pd.DataFrame(ctrl, columns=["side","ts","pts","bars","how","race"]))


def line(lbl, R, Cc):
    if len(R) < 30: print(f"  {lbl:<34}{len(R):>6} too few"); return
    t = R.pts.mean()/(R.pts.std(ddof=1)/np.sqrt(len(R)))
    gw = R.pts[R.pts > 0].sum(); gl = -R.pts[R.pts < 0].sum(); pf = gw/gl if gl > 0 else float("inf")
    days = (R.ts.max()-R.ts.min()).days or 1
    print(f"  {lbl:<34}{len(R):>6,}{R.pts.mean():>+8.2f}{t:>+6.1f}{(R.pts>0).mean()*100:>5.0f}%{pf:>6.2f}{R.bars.median():>5.0f}"
          f"{Cc.pts.mean():>+8.2f}{(R.pts.mean()-Cc.pts.mean()):>+7.2f}{R.race.mean()*100:>6.0f}%{Cc.race.mean()*100:>5.0f}%"
          f"{R.pts.sum()/days*30:>9.0f}", flush=True)


if __name__ == "__main__":
    b = features()
    print(f"Nasdaq-100 CFD ticks -> 1-minute, {b.index.min().date()} .. {b.index.max().date()}, {len(b):,} minutes, median spread {b.spread.median():.2f} pts.")
    print("His management on every row: stop 50, half at +20 then breakeven, trail 30, 2h cap. 5 random controls per trade. Points per trade.\n")
    print(f"  {'variant':<34}{'n':>6}{'pts/tr':>8}{'t':>6}{'win':>6}{'PF':>6}{'hold':>5}{'ctrl':>8}{'edge':>7}{'race':>6}{'ctrl':>5}{'pts/month':>10}")
    V = {
        "score>=4 (his book)": lambda sc, b, s: sc.sum(axis=1) >= 4,
        "score=5": lambda sc, b, s: sc.sum(axis=1) == 5,
        "delta off (other 4 >= 3)": lambda sc, b, s: sc[["trend","vwap","level","overnight"]].sum(axis=1) >= 3,
        "delta only, overnight": lambda sc, b, s: (sc.delta == 1) & (sc.overnight == 1),
        "delta + trend, overnight": lambda sc, b, s: (sc.delta == 1) & (sc.trend == 1) & (sc.overnight == 1),
        "delta + trend + vwap, overnight": lambda sc, b, s: (sc.delta == 1) & (sc.trend == 1) & (sc.vwap == 1) & (sc.overnight == 1),
        "trend + vwap + level, overnight": lambda sc, b, s: (sc.trend == 1) & (sc.vwap == 1) & (sc.level == 1) & (sc.overnight == 1),
        "score>=4 of 4, DAY session": lambda sc, b, s: (sc[["trend","vwap","delta","level"]].sum(axis=1) >= 4) & (sc.overnight == 0),
        "delta z>2.5, overnight": lambda sc, b, s: ((b.dz*s) > 2.5) & (sc.overnight == 1),
        "delta z>2.5 AGAINST trend (fade)": lambda sc, b, s: ((b.dz*s) > 2.5) & (sc.trend == 0) & (sc.overnight == 1),
    }
    for name, fn in V.items():
        R, Cc = run(b, fn); line(name, R, Cc)
        if name == "score>=4 (his book)":
            for s, lbl in ((1, "   longs"), (-1, "   shorts")): line(lbl, R[R.side == s], Cc[Cc.side == s])
            R["m"] = R.ts.dt.to_period("M")
            print("   by month (pts/trade, n):", " ".join(f"{m}:{R[R.m==m].pts.mean():+.1f}({int((R.m==m).sum())})" for m in sorted(R.m.unique())))
            print("   exits:", R.how.value_counts().to_dict())
