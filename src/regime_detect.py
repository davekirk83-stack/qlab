"""
WHEN TO SWITCH TO RANGE TRADING — nine detectors, measured against each other.

DK: "I want you to create a reliable way of knowing when to switch to range
     trading."

Every book built today carries a hand-picked regime rule that was never tested
against an alternative. The quiet filter is simply the first thing I tried, and
finding 104 showed it costs 20% of per-trade return to buy tail protection -
a trade-off I accepted without checking whether a better detector exists that
gives the protection without the cost.

NINE CANDIDATES, all causal, all computed from trailing bars only:
  eff        Kaufman efficiency ratio over 100 bars. Low = churning.
  rvol       60-bar realised volatility, as a percentile of its own history.
  bandw      Keltner band width over price - are the bands tight?
  adx        Average Directional Index. Low = no trend.
  autocorr   lag-1 autocorrelation of returns over 100 bars. NEGATIVE means
             an up bar tends to be followed by a down bar - literal oscillation.
  varratio   variance ratio: var(10-bar returns) / (10 x var(1-bar returns)).
             Below 1 means mean-reverting, above 1 trending. The textbook test
             and the one nobody in retail uses.
  touches    how many times price crossed from one band to the other in the
             last 50 bars. The most literal reading of "clearly oscillating".
  contain    share of the last 50 bars whose close sat inside the bands.
  hurst      rescaled-range Hurst exponent. Below 0.5 = mean reverting.

JUDGED ON TWO THINGS, because either alone is misleading:

  1. SEPARATION. Run DK's range book when the detector says range, and when it
     says not-range. The gap between the two is what the detector is worth. A
     detector that fires on everything separates nothing.

  2. PERSISTENCE. Measure how long the state lasts once entered, and whether
     "ranging now" predicts "still ranging in 12 hours" - the horizon the book
     actually holds for. A detector with no persistence is describing the last
     bar, not a regime, and switching on it means switching constantly.

Each detector is split at its own median so none is flattered by a threshold
chosen to suit it.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

MK, TAKER, SLIP = 1.5/10000, 4.5/10000, 5/10000
BID = [(0.15, 0.30), (0.25, 0.05), (0.30, -0.25), (0.30, -0.55)]
ASK = [(0.4, "mid"), (0.4, 0.0), (1.0, 0.35)]
CAP = 48


def load(tf="15min"):
    out = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in out: continue
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            b = d[["open","high","low","close","volume"]].resample(tf).agg(
                open=("open","first"), high=("high","max"), low=("low","min"),
                close=("close","last"), volume=("volume","sum")).dropna()
            if len(b) > 3000: out[s] = b
    return out


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def hurst(x, maxlag=40):
    """Rescaled-range exponent via the lagged-variance method."""
    lags = np.arange(2, maxlag)
    tau = [np.sqrt(np.nanstd(np.subtract(x[l:], x[:-l]))) for l in lags]
    tau = np.array(tau)
    ok = np.isfinite(tau) & (tau > 0)
    if ok.sum() < 5: return np.nan
    return float(np.polyfit(np.log(lags[ok]), np.log(tau[ok]), 1)[0]*2.0)


def detectors(d):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); a = atr_np(H, L, C)
    ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
    lo_b, hi_b = ema-2*a, ema+2*a
    r = pd.Series(C).pct_change()
    D = {}
    # Kaufman efficiency
    net = np.abs(pd.Series(C).diff(100)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(100).sum().values
    D["eff"] = -net/np.where(gross > 0, gross, np.nan)      # sign flipped: high = ranging
    # realised vol, low = ranging
    D["rvol"] = -r.rolling(60).std().values
    # band width, tight = ranging
    D["bandw"] = -((hi_b-lo_b)/C)
    # ADX
    up = pd.Series(H).diff(); dn = -pd.Series(L).diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.Series(np.maximum(H-L, np.maximum(abs(H-np.roll(C,1)), abs(L-np.roll(C,1)))))
    atr14 = tr.rolling(14).mean()
    pdi = 100*pd.Series(pdm).rolling(14).mean()/atr14
    ndi = 100*pd.Series(ndm).rolling(14).mean()/atr14
    dx = 100*(pdi-ndi).abs()/(pdi+ndi).replace(0, np.nan)
    D["adx"] = -dx.rolling(14).mean().values                # low ADX = ranging
    # lag-1 autocorrelation, negative = oscillating
    # vectorised rolling corr(r, r.shift(1)) - the .apply version was the
    # single biggest cost in the first run and gives the same number
    r1 = r.shift(1)
    D["autocorr"] = -r.rolling(100).corr(r1).values
    # variance ratio, below 1 = reverting
    v1 = r.rolling(100).var()
    v10 = pd.Series(C).pct_change(10).rolling(100).var()
    D["varratio"] = -(v10/(10*v1)).values
    # band-to-band crossings in the last 50 bars
    above = pd.Series((C > hi_b).astype(float))
    below = pd.Series((C < lo_b).astype(float))
    side = (above - below).replace(0, np.nan).ffill()
    D["touches"] = side.diff().abs().rolling(50).sum().values
    # containment: share of last 50 closes inside the bands
    inside = ((C <= hi_b) & (C >= lo_b)).astype(float)
    D["contain"] = pd.Series(inside).rolling(50).mean().values
    # Hurst, below 0.5 = reverting
    lp = np.log(np.where(C > 0, C, np.nan))
    hv = np.full(n, np.nan)
    for i in range(200, n, 20):
        hv[i] = hurst(lp[i-200:i])
    D["hurst"] = -pd.Series(hv).ffill().values
    return D, ema, lo_b, hi_b, a


def run_book_timed(d, allow, ema, lo_b, hi_b, a):
    """Same book, but each result carries the bar index it was booked on, so
    P&L can be attributed to the regime window it fell inside."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    out = []; inv = []; opened_i = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append((i, (C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((i, ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz)))
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
                    if len(inv) == 1: opened_i = i
    return out


