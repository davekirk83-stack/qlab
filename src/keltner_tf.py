"""
WHAT IS THE BEST TIMEFRAME FOR A KELTNER BAND TOUCH?

DK: "Clearly we need each idea to have an optimal timeframe."
    "Why not say - what's the most reliable timeframe for a Keltner channel
     line touch?"
    "Try every time frame - I literally don't care. We are trying to find out
     what does work."

Right question, and it reframes the job. Earlier runs picked 15-minute bars
because the MANDATE wants frequency, then reported that 15-minute bars did not
work. That measures my choice of timeframe, not the setup. Doc 66 found this
alive on hourly bars.

So this maps the thing instead of judging it. Every timeframe from 5 minutes to
daily, hold swept in BARS so it scales with the timeframe, and for each
timeframe the single best configuration is reported. The deliverable is a
curve: edge as a function of timeframe, with the peak identified.

Geometry held at target 1 ATR / stop 2 ATR for the main map so there is one
free axis, then the winning timeframe gets its own geometry sweep.
Same-regime time-matched control on every cell.

STANDING RULE: never test an idea at one timeframe and report the result as a
property of the idea.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

MAKER, TAKER, SLIP = 2/10000, 5/10000, 10/10000
RNG = np.random.default_rng(99)
STACK, LEV = 2000.0, 3.0

TFS = [("5min", 5), ("15min", 15), ("30min", 30), ("1h", 60),
       ("2h", 120), ("4h", 240), ("8h", 480), ("1D", 1440)]


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net / np.where(gross > 0, gross, np.nan)


_RAW = {}
def raw(folder):
    if folder not in _RAW:
        out = {}
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            out[os.path.basename(f)[:-4]] = d[["open", "high", "low", "close", "volume"]]
        _RAW[folder] = out
    return _RAW[folder]


def bars(folder, tf):
    return {s: d.resample(tf).agg(open=("open", "first"), high=("high", "max"),
            low=("low", "min"), close=("close", "last"), volume=("volume", "sum")).dropna()
            for s, d in raw(folder).items()}


def play(C, H, L, i, stop, tgt, maxh):
    n = len(C); e = C[i] * (1 + MAKER)
    for q in range(i + 1, min(i + 1 + maxh, n)):
        if L[q] <= stop: return (stop * (1 - SLIP - TAKER)) / e - 1
        if H[q] >= tgt:  return (tgt * (1 - MAKER)) / e - 1
    q = min(i + maxh, n - 1)
    return (C[q] * (1 - MAKER)) / e - 1


def run(data, maxh, eff_cut=0.30, t_atr=1.0, s_atr=2.0, minlen=400, kband=2.0):
    real = []; ctrl = []; days = 0.0; used = 0
    for s, d in data.items():
        if len(d) < minlen: continue
        used += 1
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); a = atr_np(H, L, C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - kband * a
        ok = efficiency(C) < eff_cut if eff_cut < 1 else np.ones(n, bool)
        trig = (C <= lower) & (np.roll(C, 1) > np.roll(lower, 1)) & ok
        days += (d.index[-1] - d.index[0]).total_seconds() / 86400
        elig = np.flatnonzero(ok & np.isfinite(a) & (np.arange(n) > 120))
        elig = elig[(elig > 120) & (elig < n - maxh - 2)]
        last = -10**9
        for i in np.flatnonzero(trig):
            if i < 120 or i > n - maxh - 2 or i - last < maxh: continue
            last = i
            real.append(play(C, H, L, i, C[i] - s_atr*a[i], C[i] + t_atr*a[i], maxh))
            if len(elig):
                q = int(RNG.choice(elig))
                ctrl.append(play(C, H, L, q, C[q] - s_atr*a[q], C[q] + t_atr*a[q], maxh))
    return np.array(real), np.array(ctrl), days / max(used, 1), used


def cell(data, maxh, **kw):
    r, c, dd, used = run(data, maxh, **kw)
    if len(r) < 60 or len(c) < 60: return None
    mo = dd / 30.44
    return dict(n=len(r), per=len(r)/mo, mean=r.mean(),
                t=r.mean()/(r.std(ddof=1)/np.sqrt(len(r))),
                ctrl=c.mean(), edge=r.mean()-c.mean(),
                te=(r.mean()-c.mean())/np.sqrt(r.var(ddof=1)/len(r)+c.var(ddof=1)/len(c)),
                win=(r > 0).mean(), dol=r.mean()*STACK*LEV*(len(r)/mo), used=used)


if __name__ == "__main__":
    print("KELTNER LOWER-BAND TOUCH — WHICH TIMEFRAME IS IT BEST ON?")
    print("target 1 ATR, stop 2 ATR, range regime (eff<0.30), 18 symbols,")
    print("same-regime time-matched control on every cell\n")
    print(f"{'bars':>6}{'hold':>5}{'=hrs':>7}{'n':>6}{'/mo':>6}{'net%':>9}{'t':>7}"
          f"{'ctrl%':>8}{'EDGE':>8}{'tEdge':>7}{'win%':>6}{'$/mo':>8}")
    cells = []
    for tf, mins in TFS:
        D = bars("/home/claude/qlab/data_1m", tf)
        shown = False
        for maxh in (4, 8, 16, 32, 64, 120):
            c = cell(D, maxh)
            if c is None: continue
            shown = True
            c.update(tf=tf, mins=mins, maxh=maxh)
            cells.append(c)
            print(f"{tf:>6}{maxh:>5}{maxh*mins/60:>7.1f}{c['n']:>6}{c['per']:>6.0f}"
                  f"{c['mean']*100:>+8.3f}%{c['t']:>+7.2f}{c['ctrl']*100:>+7.3f}%"
                  f"{c['edge']*100:>+7.3f}%{c['te']:>+7.2f}{c['win']*100:>5.0f}%"
                  f"{c['dol']:>8.0f}")
        if shown: print()

    print("=" * 92)
    print("BEST CELL AT EACH TIMEFRAME, ranked by edge over its control")
    print(f"{'bars':>6}{'hold':>5}{'best net%':>11}{'t':>7}{'EDGE':>9}{'tEdge':>7}"
          f"{'/mo':>6}{'$/mo':>8}")
    best_by_tf = {}
    for tf, _ in TFS:
        g = [x for x in cells if x["tf"] == tf]
        if not g: continue
        b = max(g, key=lambda x: x["edge"])
        best_by_tf[tf] = b
        print(f"{tf:>6}{b['maxh']:>5}{b['mean']*100:>+10.3f}%{b['t']:>+7.2f}"
              f"{b['edge']*100:>+8.3f}%{b['te']:>+7.2f}{b['per']:>6.0f}{b['dol']:>8.0f}")

    ranked = sorted(best_by_tf.items(), key=lambda kv: -kv[1]["edge"])
    print(f"\nTIMEFRAME RANKING BY EDGE: " +
          "  >  ".join(f"{k}({v['edge']*100:+.3f}%)" for k, v in ranked))
    win_tf, win = ranked[0]

    print(f"\n{'='*92}\nGEOMETRY SWEEP ON THE WINNING TIMEFRAME: {win_tf}, hold {win['maxh']} bars")
    D = bars("/home/claude/qlab/data_1m", win_tf)
    print(f"{'tgt':>5}{'stop':>6}{'band':>6}{'eff':>6}{'n':>6}{'/mo':>6}{'net%':>9}"
          f"{'t':>7}{'EDGE':>8}{'tEdge':>7}{'win%':>6}{'$/mo':>8}")
    g2 = []
    for t_atr in (0.5, 1.0, 2.0, 3.0):
        for s_atr in (1.0, 2.0, 3.0):
            for kband in (1.5, 2.0, 2.5):
                for eff_cut in (0.20, 0.30, 1.0):
                    c = cell(D, win["maxh"], t_atr=t_atr, s_atr=s_atr,
                             kband=kband, eff_cut=eff_cut)
                    if c is None: continue
                    c.update(t_atr=t_atr, s_atr=s_atr, kband=kband, eff=eff_cut)
                    g2.append(c)
    g2.sort(key=lambda x: -x["edge"])
    for c in g2[:15]:
        print(f"{c['t_atr']:>5.1f}{c['s_atr']:>6.1f}{c['kband']:>6.1f}{c['eff']:>6.2f}"
              f"{c['n']:>6}{c['per']:>6.0f}{c['mean']*100:>+8.3f}%{c['t']:>+7.2f}"
              f"{c['edge']*100:>+7.3f}%{c['te']:>+7.2f}{c['win']*100:>5.0f}%{c['dol']:>8.0f}")
    if g2:
        b = g2[0]
        print(f"\nBEST OVERALL CONFIGURATION")
        print(f"  {win_tf} bars, hold {win['maxh']}, target {b['t_atr']} ATR, "
              f"stop {b['s_atr']} ATR, band {b['kband']} ATR, eff<{b['eff']}")
        print(f"  {b['mean']*100:+.3f}%/trade  t={b['t']:+.2f}  "
              f"edge over control {b['edge']*100:+.3f}% (t={b['te']:+.2f})  "
              f"win {b['win']*100:.0f}%")
        print(f"  {b['per']:.0f} trades/month across 18 symbols  ->  "
              f"${b['dol']:.0f}/month on ${STACK:,.0f} at {LEV:.0f}x")
        np.save("/home/claude/qlab/runs/keltner_best.npy",
                np.array([b["t_atr"], b["s_atr"], b["kband"], b["eff"], win["maxh"]]))
        print(f"\n  config saved -> runs/keltner_best.npy (for the OOS run)")
