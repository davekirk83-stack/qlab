"""
COIL IGNITION — AuclairsDad's engine as read off his own Sierra panel (DK's screenshots, 19 Oct 14:18),
on 5-MINUTE bars, all sessions. One engine for NQ (Dukascopy minutes: n_ticks as activity, tick-rule
delta) and for the 18 crypto perps (Binance 1-minute with TRUE taker delta — the same bar-level
bid/ask resolution his Sierra feed gives him).

Gates (his inputs, his thresholds where shown):
  COIL        20-bar range / ATR(20)  <= 4.0                      ("Coil 3.51 / 4.00 [COILED]")
  IGNITION    this bar's range / avg range(20) >= 1.25             ("Expansion 1.39 / 1.25 [IGNITED]")
  DELTA SHARE |bar delta| / bar volume >= 0.05, sign = direction   ("Delta Share -0.018 (need 0.05)")
  HTF         EMA20 vs EMA50 on the 5-min bars, direction must agree ("HTF: BEARISH (on)")
  RAW CONVICTION path: delta ratio buy/sell >= 1.19 with HTF agreement, no coil needed
  (efficiency and range-expansion gates: shown OFF on his panel; included as ablations)
Governors: max 8 trades/day, cooloff 3 bars, daily loss cap 200 pts (= his $4,000), forced flat none.
Exit (his): hard stop; breakeven ratchet; profit target 9 x ATR with a trail (so winners run ~40 pts).
  NQ: stop 45 pts (his largest loss $870 ≈ 43 pts), BE at +15, trail 1.0 ATR, target 9 ATR, cap 36 bars (3h)
  crypto: in ATR units: stop 1.5 ATR, BE +0.5 ATR, trail 1.0 ATR, target 9 ATR, cap 36 bars
Costs: NQ half-spread each way (CFD, ~1.4 pt round trip; his future ~0.5); crypto 4.5bp taker each way.
Controls: 5 random bars per trade, same side, same exit stack; exit-free race ±1 ATR; by month; split-half.
"""
import warnings; warnings.filterwarnings("ignore")
import sys, os, glob
import numpy as np, pandas as pd
RNG = np.random.default_rng(23)
COIL, IGN, DSHARE, CONV = 4.0, 1.25, 0.05, 1.19


def bars5_nq(F):
    b = pd.read_csv(F, index_col=0); b.index = pd.to_datetime(b.index, utc=True); b = b[b.n_ticks > 0]
    d = b.resample("5min").agg(open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"),
                               vol=("n_ticks","sum"), delta=("delta","sum"), spread=("spread","mean")).dropna(subset=["close"])
    d["cost"] = d.spread/2; d["unit"] = 1.0
    return d


