"""Execution technique (DK 27 Nov 16:07: "I still don't think you have truly understood or refined your trading an execution techniques").
Live Ignition/AD enters at MARKET after the signal bar; live fills averaged ~1.9 pts worse than the signal close (7 trades), and 3 of 7
live losers went straight to the stop. A trader buys the pullback into a breakout, not the top of the bar. Test on the live config
(IG_US_PLAIN: plain Ignition in US cash hours, AD stack outside), same gate/costs/management, entry variants:
  market (now) | limit f x ATR back from the signal close, good for N bars | limit at the signal bar's midpoint, good for N bars."""
import os, sys
src = open("src/research/us_plain_integrated.py").read(); exec(src[:src.index("\nout = []")])
def build_lim(f=None, mid=False, valid=3):
    base = build_mix("B")(None)
    if f is None and not mid: return lambda x: base
    i_of = F.index.get_indexer(base.index); s = base.side.values
    if mid: px = (H_[i_of] + L_[i_of]) / 2
    else: px = C_[i_of] - s * f * a[i_of]
    out = base.copy(); out["kind"] = "limit"; out["price"] = px; out["valid"] = valid
    return lambda x: out
rows = []
for lab, kw in (("market (live)", {}), ("limit 0.25 ATR back, 3 bars", {"f": 0.25}), ("limit 0.5 ATR back, 3 bars", {"f": 0.5}),
                ("limit 0.25 ATR back, 6 bars", {"f": 0.25, "valid": 6}), ("limit at signal-bar midpoint, 3 bars", {"mid": True})):
    nm = "IGLIM " + lab.split(" (")[0].replace(",", "")
    r = G.judge(nm, d, build_lim(**kw), manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{nm.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    mo = t.groupby(t.t.dt.to_period("M")).pts.sum(); h = len(t) // 2
    line = (f"{lab:38} n {len(t):4} pts/trade {t.pts.mean():+.2f} win {100*(t.pts>0).mean():.0f}% total {t.pts.sum():+.0f} | halves {t.pts[:h].mean():+.2f} / {t.pts[h:].mean():+.2f} | "
            f"dev {t[t.t<cut].pts.mean():+.2f} hold-out {t[t.t>=cut].pts.mean():+.2f} | months+ {(mo>0).sum()}/{len(mo)} worst {mo.min():+.0f}")
    rows.append(line); print(line, flush=True)
open("runs/research/ign_limit_entry.txt", "w").write("\n".join(rows))
