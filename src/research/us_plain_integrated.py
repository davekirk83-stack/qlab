"""Audit (DK 27 Nov 16:06: make sure it's not the testing that is flawed). The 15:50 'stack outside US hours + plain v1.1 inside'
figure stitched two separate backtests (paperbook7 replay + gate judge) with different cost models and possible overlapping positions.
This re-tests it as ONE simulation: the same gate (G.judge), the same costs (data spread, +1 pt outside US cash hours), one position at a time,
the same management (stop max(45, V11 ATR), breakeven +15, 1-ATR trail, target 9 ATR, cap). Signals:
  A  live set before today: breakout + conviction, regime gate (coil for breakout), Tue/Wed off, every hour ex 12-15 NY
  B  IG_US_PLAIN: inside US cash hours plain Ignition (no regime/coil/Tue-Wed); outside, A's rules
  C  plain Ignition in US cash hours only (the original live engine)"""
import os, sys
src = open("src/research/ad_full_stack.py").read(); exec(src[:src.index("out = []")])
cashm = (lt.hour * 60 + lt.minute >= P7.US_OPEN) & (lt.hour * 60 + lt.minute < P7.US_CLOSE)
CASH = np.asarray(cashm)
def build_mix(mode):
    s = np.zeros(N, int)
    stack = np.where(REG == brk_s, brk_s, 0); conv = np.where(REG == conv_s, conv_s, 0)
    st = np.where(stack != 0, stack, conv); st = np.where(np.isin(dow, (1, 2)), 0, st)
    plain = F.sig.values.astype(int)
    if mode == "A": s = st
    if mode == "B": s = np.where(CASH, plain, st)
    if mode == "C": s = np.where(CASH, plain, 0)
    ok = (s != 0) & np.isfinite(a) & EL; ix = np.where(ok)[0]
    return lambda x: sigframe(F.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
out = []
for mode, name in (("A", "live set before today (stack all hours)"), ("B", "IG_US_PLAIN (plain in US hours, stack outside)"), ("C", "plain Ignition, US cash hours only")):
    r = G.judge("USPLAIN " + mode, d, build_mix(mode), manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/USPLAIN_{mode}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    mo = t.groupby(t.t.dt.to_period("M")).pts.sum(); h = len(t) // 2
    line = (f"{mode} {name:48} n {len(t):4} pts/trade {t.pts.mean():+.2f} win {100*(t.pts>0).mean():.0f}% total {t.pts.sum():+.0f} | "
            f"halves {t.pts[:h].mean():+.2f} / {t.pts[h:].mean():+.2f} | dev {t[t.t<cut].pts.mean():+.2f} hold-out {t[t.t>=cut].pts.mean():+.2f} | "
            f"months+ {(mo>0).sum()}/{len(mo)} worst {mo.min():+.0f}")
    out.append(line); print(line, flush=True)
open("runs/research/us_plain_integrated.txt", "w").write("\n".join(out))
