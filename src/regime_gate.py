"""
DOES THE LADDER WORK ONCE IT IS TOLD WHAT THE MARKET IS DOING?

The confluence ladder passed its shuffled control - alignment is real structure
- but flipped sign between the fit and held-out windows at every rung count.
Read together with the Keltner result (edge over control positive in all three
calendar thirds, net profit in only two) the diagnosis is the same both times:
the library is entirely reversion-signed, reversion pays in some regimes and
not others, and alignment AMPLIFIES whichever is happening rather than
predicting it.

An amplifier with no gate is a liability. An amplifier with a gate is position
sizing. So this is the test that decides whether DK's funnel is taken forward.

THE GATE - market-wide, not per-symbol. Every regime filter in this programme
so far (Kaufman efficiency inside the Keltner book) has been computed per
symbol, and finding 89 showed what separates the good periods is market-WIDE
conditions. Three candidates, all causal, all computed from trailing data on
the entry bar and lagged one bar before use:

  breadth    share of symbols above their own 100-bar mean
  dispersion cross-sectional stdev of 24-bar returns - high means symbols are
             moving independently, low means one factor is driving everything
  mkt_eff    Kaufman efficiency of the equal-weight index. High = the market
             is going somewhere, which is when reversion should fail.

THE TEST. Forward return in the ladder's direction, split by rung count AND by
gate tercile, in the fit window and the held-out window side by side. The
claim is specific and falsifiable: if alignment amplifies the regime, the
spread between high-alignment cells should widen with the gate and the SIGN
should be set by the gate, consistently in both periods. If the gate cannot
recover a consistent sign, the funnel is not taken forward.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

PANEL = "/home/claude/qlab/runs/confluence_panel.csv"
LADDER = ["1D", "8h", "4h", "1h", "15min"]
SPLIT = "2026-05-01"
ENTRY = "1h"


def market_state():
    """Market-wide regime series on the 1h bar, from the same universe."""
    closes = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in closes: continue
            d = pd.read_csv(f, usecols=["t", "close"])
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            closes[s] = d.close.resample(ENTRY).last()
    C = pd.DataFrame(closes).sort_index()
    r24 = C.pct_change(24)
    above = (C > C.rolling(100, min_periods=40).mean()).sum(axis=1) / C.notna().sum(axis=1)
    disp = r24.std(axis=1)
    idx = C.div(C.iloc[0]).mean(axis=1)
    net = idx.diff(100).abs()
    gross = idx.diff().abs().rolling(100).sum()
    eff = net / gross.replace(0, np.nan)
    M = pd.DataFrame({"breadth": above, "dispersion": disp, "mkt_eff": eff})
    M = M.shift(1)
    M.index.name = "ts"
    return M          # known only after the bar closes


def tercile(s):
    """Expanding tercile so no future information sets the cut points."""
    q1 = s.expanding(400).quantile(1/3)
    q2 = s.expanding(400).quantile(2/3)
    return np.where(s <= q1, "low", np.where(s <= q2, "mid", "high"))


def report(T, gate, tag):
    print(f"\n  {tag}  —  gate: {gate}")
    print(f"    {'rungs':>6}{'gate':>7}{'n':>8}{'signed fwd':>13}{'t':>8}{'win%':>7}")
    out = {}
    for k in (3, 4, 5):
        for lvl in ("low", "mid", "high"):
            g = T[(T["nagree"] == k) & (T[gate + "_t"] == lvl)]
            if len(g) < 300: continue
            m = g["signed"].mean()
            t = m / (g["signed"].std(ddof=1) / np.sqrt(len(g)))
            out[(k, lvl)] = (m, t, len(g))
            print(f"    {k:>6}{lvl:>7}{len(g):>8}{m*100:>+12.3f}%{t:>+8.2f}"
                  f"{(g['signed']>0).mean()*100:>6.1f}%")
    return out


if __name__ == "__main__":
    T = pd.read_csv(PANEL, parse_dates=["ts"])
    sgn = np.sign(T[LADDER].values)
    T["nup"] = (sgn > 0).sum(axis=1); T["ndn"] = (sgn < 0).sum(axis=1)
    T["nagree"] = np.maximum(T["nup"], T["ndn"])
    T["dir"] = np.where(T["nup"] >= T["ndn"], 1, -1)
    T["signed"] = T["fwd"] * T["dir"]
    print(f"panel: {T.sym.nunique()} symbols, {len(T):,} rows")

    M = market_state()
    for c in ("breadth", "dispersion", "mkt_eff"):
        M[c + "_t"] = tercile(M[c])
    T = T.merge(M.reset_index(), on="ts", how="left")
    print(f"gates merged; coverage {T.breadth.notna().mean()*100:.0f}%\n")
    T = T.dropna(subset=["breadth", "dispersion", "mkt_eff"])

    FIT = T[T.ts < SPLIT]; OOS = T[T.ts >= SPLIT]
    print(f"fit {len(FIT):,} rows   held out {len(OOS):,} rows")

    for gate in ("mkt_eff", "breadth", "dispersion"):
        print(f"\n{'='*92}")
        a = report(FIT, gate, "FIT WINDOW")
        b = report(OOS, gate, "HELD OUT")
        print(f"\n    CONSISTENCY — does the gate set the same sign in both periods?")
        same = tot = 0
        for key in sorted(set(a) & set(b)):
            tot += 1
            s = np.sign(a[key][0]) == np.sign(b[key][0])
            same += s
            print(f"      {key[0]} rungs / {key[1]:<5} fit {a[key][0]*100:+.3f}%  "
                  f"oos {b[key][0]*100:+.3f}%   {'SAME' if s else 'flip'}")
        print(f"      -> {same}/{tot} cells keep their sign across the split")
