"""
KELTNER v1 — the daily crypto book — on twenty years of ETFs.

DK: "Have you applied any of our other books to these other stocks, shares and
     commodities?" Only the range book had been. This is the daily Keltner
     book (paperbook.py, registered on 263 crypto products: 4,506 trades,
     +0.949%/trade, t=+7.49, 5 of 7 years profitable), run unchanged on the
     37-ETF panel. It is a DAILY book on DAILY data, so unlike the range book
     the timeframe fits without re-derivation.

Same rule throughout: buy the close that crosses below the lower Keltner band
while efficiency is under 0.30; target +0.5 ATR, stop -3 ATR, 16 bars max;
the whole book switched off when the equal-weight index of the universe is
below its own 200-day average, read a day late. ETF costs.
"""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd
import paperbook as PB

MK, TK, SL = 2/10000, 3/10000, 2/10000
GROUPS = {"energy":["USO","UNG","XLE"],"metals":["GLD","SLV","CPER","GDX","SLX","XME"],
          "agri":["DBA","CORN","WEAT"],"index":["SPY","QQQ","IWM","DIA"],
          "sectors":["XLF","XLK","XLV","XLU","XLP","XLI","XLB","XLY"],
          "bonds":["TLT","IEF","HYG","LQD","TIP"],
          "intl":["EEM","EFA","FXI","EWJ","EWZ"],"vol/fx":["VXX","UUP","FXE"]}

data = {}
for f in sorted(glob.glob("/home/claude/qlab/data_etf20/*.csv")):
    s = os.path.basename(f)[:-4]
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
    data[s] = d
C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
C = C[C.notna().sum(axis=1) >= 8]
idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
gate = (idx > idx.rolling(200).mean()).shift(1).fillna(False)

def book(d, sym, gated):
    Cc, H, L = d.close.values, d.high.values, d.low.values
    a = PB.atr_np(H, L, Cc); ema = pd.Series(Cc).ewm(span=20, adjust=False).mean().values
    lower = ema - PB.KBAND*a; eff = PB.efficiency(Cc)
    g = gate.reindex(d.index).fillna(False).values if gated else np.ones(len(d), bool)
    out = []; i = 150
    while i < len(Cc)-1:
        if (np.isfinite(a[i]) and a[i] > 0 and eff[i] < PB.EFF and g[i]
                and Cc[i] <= lower[i] and Cc[i-1] > lower[i-1]):
            px = Cc[i]*(1+MK); stop = Cc[i]-PB.S_ATR*a[i]; tgt = Cc[i]+PB.T_ATR*a[i]
            r = None
            for j in range(i+1, min(i+1+PB.HOLD, len(Cc))):
                if L[j] <= stop: r = (min(L[j], stop)*(1-SL-TK))/px - 1; how = "stop"; break
                if H[j] >= tgt: r = (tgt*(1-MK))/px - 1; how = "target"; break
            if r is None: j = min(i+PB.HOLD, len(Cc)-1); r = (Cc[j]*(1-TK))/px - 1; how = "time"
            out.append((sym, d.index[i], d.index[j], r, how)); i = j
        i += 1
    return out

print(f"{len(data)} ETFs, 20+ years, Keltner v1 unchanged.\n")
for gated, lbl in ((True, "WITH the 200-day gate (as registered)"), (False, "without the gate")):
    rows = []; per = {}
    for s, d in data.items():
        r = book(d, s, gated); per[s] = r; rows += r
    A = pd.DataFrame(rows, columns=["sym","entry","exit","ret","how"])
    print(f"{lbl}")
    print(f"  {'group':<10}{'trades':>8}{'per trade':>11}{'t':>7}{'win':>6}{'target':>8}{'stop':>7}{'worst':>9}")
    for g, syms in GROUPS.items():
        G = pd.DataFrame([x for s in syms for x in per.get(s, [])], columns=A.columns)
        if len(G) < 15: continue
        t = G.ret.mean()/(G.ret.std(ddof=1)/np.sqrt(len(G)))
        print(f"  {g:<10}{len(G):>8}{G.ret.mean()*100:>+10.3f}%{t:>+7.2f}{(G.ret>0).mean()*100:>5.0f}%"
              f"{(G.how=='target').mean()*100:>7.0f}%{(G.how=='stop').mean()*100:>6.0f}%{G.ret.min()*100:>+8.1f}%")
    t = A.ret.mean()/(A.ret.std(ddof=1)/np.sqrt(len(A)))
    print(f"  {'ALL':<10}{len(A):>8}{A.ret.mean()*100:>+10.3f}%{t:>+7.2f}{(A.ret>0).mean()*100:>5.0f}%"
          f"{(A.how=='target').mean()*100:>7.0f}%{(A.how=='stop').mean()*100:>6.0f}%{A.ret.min()*100:>+8.1f}%")
    A["yr"] = A.entry.dt.year
    yrs = A.groupby("yr").ret.agg(["sum","count"])
    print(f"  profitable years: {(yrs['sum']>0).sum()} of {len(yrs)}   "
          f"worst year {yrs['sum'].min()*100:+.1f}% ({yrs['sum'].idxmin()})   "
          f"best {yrs['sum'].max()*100:+.1f}% ({yrs['sum'].idxmax()})\n")
print("  Crypto registered figure: +0.949% per trade, t=+7.49, 5 of 7 years.")