def run_book(d, allow, ema, lo_b, hi_b, a):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    out = []; inv = []; opened_i = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append((C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1)
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append(((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz))
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
                    if len(inv) == 1: opened_i = i
    return out


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} symbols, 15-minute bars. Each detector split at its own median.\n")
    names = ["eff","rvol","bandw","adx","autocorr","varratio","touches","contain","hurst"]
    prepared = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = detectors(d)
        prepared[s] = (d, D, ema, lo_b, hi_b, a)
    print(f"  {'detector':<12}{'ON: per trade':>15}{'n':>8}{'OFF: per trade':>16}{'n':>8}"
          f"{'SEPARATION':>13}{'persist 12h':>13}{'median run':>12}")
    rows = []
    for nm in names:
        on_r = []; off_r = []; pers = []; runs = []
        for s, (d, D, ema, lo_b, hi_b, a) in prepared.items():
            v = pd.Series(D[nm])
            med = v.expanding(500).median()
            allow = (v > med).values
            if np.isfinite(allow).sum() < 500: continue
            on_r += run_book(d, allow, ema, lo_b, hi_b, a)
            off_r += run_book(d, ~allow, ema, lo_b, hi_b, a)
            al = pd.Series(allow)
            pers.append(float((al & al.shift(-48)).sum()/max(al.sum(), 1)))
            grp = (al != al.shift()).cumsum()
            lens = [len(g) for _, g in al.groupby(grp) if g.iloc[0]]
            if lens: runs.append(float(np.median(lens)))
        if len(on_r) < 500 or len(off_r) < 500: continue
        on = np.array(on_r); off = np.array(off_r)
        sep = on.mean()-off.mean()
        rows.append((nm, on.mean(), len(on), off.mean(), len(off), sep,
                     np.mean(pers), np.mean(runs)))
        print(f"  {nm:<12}{on.mean()*100:>+14.4f}%{len(on):>8}{off.mean()*100:>+15.4f}%"
              f"{len(off):>8}{sep*100:>+12.4f}%{np.mean(pers)*100:>12.0f}%"
              f"{np.mean(runs):>12.0f}")
    print("\n  SEPARATION is what the detector is worth: how much better the book")
    print("  does when it says range than when it says not. PERSIST 12h is the")
    print("  chance the state still holds 48 bars later - the horizon the book")
    print("  holds for. A detector needs both.")
    if rows:
        rows.sort(key=lambda z: -z[5])
        b = rows[0]
        print(f"\n  BEST SEPARATION: {b[0]} — {b[5]*100:+.4f}% gap, "
              f"persists 12h {b[6]*100:.0f}% of the time, median run {b[7]:.0f} bars")
