"""
THE 2h-4h SWEET SPOT: FINDING THE RIGHT HOLD.

Out of sample the 8h cell did NOT replicate (+1.633% in sample -> -0.063% out),
which is what an overfit peak looks like: it was the top of 108 cells on 135
trades. But 2h and 4h did replicate and IMPROVED out of sample, which is the
opposite signature:

              IS edge    OOS edge   OOS net     OOS t    OOS /mo
   30min      +0.059%    +0.187%    +0.055%     +2.58      326
   2h         +0.044%    +0.287%    +0.221%     +2.46       79
   4h         +0.175%    +0.557%    +0.472%     +3.00       35

So the real book lives at 2h-4h, not 8h.

ONE THING NOT YET SWEPT: the hold was frozen at 64 bars from the 8h run, which
at 4h is 256 hours - over ten days. These are not day trades, they are swing
trades on finer bars, and the hold was never chosen for this timeframe. That is
the same oversight as the timeframe itself, one level down.

So: hold swept properly at 2h and 4h, in sample and out of sample side by side
in the same table, so overfitting is visible as a divergence rather than
discovered later.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import keltner_tf as K

IS = "/home/claude/qlab/data_1m"
OOS = "/home/claude/qlab/data_1m_oos"
CFG = dict(t_atr=0.5, s_atr=3.0, kband=2.0, eff_cut=0.30)


if __name__ == "__main__":
    print("KELTNER 2h / 4h — SWEEPING THE HOLD, IN AND OUT OF SAMPLE TOGETHER")
    print(f"target {CFG['t_atr']} ATR, stop {CFG['s_atr']} ATR, band "
          f"{CFG['kband']} ATR, range regime eff<{CFG['eff_cut']}\n")
    rows = []
    for tf, mins in (("1h", 60), ("2h", 120), ("4h", 240)):
        A = K.bars(IS, tf); B = K.bars(OOS, tf)
        print(f"--- {tf} bars " + "-"*84)
        print(f"  {'hold':>5}{'=days':>7}{'IS net%':>10}{'IS t':>7}{'IS edge':>9}"
              f"{'|':>3}{'OOS net%':>10}{'OOS t':>7}{'OOS edge':>10}{'OOStE':>7}"
              f"{'OOS n':>7}{'/mo':>7}{'$/mo 3x':>9}")
        for hold in (4, 8, 12, 16, 24, 32, 48, 64):
            a = K.cell(A, hold, **CFG)
            b = K.cell(B, hold, **CFG)
            if a is None or b is None: continue
            dol = b["mean"]*2000*3*b["per"]
            rows.append(dict(tf=tf, hold=hold, days=hold*mins/1440,
                             is_net=a["mean"], is_t=a["t"], is_edge=a["edge"],
                             oos_net=b["mean"], oos_t=b["t"], oos_edge=b["edge"],
                             oos_te=b["te"], n=b["n"], per=b["per"],
                             win=b["win"], dol=dol))
            print(f"  {hold:>5}{hold*mins/1440:>7.1f}{a['mean']*100:>+9.3f}%"
                  f"{a['t']:>+7.2f}{a['edge']*100:>+8.3f}%{'|':>3}"
                  f"{b['mean']*100:>+9.3f}%{b['oos_t'] if False else b['t']:>+7.2f}"
                  f"{b['edge']*100:>+9.3f}%{b['te']:>+7.2f}{b['n']:>7}"
                  f"{b['per']:>7.1f}{dol:>9.0f}")
        print()

    print("="*100)
    ok = [r for r in rows if r["oos_net"] > 0 and r["oos_t"] >= 2.0
          and r["is_net"] > 0 and r["n"] >= 150]
    print(f"CELLS POSITIVE IN BOTH SAMPLES with OOS t>=2.0 and n>=150: "
          f"{len(ok)} of {len(rows)}")
    if ok:
        print(f"\n  {'tf':>5}{'hold':>6}{'days':>6}{'IS net':>9}{'OOS net':>10}"
              f"{'OOS t':>7}{'OOS edge':>10}{'/mo':>7}{'win':>6}{'$/mo 3x':>9}")
        for r in sorted(ok, key=lambda x: -x["dol"]):
            print(f"  {r['tf']:>5}{r['hold']:>6}{r['days']:>6.1f}"
                  f"{r['is_net']*100:>+8.3f}%{r['oos_net']*100:>+9.3f}%"
                  f"{r['oos_t']:>+7.2f}{r['oos_edge']*100:>+9.3f}%"
                  f"{r['per']:>7.1f}{r['win']*100:>5.0f}%{r['dol']:>9.0f}")
        b = max(ok, key=lambda x: x["dol"])
        print(f"\nBEST BY MONTHLY DOLLARS, positive in both samples:")
        print(f"  {b['tf']} bars, hold {b['hold']} ({b['days']:.1f} days), "
              f"target 0.5 ATR, stop 3 ATR, range regime")
        print(f"  in sample  {b['is_net']*100:+.3f}%/trade")
        print(f"  out of sample {b['oos_net']*100:+.3f}%/trade  t={b['oos_t']:+.2f}  "
              f"edge over control {b['oos_edge']*100:+.3f}%  win {b['win']*100:.0f}%")
        print(f"  {b['per']:.0f} trades/month on 31 symbols  ->  "
              f"${b['dol']:.0f}/month at 3x on $2,000")
        print(f"  scaled to 49 symbols: ~{b['per']*49/31:.0f} trades/month, "
              f"~${b['dol']*49/31:.0f}/month")
    else:
        print("  none - the hold sweep does not produce a cell positive in both.")
