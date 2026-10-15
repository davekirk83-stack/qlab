"""
CHANGING GEAR — timeframe as the response to volatility, not an on/off switch.

DK: "Perhaps when it gets louder you swap to the 4 hour keltners for better
     profits and safety in the wider range."

This reconciles the disagreement rather than settling it, and it fits what the
element library already found: measured net of costs, 15-minute was the WORST
timeframe of the seven tested (IR -4.85) while 4h and above were positive.

The idea in plain terms. A Keltner band is a fixed number of ATRs around a
moving average, so it is always "wide enough" in its own units. But the noise
that breaks a range does not scale with the bar - a single violent minute
blows through a 15-minute band and barely marks a 4-hour one. So a loud
15-minute chart is not necessarily a bad range. It can be a real range being
measured on too fine a grid, where ordinary chop registers as a breakdown and
the book keeps getting liquidated out of a position that was going to work.

If that is what is happening, then as volatility rises the BEST TIMEFRAME
SHIFTS OUT, and the right response to a loud market is a coarser grid rather
than no trade at all. If it is not happening, the quiet-only filter is simply
correct and this is a dead end - which is equally worth knowing.

THE GRID: volatility tercile (measured identically across all timeframes, from
the 15-minute series, so the buckets mean the same thing in every row) against
the chart the book runs on: 15m, 30m, 1h, 2h, 4h, 8h.

Break exits are filled at the worst tick in the bar throughout, per the fill
test - and that penalty grows with timeframe, since a 4-hour bar's low is much
further from its close. That is deliberate. A coarser grid has to beat a finer
one while paying honestly for the wider bar it exits into.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK = RD.BID, RD.ASK
TFS = [("15min", 48), ("30min", 24), ("1h", 12), ("2h", 12), ("4h", 12), ("8h", 12)]


def load_raw():
    out = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in out: continue
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            out[s] = d[["open", "high", "low", "close", "volume"]]
    return out


def resample(raw, tf):
    return raw.resample(tf).agg(open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), volume=("volume", "sum")).dropna()


def book(d, allow, cap, volser):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); a = RD.atr_np(H, L, C)
    ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
    lo_b, hi_b = ema-2*a, ema+2*a
    out = []; inv = []; opened_i = 0; sold = set(); v0 = np.nan
    for i in range(120, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= cap or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append(((L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, v0, i-opened_i))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), v0, i-opened_i))
                    sold.add(k)
                    inv = [(p, s*(1-sell/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: sold = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: opened_i = i; v0 = volser[i]
    return out


if __name__ == "__main__":
    raw = load_raw()
    raw = {s: d for s, d in raw.items() if len(d) > 60000}
    print(f"{len(raw)} symbols. Volatility measured on the 15-minute series "
          f"throughout, so the buckets mean the same thing in every row.")
    print("Break exits filled at the worst tick in the bar — a penalty that grows")
    print("with timeframe, which the coarser grids have to overcome.\n")

    # one common volatility clock, from 15-minute bars
    vol15 = {}
    for s, d in raw.items():
        b = resample(d, "15min")
        rv = b.close.pct_change().rolling(60).std().rank(pct=True)
        vol15[s] = rv

    print(f"  {'chart':<9}{'bucket':<9}{'trades':>9}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'@3x':>9}{'med bars':>10}{'total P&L':>12}")
    grid = {}
    for tf, cap in TFS:
        for s, d in raw.items():
            pass
        allres = []
        for s, d in raw.items():
            b = resample(d, tf)
            if len(b) < 600: continue
            v = vol15[s].reindex(b.index, method="ffill").values
            D, ema, lo_b, hi_b, a = RD.detectors(b)
            cv = pd.Series(D["contain"])
            allow = (cv > cv.expanding(300).median()).values
            allres += book(b, allow, cap, v)
        if len(allres) < 300: continue
        R = pd.DataFrame(allres, columns=["ret", "vol", "bars"]).dropna()
        for lbl, lo, hi in (("quiet", 0, 1/3), ("middle", 1/3, 2/3), ("loud", 2/3, 1.01)):
            g = R[(R.vol >= lo) & (R.vol < hi)]
            if len(g) < 100: continue
            t = g.ret.mean()/(g.ret.std(ddof=1)/np.sqrt(len(g)))
            grid[(tf, lbl)] = (g.ret.mean(), g.ret.min(), len(g), g.ret.sum())
            print(f"  {tf:<9}{lbl:<9}{len(g):>9}{g.ret.mean()*100:>+11.4f}%"
                  f"{t:>+8.2f}{(g.ret>0).mean()*100:>5.0f}%{g.ret.min()*100:>+8.1f}%"
                  f"{g.ret.min()*3*100:>+8.0f}%{g.bars.median():>10.0f}"
                  f"{g.ret.sum()*100:>+11.0f}%")
        print()

    print("="*92)
    print("THE GEAR CHANGE — best chart for each condition")
    print("="*92)
    print(f"  {'bucket':<10}{'best per trade':<34}{'best worst-case':<34}")
    for lbl in ("quiet", "middle", "loud"):
        cells = {tf: grid[(tf, lbl)] for tf, _ in TFS if (tf, lbl) in grid}
        if not cells: continue
        bp = max(cells.items(), key=lambda z: z[1][0])
        bw = max(cells.items(), key=lambda z: z[1][1])
        print(f"  {lbl:<10}{bp[0]+'  '+format(bp[1][0]*100,'+.4f')+'%':<34}"
              f"{bw[0]+'  '+format(bw[1][1]*100,'+.1f')+'%':<34}")
    print("\n  If the best chart moves OUT as the market gets louder, DK's gear")
    print("  change is right and the response to volatility is a coarser grid.")
    print("  If 15-minute wins everywhere, the quiet-only filter is the answer.")
