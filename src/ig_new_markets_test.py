"""Doc 175 — new things to trade on IG (DK 1 Nov: "I'd like to find new things we can trade on IG"). Pre-registered before results.
Data: Dukascopy 5-min bars with delta, Nov 2025 - Oct 2026 (src/pull_duka_delta.py); the Nasdaq from data_nq_cache.
Scored as on a £500 account (doc 137): return on MARGIN per margin-hour, and against random entries.

A  RANGE v3 LADDER (paperbook6 engine unchanged, both sides, IG spread costs, 0.018%/night funding) on US 500, Wall Street, Germany 40,
   FTSE 100 (and gold, EUR/USD, GBP/USD, USD/JPY, WTI oil when their data exists), new episodes (a) in the market's own cash session,
   (b) at all hours. Control: book 8's time-matched random episodes (same side and hold, trailing 30 days, 5 each).
B  NEW YORK "SIDE" CONTINUATION (doc 105 C, queued since 20 Oct) on the US Tech 100 and US 500: overnight range = 18:00 (prior day) -
   09:30 NY. At 09:30 the nearer side is the expected target; when price takes that side (trades beyond it) before 11:30 NY, enter in
   its direction at the next bar open, stop at the opposite side of the first 30 minutes' range (at least 0.5 ATR), exit at 16:00 NY.
   Control: same entry time and direction, entered on a random day.
C  OVERNIGHT DRIFT on the US Tech 100 and US 500: long from the 16:00 NY close to the next 09:30 open, minus one night's funding and the
   spread; against the intraday half (09:30 - 16:00) and the random-day mean.
SPLIT: dev Nov 2025 - Apr 2026, holdout May - Oct 2026. A market or rule passes only if positive and ahead of its control in BOTH."""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
import paperbook6 as P6, paperbook8 as P8
OUT = open("runs/ig_new_markets_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
SPLIT = pd.Timestamp("2026-05-01", tz="UTC"); RNG = np.random.default_rng(175); FUND = 0.00018; MARGIN = 0.05
MK = {  # name: (file, IG spread pts in session, margin, own session tz and hours)
    "US Tech 100": ("data_nq_cache/nq_5m.csv", 1.0, 0.05, ("America/New_York", 9.5, 16)),
    "US 500": ("data_ign/USA500IDXUSD_5m.csv", 0.4, 0.05, ("America/New_York", 9.5, 16)),
    "Wall Street": ("data_ign/USA30IDXUSD_5m.csv", 2.0, 0.05, ("America/New_York", 9.5, 16)),
    "Germany 40": ("data_ign/DEUIDXEUR_5m.csv", 1.2, 0.05, ("Europe/London", 8, 16.5)),
    "FTSE 100": ("data_ign/GBRIDXGBP_5m.csv", 1.0, 0.05, ("Europe/London", 8, 16.5)),
    "Gold": ("data_ign/XAUUSD_5m.csv", 0.3, 0.05, ("America/New_York", 8.33, 13.5)),
    "EUR/USD": ("data_ign/EURUSD_5m.csv", 0.00006, 0.0333, ("Europe/London", 7, 17)),
    "GBP/USD": ("data_ign/GBPUSD_5m.csv", 0.00009, 0.0333, ("Europe/London", 7, 17)),
    "USD/JPY": ("data_ign/USDJPY_5m.csv", 0.007, 0.0333, ("Europe/London", 0, 17)),
    "Oil (WTI)": ("data_ign/LIGHTCMDUSD_5m.csv", 0.03, 0.10, ("America/New_York", 9, 14.5)),
}
def load5(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[~d.index.duplicated()].sort_index()
def to15(d): return pd.DataFrame({"open": d.open.resample("15min").first(), "high": d.high.resample("15min").max(), "low": d.low.resample("15min").min(), "close": d.close.resample("15min").last()}).dropna()
def gate(tz, h0, h1):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = P8._orig_ind(d, sym)
        if tz is None: return ema, lob, hib, a, allow
        t = d.index.tz_convert(tz); h = t.hour + t.minute / 60; return ema, lob, hib, a, allow & ((h >= h0) & (h < h1))
    return ind

log("A — RANGE v3 LADDER (return on margin per episode and per margin-hour; vs time-matched random)")
for name, (f, sp, mg, (tz, h0, h1)) in MK.items():
    if not os.path.exists(f): log(f"  {name}: no data yet"); continue
    b = to15(load5(f)); b = b[b.index >= "2025-11-01"]; px = float(b.close.median())
    P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
    for lab, g in (("own session", (tz, h0, h1)), ("all hours", (None, 0, 24))):
        P6.indicators = gate(*g); P6._MED = {}
        closed, _ = P6.step(name, b, {}, str(b.index[250]), [10**6]); P6.indicators = P8._orig_ind
        rows = []
        for c in closed:
            o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
            nights = max(0, (cl.normalize() - o.normalize()).days); r = c[4] - nights * FUND
            sh = P8.shadow(b, [c], RNG); rows.append((o, r, max((cl - o) / pd.Timedelta(hours=1), 0.25), np.mean(sh) if sh else np.nan))
        R = pd.DataFrame(rows, columns=["t", "r", "h", "c"])
        if not len(R): log(f"  {name:12} {lab:11}: no episodes"); continue
        cell = []
        for seg, m in (("dev", R.t < SPLIT), ("hold", R.t >= SPLIT)):
            x = R[m]
            if len(x) < 10: cell.append(f"{seg} n{len(x)}"); continue
            cell.append(f"{seg} n{len(x):4} {100*x.r.mean():+.3f}%/ep vs random {100*x.c.mean():+.3f}% win {100*(x.r>0).mean():.0f}%")
        rom = R.r / mg
        log(f"  {name:12} {lab:11} {len(R)/12:5.0f} ep/month, hold {R.h.mean():4.1f}h, return on margin {100*rom.mean():+.2f}%/ep = {100*rom.sum()/R.h.sum():+.3f}% per margin-hour | " + " || ".join(cell))
P6.MK, P6.TAKER, P6.SLIP = 1.5e-4, 4.5e-4, 5e-4

log("\nB — NEW YORK 'SIDE' CONTINUATION (R per trade; vs the same entry on random days)")
log("C — OVERNIGHT DRIFT (per night, after funding and spread)")
for name in ("US Tech 100", "US 500"):
    f, sp, mg, _ = MK[name]; d = load5(f); d = d[d.index >= "2025-10-25"]; t = d.index.tz_convert("America/New_York"); d = d.copy()
    d["nyd"] = t.normalize().tz_localize(None); d["m"] = t.hour * 60 + t.minute
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs())); d["atr"] = tr.rolling(20).mean()
    days = sorted(d.nyd.unique()); B = []; Cn = []; Ci = []
    for k in range(1, len(days)):
        day, prev = days[k], days[k - 1]
        ov = d[((d.nyd == prev) & (d.m >= 18 * 60)) | ((d.nyd == day) & (d.m < 9 * 60 + 30))]
        ses = d[(d.nyd == day) & (d.m >= 9 * 60 + 30) & (d.m < 16 * 60)]
        if len(ov) < 100 or len(ses) < 70: continue
        hi, lo = ov.high.max(), ov.low.min(); o = ses.open.iloc[0]; near = 1 if (hi - o) < (o - lo) else -1; lvl = hi if near == 1 else lo
        f30 = ses.iloc[:6]; stop_lvl = f30.low.min() if near == 1 else f30.high.max()
        win = ses[ses.m < 11 * 60 + 30]; hit = np.flatnonzero((win.high.values >= lvl) if near == 1 else (win.low.values <= lvl))
        if len(hit) and hit[0] + 1 < len(ses):
            j = hit[0] + 1; e = ses.open.iloc[j]; a = float(ses.atr.iloc[j]); stop = min(stop_lvl, e - 0.5 * a) if near == 1 else max(stop_lvl, e + 0.5 * a)
            risk = abs(e - stop); px_exit = ses.close.iloc[-1]
            for q in range(j, len(ses)):
                if (near == 1 and ses.low.iloc[q] <= stop) or (near == -1 and ses.high.iloc[q] >= stop): px_exit = stop; break
            if risk > 0: B.append((ses.index[j], ((px_exit - e) * near - sp) / risk, near, ses.m.iloc[j], risk))
        nxt = d[(d.nyd == days[k + 1]) & (d.m >= 9 * 60 + 30)] if k + 1 < len(days) else None
        if nxt is not None and len(nxt): Cn.append((ses.index[-1], (nxt.open.iloc[0] / ses.close.iloc[-1] - 1) - FUND - sp / ses.close.iloc[-1]))
        Ci.append((ses.index[0], ses.close.iloc[-1] / o - 1 - sp / o))
    Bd = pd.DataFrame(B, columns=["t", "R", "s", "m", "risk"])
    # control: same direction and clock time on a random other day, same risk distance
    ctl = []
    for t0, R0, s0, m0, rk in B:
        for _ in range(5):
            dd = days[RNG.integers(1, len(days))]; ses = d[(d.nyd == dd) & (d.m >= m0) & (d.m < 16 * 60)]
            if len(ses) < 2: continue
            e = ses.open.iloc[0]; stop = e - s0 * rk; px_exit = ses.close.iloc[-1]
            for q in range(len(ses)):
                if (s0 == 1 and ses.low.iloc[q] <= stop) or (s0 == -1 and ses.high.iloc[q] >= stop): px_exit = stop; break
            ctl.append((t0, ((px_exit - e) * s0 - sp) / rk))
    Cd = pd.DataFrame(ctl, columns=["t", "R"]); cell = []
    for seg, f_ in (("dev", lambda x: x.t < SPLIT), ("hold", lambda x: x.t >= SPLIT)):
        x = Bd[f_(Bd)]; y = Cd[f_(Cd)]
        cell.append(f"{seg} n{len(x):3} {x.R.mean():+.3f}R win {100*(x.R>0).mean():.0f}% vs random {y.R.mean():+.3f}R")
    log(f"  B {name:12} {len(Bd)/12:.1f} trades/month | " + " || ".join(cell))
    N = pd.DataFrame(Cn, columns=["t", "r"]); I = pd.DataFrame(Ci, columns=["t", "r"]); cell = []
    for seg, f_ in (("dev", lambda x: x.t < SPLIT), ("hold", lambda x: x.t >= SPLIT)):
        n_, i_ = N[f_(N)], I[f_(I)]
        cell.append(f"{seg} overnight {100*n_.r.mean():+.3f}%/night (up {100*(n_.r>0).mean():.0f}%) vs intraday {100*i_.r.mean():+.3f}%/day")
    log(f"  C {name:12} " + " || ".join(cell))
log("done")
