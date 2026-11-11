"""Doc 228 part 2 — the champions' set-ups on INTRADAY data, the way they were built (DK 07:48 "Continue work on these").
5-min bars: US Tech 100 (Dukascopy, 1 year, own spreads), US 500 / Wall Street / Germany 40 / FTSE 100 / GBP-USD / USD-JPY / gold (IG's own
prices, 7-12 months), gold 2021-2026 (Dukascopy 1-min -> 5-min, 5.5 years). Costs: IG's spread as one round-trip cost (std_books.IG_COST x price;
FX 0.9 pip / 0.7 pip). Cash session per market; every trade flat by the session close (day trades, as Williams and Crabel traded them).
Set-ups (all levels known before they trigger; a bracket triggered both ways in one 5-min bar counts as the worst case):
  CRABEL STRETCH : open +/- stretch (10-session average of min(high-open, open-low)); stop = the session open; exit at the close.
  CRABEL ORB 30  : first 30 minutes' high/low breakout; stop = the other side; exit at the close.
  ... each also only after an NR7 / NR4 session (narrowest range of the last 7 / 4), Crabel's own filter.
  WILLIAMS VB    : open +/- 0.5 x the previous session's range; stop = the other side; exit at the close.
  RASCHKE 80-20  : yesterday opened in its top 20% and closed in its bottom 20% (or the mirror) -> after today trades beyond yesterday's
                   extreme, a stop entry back through it; stop = today's extreme so far; exit at the close.
Report: n, points and R (R = the session's 10-day average range) per trade, win rate, first 60% vs last 40% (hold-out), months positive,
costs x1.5. The best working version of each, per market."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FR = {"NQ": .00004, "US500": .000075, "DOW": .00005, "DAX": .00006, "FTSE": .0001, "GOLD": .000075, "GOLD5Y": .000075}
SESS = {"NQ": ("America/New_York", 570, 960), "US500": ("America/New_York", 570, 960), "DOW": ("America/New_York", 570, 960),
        "DAX": ("Europe/Berlin", 540, 1050), "FTSE": ("Europe/London", 480, 990), "GOLD": ("Europe/London", 480, 990), "GOLD5Y": ("Europe/London", 480, 990),
        "GBPUSD": ("Europe/London", 480, 990), "USDJPY": ("Europe/London", 480, 990)}

def load(m):
    if m == "NQ":
        d = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[["open", "high", "low", "close"]]
    if m == "GOLD5Y":
        xs = []
        for f in sorted(glob.glob("data_long/XAUUSD/*.npz")):
            x = np.load(f)["x"]; day = pd.Timestamp(os.path.basename(f)[:10], tz="UTC")
            df = pd.DataFrame(x[:, 1:5] / 1000.0, columns=["open", "high", "low", "close"], index=day + pd.to_timedelta(x[:, 0], unit="s")); xs.append(df)
        d = pd.concat(xs); d = d[(d.high > 0) & (d.low > 0)]
        return d.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    f = {"US500": "USA500IDXUSD", "DOW": "USA30IDXUSD", "DAX": "DEUIDXEUR", "FTSE": "GBRIDXGBP", "GOLD": "XAUUSD", "GBPUSD": "GBPUSD_IG", "USDJPY": "USDJPY_IG"}[m]
    d = pd.read_csv(f"data_ig_cache/{f}_5m.csv"); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    return d[~d.index.duplicated()].sort_index()[["open", "high", "low", "close"]].astype(float)

def sessions(m):
    d = load(m); tz, o, c = SESS[m]; lt = d.index.tz_convert(tz); mm = lt.hour * 60 + lt.minute
    d = d[(mm >= o) & (mm < c) & (lt.dayofweek < 5)].copy(); d["day"] = d.index.tz_convert(tz).date; d["mm"] = (d.index.tz_convert(tz).hour * 60 + d.index.tz_convert(tz).minute) - o
    S = d.groupby("day").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"), n=("open", "size"))
    S = S[S.n >= 0.6 * S.n.median()]
    S["rng"] = S.h - S.l; S["avg10"] = S.rng.rolling(10).mean().shift(1); S["stretch"] = np.minimum(S.h - S.o, S.o - S.l).rolling(10).mean().shift(1)
    S["nr7"] = (S.rng == S.rng.rolling(7).min()).shift(1).fillna(False); S["nr4"] = (S.rng == S.rng.rolling(4).min()).shift(1).fillna(False)
    S["prng"] = S.rng.shift(1); S["ph"], S["pl"] = S.h.shift(1), S.l.shift(1)
    po = ((S.o - S.l) / S.rng).shift(1); pc = ((S.c - S.l) / S.rng).shift(1); S["b8020"] = (po >= .8) & (pc <= .2); S["s8020"] = (po <= .2) & (pc >= .8)
    cost = {"GBPUSD": 0.00009, "USDJPY": 0.007}.get(m)
    S["cost"] = cost if cost else FR[m] * S.o
    return d, S

def bracket(bars, up, dn, stop_up, stop_dn, sides=(1, -1), start=0):
    """bars: one session's 5-min bars (numpy O,H,L,C). Stop orders at up (long) / dn (short) from bar `start`. Returns (side, entry, exit) or None."""
    O, H, L, C = bars
    for k in range(start, len(O)):
        bu, bd = (1 in sides) and H[k] >= up, (-1 in sides) and L[k] <= dn
        if bu and bd: return (1, max(up, O[k]), stop_up)                                  # both ways in one bar: worst case
        if bu or bd:
            s = 1 if bu else -1; e = max(up, O[k]) if s == 1 else min(dn, O[k]); st = stop_up if s == 1 else stop_dn
            if (s == 1 and L[k] <= st) or (s == -1 and H[k] >= st): return (s, e, st)      # stopped in the entry bar (worst case)
            for q in range(k + 1, len(O)):
                if (s == 1 and L[q] <= st) or (s == -1 and H[q] >= st): return (s, e, min(st, O[q]) if s == 1 else max(st, O[q]))
            return (s, e, C[-1])
    return None

