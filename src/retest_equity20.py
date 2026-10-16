"""Retest book (retest.py) on the 20-year ETF panel and the 79-stock panel.
Horizontal levels only; same paired break-vs-retest comparison and matched
random control as the crypto run. Fills the last '?' on doc 71's transfer map."""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import pandas as pd
import retest as RT

def loader(folder):
    def f(which):
        out = {}
        for p in sorted(glob.glob(f"/home/claude/qlab/{folder}/*.csv")):
            s = os.path.basename(p)[:-4]
            d = pd.read_csv(p, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
            d.index.name = "date"
            if len(d) > 600: out[s] = d
        return out
    return f

for folder, label in (("data_etf20", "ETFs, 20 years"), ("data_stocks20", "STOCKS (79), 20 years")):
    RT.load_universe = loader(folder)
    B, R, N, C = RT.run(label)
    RT.compare(B, R, N, C, label)
print("  Crypto (doc 58/71): retest entry no better than break entry; neither beat control cleanly.")
