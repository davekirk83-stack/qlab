"""Monthly time-series momentum, short side only - the way trend-followers
actually run it: at each month-end, if the instrument is below its 10-month
average (variant: 12-month return < 0), short it for the next month. Hold the
month regardless. Versus random month-long shorts in the same instrument.
Optional ARMED gate: only while SPY is below its own 10-month average."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from equity_short import load, COST, BORROW, table
RNG = np.random.default_rng(5)

def monthly(px, rule, gate=None, sym=""):
    p = px.dropna(); m = p.resample("ME").last(); sma = m.rolling(10).mean(); mom = m/m.shift(12)-1
    sig = (m < sma) if rule == "sma" else (mom < 0)
    if gate is not None: sig &= gate.reindex(m.index).fillna(False).astype(bool)
    rows = []; idx = list(m.index)
    for k in range(12, len(idx)-1):
        if not sig.iloc[k]: continue
        e, x = m.iloc[k], m.iloc[k+1]
        days = (idx[k+1]-idx[k]).days
        rows.append((sym, idx[k], idx[k+1], (e*(1-COST)-x*(1+COST))/e - BORROW*days/365, days))
    return rows

def ctrl(px, real, sym=""):
    p = px.dropna(); m = p.resample("ME").last(); idx = list(m.index); rows = []
    for _ in real:
        k = int(RNG.integers(12, len(idx)-1)); e, x = m.iloc[k], m.iloc[k+1]
        days = (idx[k+1]-idx[k]).days
        rows.append((sym, idx[k], idx[k+1], (e*(1-COST)-x*(1+COST))/e - BORROW*days/365, days))
    return rows

spy = load("data_etf20")["SPY"]; sm = spy.resample("ME").last(); spy_gate = sm < sm.rolling(10).mean()
for folder, label in (("data_stocks20","78 STOCKS"),("data_etf20","37 ETFs")):
    P = load(folder); print("="*100); print(f"{label}, MONTHLY, short side only"); print("="*100)
    for name, rule, g in (("10m SMA, monthly","sma",None),("12m momentum<0, monthly","mom",None),
                          ("ARMED: 10m SMA & SPY<10m","sma",spy_gate),("ARMED: 12m mom & SPY<10m","mom",spy_gate)):
        R, C = [], []
        for s, px in P.items():
            r = monthly(px, rule, g, sym=s); R += r; C += ctrl(px, r, sym=s)
        table(name, R, C); print()