def run(m, S, d, setup, filt=None, sides=(1, -1), cm=1.0):
    out = []; g = dict(tuple(d.groupby("day")))
    for day, r in S.iterrows():
        if not np.isfinite(r.avg10) or day not in g or (filt is not None and not r[filt]): continue
        b = g[day]; bars = (b.open.values, b.high.values, b.low.values, b.close.values); res = None
        if setup == "stretch": res = bracket(bars, r.o + r.stretch, r.o - r.stretch, r.o, r.o, sides)
        elif setup == "williams": k = 0.5 * r.prng; res = bracket(bars, r.o + k, r.o - k, r.o - k, r.o + k, sides)
        elif setup == "orb30":
            n0 = int((b.mm < 30).sum())
            if n0 < 3 or n0 >= len(b): continue
            hi, lo = b.high.values[:n0].max(), b.low.values[:n0].min(); res = bracket(bars, hi, lo, lo, hi, sides, start=n0)
        elif setup == "8020":
            if not (r.b8020 or r.s8020): continue
            s = 1 if r.b8020 else -1
            if s not in sides: continue
            H, L = b.high.values, b.low.values
            beyond = np.nonzero(L < r.pl)[0] if s == 1 else np.nonzero(H > r.ph)[0]
            if not len(beyond): continue
            k0 = beyond[0] + 1
            if k0 >= len(b): continue
            ext = L[:k0].min() if s == 1 else H[:k0].max()
            res = bracket(bars, r.pl if s == 1 else np.inf, r.ph if s == -1 else -np.inf, ext, ext, (s,), start=k0)
        if res:
            s, e, x = res; pts = s * (x - e) - cm * r.cost; out.append((pd.Timestamp(day), s, pts, pts / r.avg10))
    return pd.DataFrame(out, columns=["t", "side", "pts", "R"])

def summary(t):
    if len(t) < 10: return None
    cut = t.t.iloc[int(len(t) * 0.6)]; dev, hold = t[t.t < cut], t[t.t >= cut]; mo = t.groupby(t.t.dt.to_period("M")).R.sum()
    tt = t.R.mean() / t.R.std() * np.sqrt(len(t)) if t.R.std() > 0 else 0
    return dict(n=len(t), R=t.R.mean(), pts=t.pts.mean(), t=tt, win=(t.R > 0).mean(), dev=dev.R.mean(), hold=hold.R.mean(), mpos=f"{(mo > 0).sum()}/{len(mo)}")

if __name__ == "__main__":
    MK = sys.argv[1:] or ["NQ", "US500", "DOW", "DAX", "FTSE", "GOLD", "GOLD5Y", "GBPUSD", "USDJPY"]
    VARS = [("Crabel stretch", "stretch", None), ("Crabel stretch after NR7", "stretch", "nr7"), ("Crabel stretch after NR4", "stretch", "nr4"),
            ("Crabel ORB 30", "orb30", None), ("Crabel ORB 30 after NR7", "orb30", "nr7"), ("Crabel ORB 30 after NR4", "orb30", "nr4"),
            ("Williams VB 0.5", "williams", None), ("Williams VB after NR4", "williams", "nr4"), ("Raschke 80-20", "8020", None)]
    rows = []
    for m in MK:
        d, S = sessions(m); print(f"\n== {m}: {len(S)} sessions {S.index[0]} .. {S.index[-1]}", flush=True)
        for nm, st, fl in VARS:
            for sides, sl in (((1, -1), "both"), ((1,), "long")):
                t = run(m, S, d, st, fl, sides); sm = summary(t)
                if not sm: continue
                c15 = run(m, S, d, st, fl, sides, cm=1.5).R.mean()
                rows.append(dict(market=m, setup=nm, sides=sl, **sm, c15=c15))
                ok = sm["R"] > 0 and sm["dev"] > 0 and sm["hold"] > 0 and c15 > 0
                print(f"  {'OK ' if ok else '   '}{nm:26s} {sl:4s} n {sm['n']:4d} | {sm['pts']:+8.2f} pts {sm['R']:+.3f} R (t {sm['t']:+.2f}) win {100 * sm['win']:.0f}% "
                      f"| first 60% {sm['dev']:+.3f} last 40% {sm['hold']:+.3f} | months + {sm['mpos']} | x1.5 {c15:+.3f}", flush=True)
    r = pd.DataFrame(rows); r.to_csv(f"runs/gate/champ/intraday_{'_'.join(MK) if sys.argv[1:] else 'all'}.csv", index=False)
