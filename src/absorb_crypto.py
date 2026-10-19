"""
ABSORPTION WITH TRUE AGGRESSOR DELTA — crypto (DK, 19 Oct: "Try the free alternative first").

Doc 87's one lead on NQ: heavy delta while price does not move -> trade AGAINST the pressure
(sellers hitting a bid that holds = long). On NQ the delta was a tick-rule proxy with zero size
data. Here delta = 2*taker_buy - volume per 1-minute bar from Binance klines: the real
aggressor side. 18 perps, 2025-09 .. 2026-10.

Features (1-minute bars, aggregated to the 5- and 15-minute windows):
  dz      windowed delta (in units of volume) z-scored vs the trailing 24h
  move    price change over the same window, in ATR(1h) units
  ABSORPTION long:  dz < -Z  and move > -M   (heavy selling, price held)
  ABSORPTION short: dz > +Z  and move < +M
  (CONTROL READS: go-with, i.e. dz > +Z buy; and the same with price confirming)
Management: AuclairsDad's, in ATR units as doc 84 (stop 1.5 ATR, half at +1 ATR -> BE, trail 1.5,
cap 120 min), cost 4.5bp per side. Also exit-free: barrier race +-1 ATR within 2h.
Matched random control: same coin, random bar, same side, same management, 3 per trade.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
COST = 4.5/10000; RNG = np.random.default_rng(3)
D = "/home/claude/qlab/data_1m_delta"
STOP, TP1, TRAIL, CAP = 1.5, 1.0, 1.5, 120


def load(c):
    d = pd.read_csv(f"{D}/{c}.csv"); d.index = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d[["open", "high", "low", "close", "vol", "delta"]]
    d = d[~d.index.duplicated()].asfreq("1min")
    d[["open","high","low","close"]] = d[["open","high","low","close"]].ffill(); d[["vol","delta"]] = d[["vol","delta"]].fillna(0)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    b15 = d[["high","low","close"]].resample("15min").agg({"high":"max","low":"min","close":"last"})
    tr15 = np.maximum(b15.high - b15.low, np.maximum((b15.high - b15.close.shift()).abs(), (b15.low - b15.close.shift()).abs()))
    d["atr"] = tr15.rolling(14).mean().shift(1).reindex(d.index, method="ffill")   # ATR14 on completed 15-min bars, as doc 84
    for w in (5, 15, 60):
        dw = d.delta.rolling(w).sum()
        d[f"dz{w}"] = (dw - dw.rolling(1440).mean())/dw.rolling(1440).std()
        d[f"mv{w}"] = (d.close - d.close.shift(w))/d.atr
    d["hour"] = d.index.hour
    return d.dropna()


def manage(O, H, L, C, a, i, s):
    e = O[i+1]; atr = a[i]; stop = e - s*STOP*atr; tp1 = e + s*TP1*atr
    rem, pnl, be, best = 1.0, 0.0, False, e
    pr = lambda px: s*(px/e - 1) - COST
    for j in range(i+1, min(i+CAP+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pnl + rem*pr(stop), j-i, "be" if be else "stop"
        if not be and ((s == 1 and fav >= tp1) or (s == -1 and fav <= tp1)):
            pnl += 0.5*pr(tp1); rem = 0.5; be = True; stop = e*(1 + s*2*COST)
        if be:
            best = max(best, fav) if s == 1 else min(best, fav)
            t = best - s*TRAIL*atr
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+CAP, len(C)-1); return pnl + rem*pr(C[j]), j-i, "cap"


def race(H, L, C, a, i, s, k=1.0, horizon=120):
    e = C[i]; up_ = e + s*k*a[i]; dn_ = e - s*k*a[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= up_) if s == 1 else (L[j] <= up_); dn = (L[j] <= dn_) if s == 1 else (H[j] >= dn_)
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan


def run(B, sig_fn, gap=15, nctrl=3):
    rows, ctrl = [], []
    for c, b in B.items():
        O, H, L, C, a = b.open.values, b.high.values, b.low.values, b.close.values, b.atr.values
        for s in (1, -1):
            sig = sig_fn(b, s).values; idx = np.where(sig)[0]; idx = idx[(idx > 1500) & (idx < len(C)-130)]; last = -10**9
            for i in idx:
                if i - last < gap: continue
                last = i
                r, k, how = manage(O, H, L, C, a, i, s); rows.append((c, s, b.index[i], r, k, how, race(H, L, C, a, i, s)))
                for _ in range(nctrl):
                    j = int(RNG.integers(1500, len(C)-130)); r2, k2, _ = manage(O, H, L, C, a, j, s); ctrl.append((c, s, b.index[j], r2, k2, "", race(H, L, C, a, j, s)))
    cols = ["sym","side","ts","ret","bars","how","race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


def line(lbl, R, Cc):
    if len(R) < 80: print(f"  {lbl:<40}{len(R):>7} too few"); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    by = R.groupby("sym").ret.mean() - Cc.groupby("sym").ret.mean()
    gw = R.ret[R.ret > 0].sum(); gl = -R.ret[R.ret < 0].sum(); pf = gw/gl if gl > 0 else float("inf")
    print(f"  {lbl:<40}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{pf:>6.2f}{R.bars.median():>5.0f}"
          f"{Cc.ret.mean()*100:>+8.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>6.0f}%{R.race.mean()*100:>6.0f}%{Cc.race.mean()*100:>5.0f}%", flush=True)


def hdr(): print(f"  {'variant':<40}{'n':>7}{'per ep':>9}{'t':>6}{'win':>6}{'PF':>6}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>7}{'race':>6}{'ctrl':>5}")


if __name__ == "__main__":
    B = {os.path.basename(f)[:-4]: load(f"{os.path.basename(f)[:-4]}") for f in sorted(glob.glob(f"{D}/*.csv"))}
    print(f"{len(B)} perps, 1-minute bars with true taker delta, {sum(len(b) for b in B.values()):,} bars, {min(b.index.min() for b in B.values()).date()} .. {max(b.index.max() for b in B.values()).date()}")
    print("Management: stop 1.5 ATR14(15m), half at +1 ATR -> BE, trail 1.5 ATR, 2h cap, 4.5bp/side. 3 random controls per trade.\n")
    # sanity: does true delta carry contemporaneous and forward information at all?
    for w in (5, 15, 60):
        cc = np.mean([np.corrcoef(b[f"dz{w}"], b[f"mv{w}"])[0, 1] for b in B.values()])
        fw = np.mean([np.corrcoef(b[f"dz{w}"][:-w], (b.close.shift(-w) - b.close).values[:-w]/b.atr.values[:-w])[0, 1] for b in B.values()])
        print(f"  delta{w}: corr with same-window move {cc:+.3f}; corr with NEXT {w}-min move {fw:+.4f}")
    print()
    hdr()
    V = {}
    for w in (5, 15, 60):
        for Z, M in ((1.5, 0.25), (2.0, 0.25), (2.0, 0.0), (3.0, 0.5)):
            V[f"ABSORB {w}m: |dz|>{Z}, |move|<{M} ATR"] = (lambda b, s, w=w, Z=Z, M=M: ((b[f"dz{w}"] < -Z) & (b[f"mv{w}"] > -M)) if s == 1 else ((b[f"dz{w}"] > Z) & (b[f"mv{w}"] < M)))
        V[f"go-with {w}m: dz>{2.0}"] = (lambda b, s, w=w: (b[f"dz{w}"] > 2.0) if s == 1 else (b[f"dz{w}"] < -2.0))
        V[f"go-with {w}m + price confirms"] = (lambda b, s, w=w: ((b[f"dz{w}"] > 2.0) & (b[f"mv{w}"] > 0.5)) if s == 1 else ((b[f"dz{w}"] < -2.0) & (b[f"mv{w}"] < -0.5)))
        V[f"exhaustion {w}m: dz>2 AND move>1 ATR, FADE"] = (lambda b, s, w=w: ((b[f"dz{w}"] < -2.0) & (b[f"mv{w}"] < -1.0)) if s == 1 else ((b[f"dz{w}"] > 2.0) & (b[f"mv{w}"] > 1.0)))
    best = None
    for name, fn in V.items():
        R, Cc = run(B, fn); line(name, R, Cc)
        if name.startswith("ABSORB 15m: |dz|>2.0, |move|<0.25"): best = (R, Cc)
    if best is not None and len(best[0]):
        R, Cc = best; R["m"] = R.ts.dt.to_period("M"); Cc["m"] = Cc.ts.dt.to_period("M")
        print("\n  ABSORB 15m z>2 by month (real/ctrl %):", " ".join(f"{m}:{R[R.m==m].ret.mean()*100:+.2f}/{Cc[Cc.m==m].ret.mean()*100:+.2f}" for m in sorted(R.m.unique())))
        for s, lbl in ((1, "   longs"), (-1, "   shorts")): line(lbl, R[R.side == s], Cc[Cc.side == s])
        asia = R[R.ts.dt.hour < 8]; line("   Asia 00-08 UTC", asia, Cc[Cc.ts.dt.hour < 8])
        print("   exits:", R.how.value_counts().to_dict())
