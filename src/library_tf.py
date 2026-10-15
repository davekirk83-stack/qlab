"""
THE WHOLE ELEMENT LIBRARY, RE-MEASURED ACROSS TIMEFRAMES.

DK: "Clearly we need each idea to have an optimal timeframe... and I don't just
     mean for K channels, I mean for everything."  "Re-run them all."

Every element in this library - all 86 of them, across 15 families - was
measured on HOURLY bars. One timeframe, chosen by me early on and never
revisited. Finding 88 showed what that costs: the Keltner band touch looked
dead at 15 minutes and carried a clean monotonic edge gradient rising to 4h.
Any element whose signal lives on a different clock has been mismeasured in
exactly the same way, and some of the elements rejected as weak may simply
have been read at the wrong bar size.

So: every element, at every timeframe from 15 minutes to daily.

METHOD - unchanged from the original library measurement, so the numbers are
comparable with what is already in the database:
  per-symbol    IC computed WITHIN each symbol, then averaged. A factor cannot
                win by sorting good coins from bad ones.
  demeaned      forward returns demeaned per bar across the panel, which strips
                market-wide drift.
  horizon       20 BARS, so the horizon scales with the timeframe rather than
                being fixed in wall-clock. That is the whole point: at 15min it
                is 5 hours, at 4h it is 3.3 days.
  split         first half vs second half, reported separately.
  trailing      no lookahead anywhere; the Nadaraya-Watson is one-sided.

ONE KNOWN EXCEPTION, from finding 87: a panel-wide variable (session clock,
weekend, turn-of-month) is annihilated by cross-sectional demeaning. Those are
tagged in the output rather than silently reported as zero.

Run as:  python library_tf.py <timeframe>
Writes:  runs/libtf_<timeframe>.csv
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd
from scipy import stats
import elements as EL
import elements_mktadv as MA

HORIZON = 20
MINLEN = {"15min": 4000, "30min": 3000, "1h": 2000, "2h": 1200,
          "4h": 700, "8h": 400, "1D": 150}
# panel-wide clock variables: demeaning destroys them by construction (doc 87)
CLOCK = ("cal_", "sess_in_", "sess_ldn_standing")


def load(tf):
    out = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in out: continue
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            b = d.resample(tf).agg(open=("open", "first"), high=("high", "max"),
                                   low=("low", "min"), close=("close", "last"),
                                   volume=("volume", "sum")).dropna()
            if len(b) >= MINLEN.get(tf, 1000):
                out[s] = b
    return out


def main(tf):
    data = load(tf)
    print(f"[{tf}] {len(data)} symbols, horizon {HORIZON} bars", flush=True)
    if not data:
        print(f"[{tf}] no symbol long enough"); return

    fwd = {}
    for s, d in data.items():
        fwd[s] = d.close.shift(-HORIZON) / d.close - 1
    F = pd.DataFrame(fwd)
    Fd = F.sub(F.mean(axis=1), axis=0)          # demeaned
    print(f"[{tf}] forward returns built", flush=True)

    feats = {}
    for i, (s, d) in enumerate(data.items(), 1):
        f = EL.build(d)
        f.update(MA.build(d))
        feats[s] = f
        if i % 10 == 0: print(f"[{tf}] elements {i}/{len(data)}", flush=True)

    names = sorted(set().union(*[set(v) for v in feats.values()]))
    rows = []
    for name in names:
        clock = any(name.startswith(c) for c in CLOCK)
        Y = F if clock else Fd                   # doc 87: clock vars use RAW
        ics = []; h1 = []; h2 = []
        for s, fe in feats.items():
            if name not in fe: continue
            x = pd.Series(fe[name], index=data[s].index)
            y = Y[s].reindex(x.index)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 300 or x[m].nunique() < 2: continue
            ics.append(stats.spearmanr(x[m], y[m]).statistic)
            k = m.sum() // 2
            a, b = x[m].iloc[:k], y[m].iloc[:k]
            c, e = x[m].iloc[k:], y[m].iloc[k:]
            if a.nunique() > 1: h1.append(stats.spearmanr(a, b).statistic)
            if c.nunique() > 1: h2.append(stats.spearmanr(c, e).statistic)
        if len(ics) < 10: continue
        ics = np.array(ics, float)
        ic = np.nanmean(ics)
        sd = np.nanstd(ics, ddof=1)
        rows.append(dict(tf=tf, name=name, family=EL.family(name)
                         if EL.family(name) != "other" else
                         next((v for k, v in MA.FAMILY.items()
                               if name.startswith(k)), "other"),
                         clock=int(clock), ic=ic,
                         t=ic / (sd / np.sqrt(len(ics))) if sd > 0 else np.nan,
                         agree=int((np.sign(ics) == np.sign(ic)).sum()),
                         total=len(ics),
                         ic_h1=np.nanmean(h1) if h1 else np.nan,
                         ic_h2=np.nanmean(h2) if h2 else np.nan,
                         nsym=len(data)))
    T = pd.DataFrame(rows)
    T["stable"] = (np.sign(T.ic_h1) == np.sign(T.ic_h2)).astype(int)
    os.makedirs("/home/claude/qlab/runs", exist_ok=True)
    T.to_csv(f"/home/claude/qlab/runs/libtf_{tf}.csv", index=False)
    print(f"[{tf}] DONE {len(T)} elements -> runs/libtf_{tf}.csv", flush=True)
    top = T.reindex(T.ic.abs().sort_values(ascending=False).index).head(10)
    for _, r in top.iterrows():
        print(f"[{tf}]   {r['name']:<22}{r['ic']:+.4f}  t={r['t']:+6.2f}  "
              f"{r['agree']}/{r['total']}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1h")
