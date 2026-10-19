"""Pass 3: NIGHT SELECTION and SESSION-OPEN breakouts on NQ, plus slower delta horizons."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import flow_nq as FN
from flow_nq import manage, race, line
from flow_nq2 import prep, run, hdr
RNG = np.random.default_rng(5)

if __name__ == "__main__":
    b = prep(); on = b.overnight
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values

    # ---- A. Night-level: does anything known at 22:00 predict how a simple overnight book does that night?
    print("A. NIGHT SELECTION — his-management trades at every 15th overnight minute, P&L per night vs features known at 22:00")
    idx = np.where(on.values)[0]; idx = idx[(idx > 1500) & (idx < len(C)-130)][::15]
    rows = []
    for i in idx:
        for s in (1, -1):
            r, k, how = manage(O, H, L, C, cost, i, s); rows.append((b.gday.iloc[i], s, r))
    R = pd.DataFrame(rows, columns=["gday", "side", "pts"])
    night = R.groupby("gday").pts.agg(["mean", "count"])
    # features of the PRIOR day (known at 22:00): range, close location, trend, realised vol, day-of-week
    dayg = b.groupby("gday").agg(hi=("high", "max"), lo=("low", "min"), cl=("close", "last"), op=("open", "first"), vol=("ret1", "std"), n=("close", "size"))
    dayg["rng"] = dayg.hi - dayg.lo; dayg["cloc"] = (dayg.cl - dayg.lo)/dayg.rng; dayg["ret"] = dayg.cl/dayg.op - 1
    f = dayg.shift(1).reindex(night.index)
    f["dow"] = pd.to_datetime(night.index).dayofweek
    night = night.join(f)
    print(f"   {len(night)} nights; mean night P&L {night['mean'].mean():+.2f} pts/trade, SD across nights {night['mean'].std():.2f}, nights >0: {(night['mean']>0).mean()*100:.0f}%")
    for col in ("rng", "cloc", "ret", "vol"):
        q = pd.qcut(night[col], 3, labels=["low", "mid", "high"])
        g = night.groupby(q)["mean"].agg(["mean", "count"])
        print(f"   prior-day {col:<5}: " + "  ".join(f"{k} {v['mean']:+.2f} (n={int(v['count'])})" for k, v in g.iterrows()))
    g = night.groupby("dow")["mean"].mean(); print("   by weekday (Mon=0):", " ".join(f"{k}:{v:+.2f}" for k, v in g.items()))
    # night autocorrelation: a good night followed by a good night?
    print(f"   night-to-night autocorr of P&L: {night['mean'].autocorr():+.2f}")

    # ---- B. Session-open breakouts
    print("\nB. SESSION-OPEN BREAKOUTS — opening range (first 30 min) break with his management"); hdr()
    def orb(open_h, s_, win=30):
        hh = b.hour.values; out = np.zeros(len(b), bool)
        # opening range high/low from open_h to open_h+win min, then first break within next 3h
        for gd, grp in b.groupby(b.gday):
            ii = grp.index; hrs = grp.hour.values
            m = (hrs >= open_h) & (hrs < open_h + win/60)
            if m.sum() < 10: continue
            orh, orl = grp.high[m].max(), grp.low[m].min()
            after = (hrs >= open_h + win/60) & (hrs < open_h + 3)
            pos = b.index.get_indexer(ii[after])
            brk = (grp.close[after] > orh).values if s_ == 1 else (grp.close[after] < orl).values
            if brk.any(): out[pos[np.argmax(brk)]] = True
        return pd.Series(out, index=b.index)
    for oh, nm in ((22, "Globex 22:00"), (7, "London 07:00"), (13.5, "pre-cash 13:30"), (0, "Asia 00:00")):
        R, Cc = run(b, lambda b_, s, oh=oh: orb(oh, s), gap=1); line(f"ORB {nm} (first break, 30m range)", R, Cc)
        R, Cc = run(b, lambda b_, s, oh=oh: orb(oh, s) & ((b_.dz > 1) if s == 1 else (b_.dz < -1)), gap=1); line(f"  + delta confirms", R, Cc)
        R, Cc = run(b, lambda b_, s, oh=oh: orb(oh, -s), gap=1); line(f"  FADE the break", R, Cc)

    # ---- C. Slower delta horizons, overnight
    print("\nC. SLOWER DELTA — 60-min and 180-min delta z, go with / fade, overnight"); hdr()
    for w in (60, 180):
        d = b.delta.rolling(w).sum(); z = (d - d.rolling(1440).mean())/d.rolling(1440).std(); b[f"dz{w}"] = z
        R, Cc = run(b, lambda b_, s, w=w: on & ((b_[f"dz{w}"] > 1.5) if s == 1 else (b_[f"dz{w}"] < -1.5)), gap=30); line(f"delta{w} z>1.5 go-with", R, Cc)
        R, Cc = run(b, lambda b_, s, w=w: on & ((b_[f"dz{w}"] < -1.5) if s == 1 else (b_[f"dz{w}"] > 1.5)), gap=30); line(f"delta{w} z>1.5 FADE", R, Cc)
    # absorption, 15m, both sessions and stricter
    R, Cc = run(b, lambda b_, s: ((b_.dz < -1.5) & (b_.close - b_.close.shift(15) > -5)) if s == 1 else ((b_.dz > 1.5) & (b_.close - b_.close.shift(15) < 5))); line("absorption 15m, ANY session", R, Cc)
    R, Cc = run(b, lambda b_, s: on & (((b_.dz < -2.0) & (b_.close - b_.close.shift(15) > 0)) if s == 1 else ((b_.dz > 2.0) & (b_.close - b_.close.shift(15) < 0)))); line("absorption 15m, z>2, price flat/against", R, Cc)
    R, Cc = run(b, lambda b_, s: on & (((b_.dz < -1.5) & (b_.close - b_.close.shift(15) > -5)) if s == 1 else ((b_.dz > 1.5) & (b_.close - b_.close.shift(15) < 5))), gap=30); line("absorption 15m, overnight, gap 30", R, Cc)
    R["m"] = R.ts.dt.to_period("M") if len(R) else None
    if len(R): print("   absorption by month:", " ".join(f"{m}:{R[R.m==m].pts.mean():+.1f}({int((R.m==m).sum())})" for m in sorted(R.m.unique())))
