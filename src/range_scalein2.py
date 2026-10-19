import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, clean_portfolio as CP, regime_detect as RD
from range_scalein import load_all, run
B = load_all()
CANDS = {"REGISTERED v2.2": (RD.BID, RD.ASK),
         "CL lots, target at mid EMA": ([(1/3, 0.0), (1/3, -0.7), (1/3, -1.0)], [(1.0, "mid")]),
         "registered bids, ONE target at band": (RD.BID, [(1.0, 0.0)]),
         "registered bids, ONE target at mid EMA": (RD.BID, [(1.0, "mid")]),
         "CL lots deeper: band / -1.0 / -1.3, mid target": ([(1/3, 0.0), (1/3, -1.0), (1/3, -1.3)], [(1.0, "mid")]),
         "CL 4 lots: +0.3 / 0 / -0.7 / -1.0, mid target": ([(0.25, 0.3), (0.25, 0.0), (0.25, -0.7), (0.25, -1.0)], [(1.0, "mid")])}
print(f"  {'ladder':<50}{'eps':>7}{'per ep':>9}{'t':>6}{'win':>5}{'median':>8}{'hold(b)':>8}{'CAGR 1x':>9}{'maxDD':>8}{'Sharpe':>7}{'L':>8}{'S':>8}")
for name, (bid, ask) in CANDS.items():
    R = run(B, bid, ask); R["hold"] = (R.exit - R.entry).dt.total_seconds()/900
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    r, *_ = CP.simulate(R[["sym","entry","exit","ret"]], 20, 1)
    print(f"  {name:<50}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>4.0f}%{R.ret.median()*100:>+7.3f}%{R.hold.median():>8.0f}{r['cagr']*100:>+8.1f}%{r['dd']*100:>+7.1f}%{r['sharpe']:>7.2f}{R[R.side=='L'].ret.mean()*100:>+7.3f}%{R[R.side=='S'].ret.mean()*100:>+7.3f}%", flush=True)
    ys = []
    for yv in sorted(set(R.entry.dt.year)):
        Ry = R[R.entry.dt.year == yv]; ry, *_ = CP.simulate(Ry[["sym","entry","exit","ret"]], 20, 1)
        ys.append(f"{yv}:{Ry.ret.mean()*100:+.3f}%/{ry['cagr']*100:+.0f}%/{ry['dd']*100:+.0f}%" if ry else f"{yv}:blew up")
    print("     per ep / CAGR 1x / maxDD by year:", "  ".join(ys))
    cm = (R.groupby("sym").ret.mean() > 0).mean()*100; print(f"     coins positive {cm:.0f}%; worst month {R.set_index('entry').ret.resample('ME').mean().min()*100:+.3f}%; months >0 {(R.set_index('entry').ret.resample('ME').mean()>0).mean()*100:.0f}%", flush=True)
