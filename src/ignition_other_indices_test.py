"""Doc 174 — Ignition v1.1 on IG's other index markets (DK 1 Nov: "Yes please", to more trades through the tax-free IG account).
Pre-registered 1 Nov 2026 before any result. Data: Dukascopy ticks -> 5-min bars with tick-rule delta (src/pull_duka_delta.py),
Nov 2025 - Oct 2026: US 500 (USA500IDXUSD), Wall Street (USA30IDXUSD), Germany 40 (DEUIDXEUR), FTSE 100 (GBRIDXGBP); the Nasdaq-100
(data_nq_cache, the registered book) is run through the same code as the reference.
TRANSLATION, fixed before results (rule 188 — the engine as written, adapted only where units force it):
  - point constants (stop 45, breakeven 15, daily loss cap 200) scaled by the market's median 5-min ATR in US cash hours / the NQ's;
    ATR-based parts (trail 1 ATR, target 9 ATR, v1.1 stop 1.5 ATR) unchanged
  - delta-share threshold percentile-matched: the same share of bars clears it as clears 0.05 on the NQ (as done for IG's feed, doc 119)
  - costs: IG spread per side = half the IG cash-hours spread (US 500 0.4, Wall St 2.0, Germany 40 1.2, FTSE 1.0 pts), doubled outside
  - sessions: (a) the registered US cash hours with the 12-15 NY lunch skip, for all; (b) for Germany 40 and FTSE also their own cash
    session 08:00-16:30 London (no lunch skip)
CONTROL: 5 random entries per trade, same market, same session, same side, same management (book 7's shadow).
SPLIT: dev Nov 2025 - Apr 2026, holdout May - Oct 2026. Verdict per market: positive in both halves AND beats its control in both."""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
import paperbook7 as P7
OUT = open("runs/ignition_other_indices_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
RNG = np.random.default_rng(174); SPLIT = pd.Timestamp("2026-05-01", tz="UTC")
BASE = dict(STOP=P7.STOP, BE=P7.BE, LOSSCAP=P7.LOSSCAP, DSHARE=P7.DSHARE)
def load(path):
    d = pd.read_csv(path, index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    return d[~d.index.duplicated()].sort_index()
nq = load("data_nq_cache/nq_5m.csv"); nq = nq[nq.index >= "2025-11-01"]
def us_hours(ix):
    t = ix.tz_convert("America/New_York"); m = t.hour * 60 + t.minute
    return (m >= 9 * 60 + 30) & (m < 16 * 60)
def med_atr(d):
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    return float(tr.rolling(20).mean()[us_hours(d.index)].median())
NQ_ATR = med_atr(nq); NQ_FRAC = float(((nq.delta / nq.vol.replace(0, np.nan)).abs() >= BASE["DSHARE"]).mean())
def run(name, d, spread, session):
    k = med_atr(d) / NQ_ATR
    P7.STOP, P7.BE, P7.LOSSCAP = BASE["STOP"] * k, BASE["BE"] * k, BASE["LOSSCAP"] * k
    P7.DSHARE = float((d.delta / d.vol.replace(0, np.nan)).abs().dropna().quantile(1 - NQ_FRAC))
    f = P7.features(d)
    if session == "US": ins = us_hours(f.index); t = f.index.tz_convert("America/New_York"); skip = np.isin(t.hour, P7.V11_SKIP_HOURS)
    else:
        t = f.index.tz_convert("Europe/London"); m = t.hour * 60 + t.minute; ins = (m >= 8 * 60) & (m < 16 * 60 + 30); skip = np.zeros(len(f), bool)
    f["cost"] = np.where(ins, spread / 2, spread)
    O, H, L, C, cost, atr, sig, day, idx = f.open.values, f.high.values, f.low.values, f.close.values, f.cost.values, f.atr.values, f.sig.values, f.day.values, f.index
    ok = ins & ~skip; trades = []; last = -10**9; cur = None; ntr = 0; dpl = 0
    for i in range(300, len(C) - 1):
        if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0
        s = int(sig[i])
        if s == 0 or not ok[i] or np.isnan(atr[i]) or i < last + P7.COOL or ntr >= P7.MAXT or dpl <= -P7.LOSSCAP: continue
        sp = max(P7.STOP, P7.V11_STOP_ATR * atr[i]); r = P7.manage(O, H, L, C, cost, atr, i, s, len(C), sp)
        if r is None: break
        last = i + r[1]; ntr += 1; dpl += r[0]
        ctl = []
        pool = np.flatnonzero(ok & ~np.isnan(atr)); pool = pool[(pool > 300) & (pool < len(C) - 40)]
        for _ in range(5):
            j = int(RNG.choice(pool)); rc = P7.manage(O, H, L, C, cost, atr, j, s, len(C), max(P7.STOP, P7.V11_STOP_ATR * atr[j]))
            if rc: ctl.append(rc[0] / max(P7.STOP, P7.V11_STOP_ATR * atr[j]))
        trades.append((idx[i], r[0] / sp, np.mean(ctl) if ctl else np.nan, r[1] * 5))
    for kk, v in BASE.items(): setattr(P7, kk, v)
    T = pd.DataFrame(trades, columns=["t", "R", "ctl", "mins"])
    cell = []
    for seg, m in (("dev", T.t < SPLIT), ("hold", T.t >= SPLIT)):
        x = T[m]
        if len(x) < 5: cell.append(f"{seg} n{len(x)}"); continue
        tt = x.R.mean() / (x.R.std() / np.sqrt(len(x)))
        cell.append(f"{seg} n{len(x):3} {x.R.mean():+.3f}R (t {tt:+.1f}) win {100*(x.R>0).mean():.0f}% | random {x.ctl.mean():+.3f}R edge {x.R.mean()-x.ctl.mean():+.3f}R")
    log(f"{name:28} scale x{k:.2f} dshare>={P7.DSHARE if False else ''}{'':0} trades/month {len(T)/12:4.1f} avg hold {T.mins.mean():.0f} min | " + " || ".join(cell))
    return T
log(f"IGNITION v1.1 ON IG INDEX MARKETS — Nov 2025 to Oct 2026 (NQ median 5-min ATR {NQ_ATR:.1f} pts; {100*NQ_FRAC:.1f}% of NQ bars clear the 0.05 delta share)")
run("US Tech 100 (reference)", nq, 1.0, "US")
for name, f, sp in (("US 500", "USA500IDXUSD", 0.4), ("Wall Street", "USA30IDXUSD", 2.0), ("Germany 40", "DEUIDXEUR", 1.2), ("FTSE 100", "GBRIDXGBP", 1.0)):
    p = f"data_ign/{f}_5m.csv"
    if not os.path.exists(p): log(f"{name}: no data"); continue
    d = load(p)
    run(f"{name} — US hours", d, sp, "US")
    if f in ("DEUIDXEUR", "GBRIDXGBP"): run(f"{name} — own session", d, sp, "EU")
log("done")
