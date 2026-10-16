"""Patterns book (patterns_proper.py, doc 39) on the 20-year ETF panel.
Pattern-native targets and stops, scored against a matched random control
with the same reward:risk in the same instrument. Unchanged detection."""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd
import patterns_proper as PP
import levels_general as LG

def load_etf20(which):
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_etf20/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d.index.name = "date"
        if len(d) > 600: out[s] = d
    return out
PP.load_universe = load_etf20
print("PATTERNS WITH THEIR OWN TARGETS — 37 ETFs, 20+ years\n")
A, B = PP.run("etf20")
a = PP.report("REAL (all patterns)", A)
b = PP.report("CONTROL (same R:R)", B)
if a is not None and b is not None:
    print(f"\n  edge over control: {(a-b):+.3f}R")
if len(A):
    print("\n  by pattern:")
    for nm, g in A.groupby("name"):
        R = PP.expectancy(g); res = g[g.resolved==1]
        print(f"    {nm:<22} n={len(g):4d}  hit {res.win.mean()*100 if len(res) else 0:5.1f}%  expectancy {R.mean():+.3f}R")
print("\n  Crypto registered (doc 39): patterns beat control; pass line +0.017R.")
