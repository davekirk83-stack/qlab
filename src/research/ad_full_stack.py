"""DK 22 Nov 10:27: "make it work like his does not just picking parts". AuclairsDad's FULL entry set, OR'd through the same gates
(his blueprint, doc 90 / memory): REGIME (16 x 15-min regression, hysteresis) -> paths: (1) clean breakout = Ignition bar (range >= 1.25x avg,
delta share >= 0.05, HTF EMA20/50 agrees) inside a coil (20-bar range <= 4 ATR); (2) RAW-CONVICTION continuation = bid/ask ratio >= 1.19
(delta share >= 0.087) with the regime, close in the outer 30% of the bar, HTF agrees; (3) DIVERGENCE = new 20-bar high on weaker
net delta than at the previous high (and the reverse), with net delta of the push above his 420-contract equivalent (our 90th pct).
Management = his panel (stop 45 / breakeven +15 / trail 1 ATR / target 9 ATR / 3h), governors 8/day, 3-bar cooloff. Tue/Wed off as doc 227.
US Tech 100 5-min, costs = data spread +1 pt outside US cash hours."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open("src/ad_stack_gate.py").read(); exec(src[:src.index("R = []")])
F = P7.features(d); a = F.atr.values; ds = F.dshare.values; htf = F.htf.values; C_, O_, H_, L_ = F.close.values, F.open.values, F.high.values, F.low.values
rng = (H_ - L_); loc = np.where(rng > 0, (C_ - L_) / np.where(rng > 0, rng, 1), 0.5)
dow = lt.dayofweek.values
# divergence: 20-bar new high/low, net delta of the last 6 bars vs the net delta of the 6 bars into the previous 20-bar high/low
nd6 = pd.Series(F.delta.values).rolling(6).sum().values; thr = np.nanpercentile(np.abs(nd6), 90)
hh = pd.Series(H_).rolling(20).max().shift(1).values; ll = pd.Series(L_).rolling(20).min().shift(1).values
ih = pd.Series(H_).rolling(20).apply(np.argmax, raw=True).shift(1).values; il = pd.Series(L_).rolling(20).apply(np.argmin, raw=True).shift(1).values
N = len(F); idx = np.arange(N)
prev_hi_nd = np.full(N, np.nan); prev_lo_nd = np.full(N, np.nan)
okh = np.isfinite(ih); j = (idx - 20 + np.nan_to_num(ih)).astype(int); prev_hi_nd[okh] = nd6[np.clip(j, 0, N - 1)][okh]
okl = np.isfinite(il); j = (idx - 20 + np.nan_to_num(il)).astype(int); prev_lo_nd[okl] = nd6[np.clip(j, 0, N - 1)][okl]
div_s = np.where((H_ > hh) & (nd6 < prev_hi_nd) & (np.abs(prev_hi_nd) >= thr) & (C_ < O_), -1,
        np.where((L_ < ll) & (nd6 > prev_lo_nd) & (np.abs(prev_lo_nd) >= thr) & (C_ > O_), 1, 0))
brk_s = F.sig.values * (RNG20 <= 4.0 * a)
conv_s = np.where((ds >= 0.087) & (loc >= 0.7) & (htf == 1), 1, np.where((ds <= -0.087) & (loc <= 0.3) & (htf == -1), -1, 0))
def build(paths, regime_rule="with", tuewed=True):
    s = np.zeros(N, int)
    for p in paths:
        v = {"brk": brk_s, "conv": conv_s, "div": div_s}[p]
        if p == "div":
            v = np.where((REG == 0) | (REG == v), v, 0) if regime_rule != "none" else v
        else:
            v = np.where(REG == v, v, 0) if regime_rule != "none" else v
        s = np.where(s == 0, v, s)
    ok = (s != 0) & np.isfinite(a) & EL
    if tuewed: ok &= ~np.isin(dow, (1, 2))
    ix = np.where(ok)[0]
    return lambda x: sigframe(F.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
out = []
days = (d.index[-1] - d.index[0]).days / 365.25
for name, paths, rr, tw in (("doc 227 stack (breakout only)", ["brk"], "with", True),
                            ("+ raw conviction", ["brk", "conv"], "with", True),
                            ("+ divergence", ["brk", "div"], "with", True),
                            ("FULL: breakout + conviction + divergence", ["brk", "conv", "div"], "with", True),
                            ("FULL, all weekdays", ["brk", "conv", "div"], "with", False),
                            ("conviction alone", ["conv"], "with", True),
                            ("divergence alone", ["div"], "with", True)):
    r = G.judge("ADFULL " + name, d, build(paths, rr, tw), manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{('ADFULL ' + name).replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    mo = t.groupby(t.t.dt.to_period("M")).pts.sum(); tday = t.groupby(t.t.dt.date).size()
    line = (f"{name:44} n {len(t):4} ({len(t)/days:4.0f}/yr, {len(t)/(days*252):.1f}/day) pts/trade {t.pts.mean():+.2f} win {100*(t.pts>0).mean():.0f}% total {t.pts.sum():+.0f} | "
            f"dev {t[t.t<cut].pts.mean():+.2f} hold-out {t[t.t>=cut].pts.mean():+.2f} | months+ {(mo>0).sum()}/{len(mo)} worst {mo.min():+.0f}")
    out.append(line); print(line, flush=True)
open("runs/research/ad_full_stack.txt", "w").write("\n".join(out))
