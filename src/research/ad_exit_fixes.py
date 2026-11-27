"""DK 27 Nov: profit taking / loss avoidance on the live AD stack (breakout + conviction, regime, Tue/Wed off, round the clock).
Live: winners kept ~41% of their best open profit. Tests breakeven trigger and trail width on the same backtest as doc 256."""
import os, sys
src = open("src/research/ad_full_stack.py").read(); exec(src[:src.index("out = []")])
days = (d.index[-1] - d.index[0]).days / 365.25; out = []
for be, tr in ((15, 1.0), (20, 1.0), (30, 1.0), (15, 1.5), (30, 1.5), (45, 1.5), (30, 2.0)):
    P7.BE, P7.TRAIL_ATR = be, tr
    name = f"live set BE{be} trail{tr}"
    r = G.judge("ADX " + name, d, build(["brk", "conv"], "with", True), manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{('ADX ' + name).replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    mo = t.groupby(t.t.dt.to_period("M")).pts.sum()
    line = (f"{name:26} n {len(t):4} pts/trade {t.pts.mean():+.2f} win {100*(t.pts>0).mean():.0f}% total {t.pts.sum():+.0f} | "
            f"dev {t[t.t<cut].pts.mean():+.2f} hold-out {t[t.t>=cut].pts.mean():+.2f} | months+ {(mo>0).sum()}/{len(mo)} worst {mo.min():+.0f}")
    out.append(line); print(line, flush=True)
open("runs/research/ad_exit_fixes.txt", "w").write("\n".join(out))
