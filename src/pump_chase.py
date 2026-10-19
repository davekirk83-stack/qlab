"""
PUMP CHASE WITH A TRAILING STOP — DK, 18 Oct: "do we have a strategy for chasing pumps with a
trailing stop?" plus his EMA-cross entries: "jumping in just before or as a major Gooner EMA
crossover happens" and the mirror "impending downward crosses (death crosses?) as shorts".

ENTRY (long): close up >= X% over the last N bars, with volume over those N bars >= V x the
trailing 30-day median N-bar volume ("with volume"). Mirror for shorts (dump chase), alts only
(no directional short on BTC/ETH, rule from 16 Oct). One trade per episode (gap N bars).
EMA entries (20/50 on the panel's own bars): CROSS = first bar fast > slow; ABOUT-TO-CROSS =
fast still below slow by < 0.3 ATR and rising faster than slow (converging); mirrors for shorts.

EXITS: trailing stop k x ATR14 from the best price (k = 1, 2, 3), with a cap; and DK's scale-out
(half at +1 ATR, stop to breakeven, trail the rest). Costs 4.5bp per side (perps) / 10bp (daily
alts, spot-like). Entry at the next bar's open.
CONTROLS: random bar, same coin, same side, same exit, 3 per trade (identical management, so the
exit geometry cannot flatter the entry); exit-free barrier race +-2 ATR.
PANELS: 1-minute (18 perps, 13 mo) · 15-minute (42 pairs, 5 yrs) · hourly (33 perps, 15 mo) ·
daily (242 alts incl. delisted, from 2024-12).
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd
RNG = np.random.default_rng(21)
Q = "/home/claude/qlab"
PANELS = {
    "1m":  dict(d=f"{Q}/data_1m", tcol="t", unit="ms", cost=4.5e-4, grid=[(5, 2.0), (15, 3.0), (60, 5.0)], cap=240, daybars=1440),
    "15m": dict(d=f"{Q}/data_15m", tcol=None, unit=None, cost=4.5e-4, grid=[(4, 3.0), (16, 5.0), (96, 10.0)], cap=192, daybars=96),
    "1h":  dict(d=f"{Q}/data_1h_33", tcol="date", unit=None, cost=4.5e-4, grid=[(4, 5.0), (24, 10.0)], cap=168, daybars=24),
    "1d":  dict(d=f"{Q}/data_alt", tcol="date", unit=None, cost=10e-4, grid=[(1, 15.0), (3, 25.0), (7, 40.0)], cap=30, daybars=1),
}
VOLX = 2.0


def load(p, f):
    d = pd.read_csv(f)
    if p["tcol"] is None: d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d.iloc[:, 1:]
    else: d.index = pd.to_datetime(d[p["tcol"]], unit=p["unit"], utc=True, errors="coerce"); d = d[d.index.notna()]
    d = d[["open", "high", "low", "close", "volume"]].astype(float)
    d = d[~d.index.duplicated()].sort_index()
    d = d[(d.close > 0) & (d.volume >= 0)]
    if len(d) < 600: return None
    pc = d.close.shift(); tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    d["atr"] = tr.rolling(14).mean()
    d["ef"] = d.close.ewm(span=20, adjust=False).mean(); d["es"] = d.close.ewm(span=50, adjust=False).mean()
    return d.dropna()


def signals(d, N, X, p):
    mv = d.close/d.close.shift(N) - 1
    vN = d.volume.rolling(N).sum(); vmed = vN.rolling(30*p["daybars"], min_periods=5*p["daybars"]).median()
    volok = vN >= VOLX*vmed
    out = {"pump": (mv >= X/100) & volok, "pump (no volume filter)": (mv >= X/100),
           "dump": (mv <= -X/100) & volok}
    return out


def ema_signals(d):
    up = (d.ef > d.es) & (d.ef.shift() <= d.es.shift())
    dn = (d.ef < d.es) & (d.ef.shift() >= d.es.shift())
    gap = (d.es - d.ef)/d.atr; conv = (d.ef - d.ef.shift(3)) > (d.es - d.es.shift(3))
    about_up = (gap > 0) & (gap < 0.3) & conv
    about_dn = (-gap > 0) & (-gap < 0.3) & ~conv
    return {"golden cross": up, "about to golden-cross": about_up, "death cross": dn, "about to death-cross": about_dn}


def trail_exit(O, H, L, C, a, i, s, k, cap, cost, scale=False):
    e = O[i+1]; atr = a[i]; stop = e - s*k*atr; best = e; rem, pnl, be = 1.0, 0.0, False
    pr = lambda px: s*(px/e - 1) - cost
    for j in range(i+1, min(i+cap+1, len(C))):
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop): return pnl + rem*pr(stop), j-i
        if scale and not be and ((s == 1 and fav >= e + s*atr) or (s == -1 and fav <= e + s*atr)):
            pnl += 0.5*pr(e + s*atr); rem = 0.5; be = True; stop = e*(1 + s*2*cost)
        best = max(best, fav) if s == 1 else min(best, fav)
        t = best - s*k*atr
        if (s == 1 and t > stop) or (s == -1 and t < stop): stop = t
    j = min(i+cap, len(C)-1); return pnl + rem*pr(C[j]), j-i


def race(H, L, C, a, i, s, k=2.0, horizon=200):
    e = C[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= e + s*k*a[i]) if s == 1 else (L[j] <= e + s*k*a[i])
        dn = (L[j] <= e - s*k*a[i]) if s == 1 else (H[j] >= e - s*k*a[i])
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan


def run(B, sigfn, side, k, cap, cost, scale=False, gap=1, nctrl=3, exclude=()):
    rows, ctrl = [], []
    for sym, d in B.items():
        if side == -1 and any(sym.startswith(x) for x in exclude): continue
        O, H, L, C, a = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
        sig = sigfn(sym, d).values; idx = np.where(sig)[0]; idx = idx[(idx > 100) & (idx < len(C)-cap-2)]; last = -10**9
        for i in idx:
            if i - last < gap: continue
            last = i
            r, n = trail_exit(O, H, L, C, a, i, side, k, cap, cost, scale); rows.append((sym, d.index[i], r, n, race(H, L, C, a, i, side)))
            for _ in range(nctrl):
                j = int(RNG.integers(100, len(C)-cap-2)); r2, n2 = trail_exit(O, H, L, C, a, j, side, k, cap, cost, scale); ctrl.append((sym, d.index[j], r2, n2, race(H, L, C, a, j, side)))
    cols = ["sym", "ts", "ret", "bars", "race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


def line(lbl, R, Cc, minn=60):
    if len(R) < minn: print(f"  {lbl:<46}{len(R):>6} too few", flush=True); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    by = R.groupby("sym").ret.mean() - Cc.groupby("sym").ret.mean()
    top = R.ret.sort_values(ascending=False); fat = top.iloc[:max(1, len(R)//20)].sum()/R.ret.sum()*100 if R.ret.sum() > 0 else float("nan")
    print(f"  {lbl:<46}{len(R):>6,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>5.0f}"
          f"{Cc.ret.mean()*100:>+8.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>6.0f}%{R.race.mean()*100:>6.0f}%{Cc.race.mean()*100:>5.0f}%{fat:>6.0f}%", flush=True)
    if t >= 2.0 and (R.ret.mean()-Cc.ret.mean()) > 0:
        m = R.ts.dt.to_period("M"); g = R.groupby(m).ret.agg(["sum","mean","count"])
        big = g["sum"].idxmax(); ex = R[m != big]
        print(f"     biggest month {big}: {g.loc[big,'mean']*100:+.1f}% x {int(g.loc[big,'count'])} = {g.loc[big,'sum']/R.ret.sum()*100:.0f}% of P&L; EX that month {ex.ret.mean()*100:+.3f}%/ep (n={len(ex)}); months >0: {(g['mean']>0).mean()*100:.0f}%; median trade {R.ret.median()*100:+.2f}%", flush=True)


def hdr(): print(f"  {'entry / exit':<46}{'n':>6}{'per ep':>9}{'t':>6}{'win':>6}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>7}{'race':>6}{'ctrl':>5}{'top5%':>6}")


if __name__ == "__main__":
    which = sys.argv[1:] or list(PANELS)
    for name in which:
        p = PANELS[name]
        B = {}
        for f in sorted(glob.glob(f"{p['d']}/*.csv")):
            d = load(p, f)
            if d is not None: B[os.path.basename(f)[:-4]] = d
        nb = sum(len(d) for d in B.values())
        print(f"\n===== {name} panel: {len(B)} instruments, {nb:,} bars, {min(d.index.min() for d in B.values()).date()} .. {max(d.index.max() for d in B.values()).date()}; cost {p['cost']*1e4:.0f}bp/side; cap {p['cap']} bars =====")
        hdr()
        for N, X in p["grid"]:
            S = {s: signals(d, N, X, p) for s, d in B.items()}
            for key in ("pump", "pump (no volume filter)"):
                for k in (1.0, 2.0, 3.0):
                    R, Cc = run(B, lambda sym, d, key=key: S[sym][key], 1, k, p["cap"], p["cost"], gap=N)
                    line(f"{key} +{X:.0f}%/{N}b, trail {k:.0f} ATR", R, Cc)
                R, Cc = run(B, lambda sym, d, key=key: S[sym][key], 1, 2.0, p["cap"], p["cost"], scale=True, gap=N)
                line(f"{key} +{X:.0f}%/{N}b, scale-out + trail 2", R, Cc)
            for k in (1.0, 2.0, 3.0):
                R, Cc = run(B, lambda sym, d: S[sym]["dump"], -1, k, p["cap"], p["cost"], gap=N, exclude=("BTC", "ETH"))
                line(f"DUMP chase short -{X:.0f}%/{N}b, trail {k:.0f} ATR (alts)", R, Cc)
                if k == 2.0 and len(R) >= 60:
                    R["m"] = R.ts.dt.to_period("M"); Cc["m"] = Cc.ts.dt.to_period("M")
                    print("     by month (real/ctrl %):", " ".join(f"{m}:{R[R.m==m].ret.mean()*100:+.1f}/{Cc[Cc.m==m].ret.mean()*100:+.1f}({int((R.m==m).sum())})" for m in sorted(R.m.unique())))
                    h = len(R)//2; Rs = R.sort_values("ts"); print(f"     split-half: {Rs.ret.iloc[:h].mean()*100:+.3f}% / {Rs.ret.iloc[h:].mean()*100:+.3f}%   median {R.ret.median()*100:+.3f}%  worst {R.ret.min()*100:+.1f}%  best {R.ret.max()*100:+.1f}%")
            R, Cc = run(B, lambda sym, d: (d.close/d.close.shift(N) - 1 <= -X/100), -1, 2.0, p["cap"], p["cost"], gap=N, exclude=("BTC", "ETH"))
            line(f"DUMP chase short -{X:.0f}%/{N}b, NO volume filter, trail 2", R, Cc)
        E = {s: ema_signals(d) for s, d in B.items()}
        for key, side in (("golden cross", 1), ("about to golden-cross", 1), ("death cross", -1), ("about to death-cross", -1)):
            for k in (2.0, 3.0):
                R, Cc = run(B, lambda sym, d, key=key: E[sym][key], side, k, p["cap"], p["cost"], gap=20, exclude=("BTC", "ETH") if side == -1 else ())
                line(f"EMA {key}, trail {k:.0f} ATR", R, Cc)
