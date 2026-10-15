"""
THE 8-HOUR KELTNER BOOK, ON 31 SYMBOLS IT HAS NEVER SEEN.

The timeframe map found a clean monotonic gradient: edge over a same-regime
control rises with every step up in bar size, 5min +0.021% to 8h +1.341%, no
reversals across seven timeframes. The setup is a slow trade. The winning
geometry is a SMALL target and a WIDE stop - 0.5 ATR up, 3 ATR down, 95% win -
which is the opposite of the mid-target assumption carried since doc 63.

That peak was chosen out of 108 geometry cells on 18 symbols, so it is a
hypothesis, not a result. This runs the same configuration, unchanged and
unretuned, on data_1m_oos: 31 symbols never used in any sweep.

Three things are checked, not one:
  1. does the EDGE over the same-regime control replicate
  2. does the monotonic timeframe gradient replicate (the gradient is the
     real claim; a single cell could be luck, an ordered curve across seven
     timeframes is much harder to produce by chance)
  3. what the book actually pays per month on 49 symbols at DK's scale
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import keltner_tf as K

OOS = "/home/claude/qlab/data_1m_oos"
IS = "/home/claude/qlab/data_1m"
CFG = dict(t_atr=0.5, s_atr=3.0, kband=2.0, eff_cut=0.30)
HOLD = 64


def line(tag, c):
    if c is None:
        print(f"  {tag:<34} too few trades"); return
    print(f"  {tag:<34}{c['n']:>6}{c['per']:>7.1f}{c['mean']*100:>+9.3f}%"
          f"{c['t']:>+7.2f}{c['ctrl']*100:>+9.3f}%{c['edge']*100:>+8.3f}%"
          f"{c['te']:>+7.2f}{c['win']*100:>6.0f}%")


if __name__ == "__main__":
    print("8-HOUR KELTNER BOOK — OUT OF SAMPLE")
    print(f"config frozen from the in-sample sweep: 8h bars, hold {HOLD}, "
          f"target {CFG['t_atr']} ATR, stop {CFG['s_atr']} ATR,")
    print(f"band {CFG['kband']} ATR, range regime eff<{CFG['eff_cut']}. "
          f"Nothing retuned.\n")
    print(f"  {'panel':<34}{'n':>6}{'/mo':>7}{'net%':>10}{'t':>7}"
          f"{'ctrl%':>10}{'EDGE':>8}{'tEdge':>7}{'win%':>7}")

    D_is = K.bars(IS, "8h")
    D_oos = K.bars(OOS, "8h")
    c_is = K.cell(D_is, HOLD, **CFG)
    c_oos = K.cell(D_oos, HOLD, **CFG)
    line(f"IN SAMPLE   ({len(D_is)} symbols)", c_is)
    line(f"OUT OF SAMPLE ({len(D_oos)} symbols)", c_oos)

    print(f"\n{'='*96}")
    print("DOES THE TIMEFRAME GRADIENT REPLICATE OUT OF SAMPLE?")
    print("The gradient is the real claim. One cell can be luck; an ordered")
    print("curve across seven timeframes is much harder to produce by chance.\n")
    print(f"  {'bars':>6}{'IS edge':>12}{'OOS edge':>12}{'OOS net%':>11}"
          f"{'OOS t':>8}{'OOS n':>7}{'OOS /mo':>9}")
    gi = []; go = []
    for tf, mins in K.TFS:
        if tf in ("1D",): continue
        A = K.bars(IS, tf); B = K.bars(OOS, tf)
        ci = K.cell(A, HOLD, **CFG)
        co = K.cell(B, HOLD, **CFG)
        if ci is None or co is None:
            print(f"  {tf:>6}{'-':>12}{'-':>12}   (too few trades)")
            continue
        gi.append(ci["edge"]); go.append(co["edge"])
        print(f"  {tf:>6}{ci['edge']*100:>+11.3f}%{co['edge']*100:>+11.3f}%"
              f"{co['mean']*100:>+10.3f}%{co['t']:>+8.2f}{co['n']:>7}{co['per']:>9.1f}")
    if len(go) >= 4:
        from scipy import stats
        rho = stats.spearmanr(range(len(go)), go).statistic
        rho_i = stats.spearmanr(range(len(gi)), gi).statistic
        print(f"\n  monotonicity of edge vs timeframe:  in-sample rho {rho_i:+.2f}"
              f"   out-of-sample rho {rho:+.2f}")
        print("  (+1.00 = edge rises at every single step up in bar size)")

    print(f"\n{'='*96}")
    print("WHAT IT PAYS AT DK'S SCALE")
    if c_oos is not None:
        both = {**D_is, **D_oos}
        c_all = K.cell(both, HOLD, **CFG)
        if c_all:
            line(f"ALL {len(both)} SYMBOLS COMBINED", c_all)
            for lev in (2, 3, 5):
                print(f"    at {lev}x on $2,000: ${c_all['mean']*2000*lev:+.2f}/trade"
                      f"  x {c_all['per']:.1f} trades/mo  =  "
                      f"${c_all['mean']*2000*lev*c_all['per']:+.0f}/month")
            print(f"\n  DK's target is 50+ trades a month. This book gives "
                  f"{c_all['per']:.0f} on {len(both)} symbols.")
            print(f"  To reach 50 it needs roughly "
                  f"{int(np.ceil(50/max(c_all['per'],0.1)*len(both)))} instruments, "
                  f"which is a breadth problem, not a signal problem.")