def bars5_crypto(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.t, unit="ms", utc=True); d = d[["open","high","low","close","vol","delta"]]
    d = d[~d.index.duplicated()].resample("5min").agg(open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"), vol=("vol","sum"), delta=("delta","sum")).dropna(subset=["close"])
    d["cost"] = 4.5e-4*d.close; d["unit"] = np.nan                    # unit set to ATR later (exit stack in ATR units)
    return d


def features(d):
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    d["atr"] = tr.rolling(20).mean().shift(1)
    d["rng"] = d.high - d.low
    d["coil"] = (d.high.shift(1).rolling(20).max() - d.low.shift(1).rolling(20).min())/d.atr
    d["ign"] = d.rng/d.rng.shift(1).rolling(20).mean()
    d["dshare"] = d.delta/d.vol.replace(0, np.nan)
    buy = (d.vol + d.delta)/2; sell = (d.vol - d.delta)/2; d["dratio"] = buy/sell.replace(0, np.nan)
    d["ef"] = d.close.ewm(span=20, adjust=False).mean(); d["es"] = d.close.ewm(span=50, adjust=False).mean()
    d["htf"] = np.sign(d.ef - d.es).shift(1)
    d["eff"] = (d.close - d.close.shift(10)).abs()/d.rng.rolling(10).sum()     # efficiency ratio (his, shown OFF)
    d["brk_up"] = d.close > d.high.shift(1).rolling(20).max(); d["brk_dn"] = d.close < d.low.shift(1).rolling(20).min()
    d["day"] = d.index.floor("D")
    return d.dropna(subset=["atr", "coil", "ign", "htf"])


def manage(O, H, L, C, cost, u, i, s, stop_u, be_u, trail_u, tgt_u, cap):
    e = O[i+1] + s*cost[i+1]; U = u[i]; stop = e - s*stop_u*U; tgt = e + s*tgt_u*U; best = e; be = False
    pts = lambda px: (s*(px - e) - cost[i+1])/U
    for j in range(i+1, min(i+cap+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pts(stop), j-i, "be" if be else "stop"
        if (s == 1 and fav >= tgt) or (s == -1 and fav <= tgt): return pts(tgt), j-i, "tgt"
        best = max(best, fav) if s == 1 else min(best, fav)
        if not be and s*(best - e) >= be_u*U: be = True; stop = e + s*cost[i+1]*2
        if be:
            t = best - s*trail_u*U
            if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+cap, len(C)-1); return pts(C[j]), j-i, "cap"


def race(H, L, C, u, i, s, k=1.0, horizon=36):
    e = C[i]; U = u[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= e + s*k*U) if s == 1 else (L[j] <= e + s*k*U); dn = (L[j] <= e - s*k*U) if s == 1 else (H[j] >= e - s*k*U)
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan


def run(D, sigfn, ex, nctrl=5, max_trades=8, cooloff=3, loss_cap_u=None):
    rows, ctrl = [], []
    for sym, d in D.items():
        O, H, L, C, cost, u = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values, d.unit.values
        su, sd = sigfn(d); su, sd = su.values, sd.values; day = d.day.values
        last_exit = -10**9; cur = None; ntr = 0; dpl = 0.0
        for i in range(300, len(C)-ex["cap"]-2):
            if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0.0
            s = 1 if su[i] else (-1 if sd[i] else 0)
            if s == 0 or i < last_exit + cooloff or ntr >= max_trades or (loss_cap_u and dpl <= -loss_cap_u): continue
            r, k, how = manage(O, H, L, C, cost, u, i, s, ex["stop"], ex["be"], ex["trail"], ex["tgt"], ex["cap"])
            rows.append((sym, s, d.index[i], r, k, how, race(H, L, C, u, i, s))); last_exit = i + k; ntr += 1; dpl += r
            for _ in range(nctrl):
                j = int(RNG.integers(300, len(C)-ex["cap"]-2)); r2, k2, _ = manage(O, H, L, C, cost, u, j, s, ex["stop"], ex["be"], ex["trail"], ex["tgt"], ex["cap"])
                ctrl.append((sym, s, d.index[j], r2, k2, "", race(H, L, C, u, j, s)))
    cols = ["sym","side","ts","ret","bars","how","race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


def line(lbl, R, Cc, unit="pts"):
    if len(R) < 40: print(f"  {lbl:<48}{len(R):>6} too few", flush=True); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    gw = R.ret[R.ret > 0].sum(); gl = -R.ret[R.ret < 0].sum(); pf = gw/gl if gl > 0 else float("inf")
    days = max((R.ts.max()-R.ts.min()).days, 1); nsym = R.sym.nunique()
    m = R.ts.dt.to_period("M"); mon = (R.groupby(m).ret.mean() > 0).mean()*100
    h = len(R)//2; Rs = R.sort_values("ts")
    print(f"  {lbl:<48}{len(R):>6,}{R.ret.mean():>+8.3f}{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{pf:>6.2f}{R.ret[R.ret>0].mean():>+7.2f}{R.ret[R.ret<0].mean():>+7.2f}{R.bars.median():>5.0f}"
          f"{Cc.ret.mean():>+8.3f}{(R.ret.mean()-Cc.ret.mean()):>+7.3f}{R.race.mean()*100:>6.0f}%{Cc.race.mean()*100:>5.0f}%{mon:>5.0f}%{Rs.ret.iloc[:h].mean():>+7.2f}{Rs.ret.iloc[h:].mean():>+7.2f}{len(R)/days/nsym:>6.2f}", flush=True)


def hdr(): print(f"  {'variant':<48}{'n':>6}{'per tr':>8}{'t':>6}{'win':>6}{'PF':>6}{'avgW':>7}{'avgL':>7}{'hold':>5}{'ctrl':>8}{'edge':>7}{'race':>6}{'ctrl':>5}{'mo>0':>6}{'half1':>7}{'half2':>7}{'/d/sym':>7}")


def variants(d):
    coil = d.coil <= COIL; ign = d.ign >= IGN
    up = (d.dshare >= DSHARE) & (d.close > d.open); dn = (d.dshare <= -DSHARE) & (d.close < d.open)
    hu, hd = d.htf == 1, d.htf == -1
    cu, cd = d.dratio >= CONV, d.dratio <= 1/CONV
    return {
        "COIL IGNITION: coil + ign + delta share + HTF": (coil & ign & up & hu, coil & ign & dn & hd),
        "  + channel break (structure)": (coil & ign & up & hu & d.brk_up, coil & ign & dn & hd & d.brk_dn),
        "  without HTF (both ways)": (coil & ign & up, coil & ign & dn),
        "  without delta share": (coil & ign & (d.close > d.open) & hu, coil & ign & (d.close < d.open) & hd),
        "  without coil (ignition + delta + HTF)": (ign & up & hu, ign & dn & hd),
        "  COUNTER-HTF (fade the ignition)": (coil & ign & up & hd, coil & ign & dn & hu),
        "  + efficiency >= 0.4 (his OFF gate)": (coil & ign & up & hu & (d.eff >= 0.4), coil & ign & dn & hd & (d.eff >= 0.4)),
        "RAW CONVICTION: delta ratio 1.19 + HTF": (cu & hu & (d.close > d.open), cd & hd & (d.close < d.open)),
        "  raw conviction + ignition": (cu & hu & ign & (d.close > d.open), cd & hd & ign & (d.close < d.open)),
        "HTF + candle only (control read)": (hu & (d.close > d.open), hd & (d.close < d.open)),
    }


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "nq"
    if which == "nq":
        F = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/qlab/data_nq/nq_1m.csv"
        d = features(bars5_nq(F)); D = {"NQ": d}
        EX = dict(stop=45.0, be=15.0, trail=None, tgt=None, cap=36); EX["trail"] = 1.0; EX["tgt"] = 9.0
        # NQ exits: stop/be in points (unit=1), trail/target in ATR -> convert per bar by passing unit=1 and scaling trail/tgt by atr
        d["unit"] = 1.0
        # express trail and target in points using the bar ATR at entry: handled by a wrapper below
        atr = d.atr.values
        def run_nq(sigfn, nctrl=5, loss_cap=200.0):
            rows, ctrl = [], []
            O, H, L, C, cost = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values
            su, sd = sigfn(d); su, sd = su.values, sd.values; day = d.day.values
            last_exit = -10**9; cur = None; ntr = 0; dpl = 0.0
            for i in range(300, len(C)-40):
                if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0.0
                s = 1 if su[i] else (-1 if sd[i] else 0)
                if s == 0 or i < last_exit + 3 or ntr >= 8 or dpl <= -loss_cap: continue
                u = np.ones(len(C)); r, k, how = manage(O, H, L, C, cost, u, i, s, 45.0, 15.0, 1.0*atr[i], 9.0*atr[i], 36)
                rows.append(("NQ", s, d.index[i], r, k, how, race(H, L, C, atr, i, s))); last_exit = i + k; ntr += 1; dpl += r
                for _ in range(nctrl):
                    j = int(RNG.integers(300, len(C)-40)); r2, k2, _ = manage(O, H, L, C, cost, u, j, s, 45.0, 15.0, 1.0*atr[j], 9.0*atr[j], 36)
                    ctrl.append(("NQ", s, d.index[j], r2, k2, "", race(H, L, C, atr, j, s)))
            cols = ["sym","side","ts","ret","bars","how","race"]
            return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)
        print(f"NQ 5-minute {d.index.min().date()}..{d.index.max().date()}, {len(d):,} bars, median ATR {d.atr.median():.1f} pts, cost {d.cost.median()*2:.2f} pts round trip (CFD; his future ~0.5). Exit: stop 45 / BE +15 / trail 1 ATR / target 9 ATR / cap 3h. Points per trade.\n"); hdr()
        for name, fn in variants(d).items():
            R, Cc = run_nq(lambda d_, fn=fn: fn); line(name, R, Cc)
            if name.startswith("COIL IGNITION"):
                print(f"     exits {R.how.value_counts().to_dict()}; longs {R[R.side==1].ret.mean():+.2f} (n={int((R.side==1).sum())}) shorts {R[R.side==-1].ret.mean():+.2f} (n={int((R.side==-1).sum())})")
                R["h"] = R.ts.dt.hour; on = R[(R.h >= 22) | (R.h < 13)]; rth = R[(R.h >= 13) & (R.h < 21)]
                print(f"     overnight {on.ret.mean():+.2f} (n={len(on)}, win {(on.ret>0).mean()*100:.0f}%)  RTH {rth.ret.mean():+.2f} (n={len(rth)}, win {(rth.ret>0).mean()*100:.0f}%)")
                m = R.ts.dt.to_period("M"); print("     by month:", " ".join(f"{k}:{v:+.1f}({int((m==k).sum())})" for k, v in R.groupby(m).ret.mean().items()))
                print(f"     at his futures cost (0.5 pt round trip instead of {d.cost.median()*2:.2f}): {R.ret.mean() + d.cost.median()*2 - 0.5:+.2f} pts/trade")
    else:
        D = {}
        for f in sorted(glob.glob("/home/claude/qlab/data_1m_delta/*.csv")):
            dd = features(bars5_crypto(f)); dd["unit"] = dd.atr; D[os.path.basename(f)[:-4]] = dd.dropna(subset=["unit"])
        EX = dict(stop=1.5, be=0.5, trail=1.0, tgt=9.0, cap=36)
        print(f"{len(D)} perps, 5-minute bars with TRUE taker delta, {sum(len(x) for x in D.values()):,} bars. Exit in ATR units: stop 1.5 / BE +0.5 / trail 1 / target 9 / cap 3h; 4.5bp per side. Returns in ATR units per trade.\n"); hdr()
        for name, fn in variants(next(iter(D.values()))).items():
            R, Cc = run(D, lambda d_, name=name: variants(d_)[name], EX); line(name, R, Cc)
            if name.startswith("COIL IGNITION"):
                print(f"     exits {R.how.value_counts().to_dict()}; longs {R[R.side==1].ret.mean():+.3f} (n={int((R.side==1).sum())}) shorts {R[R.side==-1].ret.mean():+.3f} (n={int((R.side==-1).sum())}); coins >0: {(R.groupby('sym').ret.mean()>0).mean()*100:.0f}%")
                R["h"] = R.ts.dt.hour; asia = R[R.h < 8]; us = R[(R.h >= 13) & (R.h < 21)]
                print(f"     Asia {asia.ret.mean():+.3f} (n={len(asia)})  US {us.ret.mean():+.3f} (n={len(us)})")
                m = R.ts.dt.to_period("M"); print("     by month:", " ".join(f"{k}:{v:+.2f}" for k, v in R.groupby(m).ret.mean().items()))
                # in return terms: ATR units x median ATR% of price
                atrpct = np.median([(x.atr/x.close).median() for x in D.values()])*100
                print(f"     median ATR = {atrpct:.2f}% of price -> {R.ret.mean()*atrpct:+.3f}% per trade net")
