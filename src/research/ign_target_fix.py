"""Weekly review 28 Nov 2026. Live/demo Ignition-AD winners 27 Nov hit the IG limit fast (35-36 min to best): live +41 pts (limit), demo +25 pts
(limit) and then ran +141 pts more. Cause found: the target is 9 x 5-min ATR, but the stop has a 45-pt floor, so in quiet overnight hours
(ATR 3-5 pts) the target (25-41 pts) is SMALLER than the stop (45 pts). Test: target floors / wider targets on the live configuration
(IG_US_PLAIN: plain v1.1 in US cash hours, AD stack outside), ONE integrated simulation (same engine as us_plain_integrated.py).
Calibration: row 'live 9 ATR, BE15' must reproduce us_plain_integrated.txt row B (n 270, +11.01 pts/trade)."""
import os, sys
src = open("src/research/us_plain_integrated.py").read(); exec(src[:src.index("\nout = []")])
def build_tgt(mode, tgt_fn, where="all"):
    stack = np.where(REG == brk_s, brk_s, 0); conv = np.where(REG == conv_s, conv_s, 0)
    st = np.where(stack != 0, stack, conv); st = np.where(np.isin(dow, (1, 2)), 0, st)
    plain = F.sig.values.astype(int); s = np.where(CASH, plain, st)
    ok = (s != 0) & np.isfinite(a) & EL; ix = np.where(ok)[0]
    stop = np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]); base = P7.TGT_ATR * a[ix]; new = tgt_fn(a[ix], stop)
    tg = np.where(CASH[ix], base, new) if where == "outside" else new
    return lambda x: sigframe(F.index[ix], s[ix].astype(int), "market", np.nan, stop, tg, P7.CAP, dist=True)
V = [("live 9 ATR", lambda a_, sp: 9 * a_, "all"),
     ("target >= stop", lambda a_, sp: np.maximum(9 * a_, sp), "all"),
     ("target >= 1.5 x stop", lambda a_, sp: np.maximum(9 * a_, 1.5 * sp), "all"),
     ("target >= 2 x stop", lambda a_, sp: np.maximum(9 * a_, 2 * sp), "all"),
     ("12 ATR", lambda a_, sp: 12 * a_, "all"),
     ("15 ATR", lambda a_, sp: 15 * a_, "all"),
     ("no target (trail only)", lambda a_, sp: 1e5 + 0 * a_, "all"),
     ("target >= stop, outside US only", lambda a_, sp: np.maximum(9 * a_, sp), "outside"),
     ("target >= 1.5 x stop, outside US only", lambda a_, sp: np.maximum(9 * a_, 1.5 * sp), "outside")]
out = []
for be in (15, 20):
    P7.BE = be
    for name, fn, where in V:
        tag = f"IGNTGT {name} BE{be}".replace(">=", "ge").replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
        r = G.judge(tag, d, build_tgt("B", fn, where), manage=ign_manage)
        t = pd.read_csv(f"{G.OUT}/{tag}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
        mo = t.groupby(t.t.dt.to_period("M")).pts.sum(); h = len(t) // 2
        lt_ = t.t.dt.tz_convert("America/New_York"); cash = ((lt_.dt.hour * 60 + lt_.dt.minute) >= P7.US_OPEN) & ((lt_.dt.hour * 60 + lt_.dt.minute) < P7.US_CLOSE)
        line = (f"BE{be} {name:40} n {len(t):4} pts/trade {t.pts.mean():+.2f} median {t.pts.median():+.2f} win {100*(t.pts>0).mean():.0f}% total {t.pts.sum():+.0f} | "
                f"halves {t.pts[:h].mean():+.2f} / {t.pts[h:].mean():+.2f} | dev {t[t.t<cut].pts.mean():+.2f} hold-out {t[t.t>=cut].pts.mean():+.2f} | "
                f"months+ {(mo>0).sum()}/{len(mo)} worst {mo.min():+.0f} | outside-US n {(~cash).sum()} {t[~cash].pts.mean():+.2f}  US n {cash.sum()} {t[cash].pts.mean():+.2f}")
        out.append(line); print(line, flush=True)
open("runs/research/ign_target_fix.txt", "w").write("\n".join(out) + "\n")
