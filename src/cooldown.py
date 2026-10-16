"""Per-instrument COOLDOWN as a real gate, not a post-hoc split.
post_loss.py found episodes starting <6h after the previous episode on the same
coin lose (-0.19%, t=-18) whatever the previous outcome. Here the ladder is
simply not allowed to start a new episode until N hours after the last one on
that coin closed. Exits are untouched. Tests 0 (registered), 2, 6, 12, 24h."""
import warnings; warnings.filterwarnings("ignore")
import os, glob, inspect, sys
import numpy as np, pandas as pd
import clean_portfolio as CP, regime_detect as RD
from regime_hyst import load

_src = inspect.getsource(CP.episodes).replace("def episodes(", "def episodes_cd(")
_src = _src.replace("    oi = None; sold = set()\n    sgn",
                    "    oi = None; sold = set(); cool = -1; was_open = False\n    sgn")
_src = _src.replace("        if not ok: continue\n        if inv:",
                    "        if oi is None and was_open: cool = i + CD; was_open = False\n"
                    "        if oi is not None: was_open = True\n"
                    "        if not ok: continue\n        if inv:")
_src = _src.replace("        for k, (frac, off) in enumerate(BID):",
                    "        if oi is None and i < cool: continue\n"
                    "        for k, (frac, off) in enumerate(BID):")
assert "cool = i + CD" in _src and "i < cool" in _src
exec(_src, CP.__dict__)

if __name__ == "__main__":
    P = {}
    for s, d in load().items():
        D, ema, lo, hi, a = RD.detectors(d)
        v = pd.Series(D["contain"]); P[s] = (d, (v > v.expanding(500).median()).values, ema, lo, hi, a)
    print(f"{len(P)} coins.\n")
    print(f"  {'cooldown':<12}{'episodes':>10}{'per ep':>10}{'t':>7}{'win':>6}{'total':>9}{'worst':>8}"
          f"{'CAGR 1x':>9}{'maxDD':>8}{'Sharpe':>8}{'CAGR 2x':>9}{'maxDD':>8}")
    for hrs in (0, 2, 6, 12, 24):
        CP.CD = hrs*4; rows = []
        for s, (d, al, ema, lo, hi, a) in P.items():
            for side in ("L", "S"):
                rows += CP.episodes_cd(d, al, ema, lo, hi, a, None, "optimistic", side, s)
        S = pd.DataFrame(rows, columns=["sym","entry","exit","ret","side"]); S = S[np.isfinite(S.ret)]
        t = S.ret.mean()/(S.ret.std(ddof=1)/np.sqrt(len(S)))
        r1, _, _ = CP.simulate(S, 40, 1); r2, _, _ = CP.simulate(S, 40, 2)
        print(f"  {str(hrs)+'h':<12}{len(S):>10,}{S.ret.mean()*100:>+9.3f}%{t:>+7.1f}{(S.ret>0).mean()*100:>5.0f}%"
              f"{S.ret.sum()*100:>+8.0f}%{S.ret.min()*100:>+7.1f}%{r1['cagr']*100:>8.1f}%{r1['dd']*100:>7.1f}%"
              f"{r1['sharpe']:>8.2f}{r2['cagr']*100:>8.1f}%{r2['dd']*100:>7.1f}%", flush=True)
