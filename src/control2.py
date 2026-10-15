"""Isolate whether the detection floor is the GATES or the TURNOVER."""
import numpy as np, pandas as pd, core as C
from control import synth, run_gates, N_INST, SEED

def rare_signal(df, hold):
    pos = (df.close - df.low) / (df.high - df.low).replace(0, np.nan)
    s = (pos > 0.5).astype(float).fillna(0.0)
    return s.rolling(hold, min_periods=1).max()   # hold -> far fewer round trips

print("Same planted edge, lower turnover (holding period). Does the floor drop?\n")
for hold in (1, 5, 20):
    print(f"  hold={hold} bars")
    for edge in (10, 20, 40):
        panel = {f"S{i}": synth(edge, SEED+i) for i in range(N_INST)}
        r = run_gates(panel, lambda df,h=hold: rare_signal(df,h), label="")
        print(f"    {edge:3d}bp  Sharpe {r['sharpe']:+6.2f}  trades {r['trades']:6d}  {r['verdict']}")
