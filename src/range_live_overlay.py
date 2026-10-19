import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, clean_portfolio as CP, regime_detect as RD
from range_scalein import load_all, run
B = load_all()
T0 = pd.Timestamp("2026-10-16", tz="UTC")
s = json.load(open("/home/claude/qlab-git/runs/paper2_state.json")); print("LIVE v2.2:", s["closed"], "trips closed, equity", round(s["equity"],2), "started", s["started"])
for name, (bid, ask) in {"v2.2 ladder": (RD.BID, RD.ASK), "bids + ONE mid-EMA target": (RD.BID, [(1.0, "mid")]), "CL lots + mid target": ([(1/3,0.0),(1/3,-0.7),(1/3,-1.0)], [(1.0,"mid")])}.items():
    R = run(B, bid, ask); R = R[R.entry >= T0]
    r, taken, skipped = CP.simulate(R[["sym","entry","exit","ret"]], 20, 3)
    print(f"  BACKTEST over the live window {name:<28} eps {len(R):>4} per ep {R.ret.mean()*100:+.3f}% win {(R.ret>0).mean()*100:.0f}%  -> $2,000 at 20 slots 3x: {r['final']:,.0f}" if r else f"  {name}: blew up")
