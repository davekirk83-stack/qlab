"""Doc 169 — a combined book for the £500 IG account (DK 1 Nov: "With everything we have learned so far, is there any way to create a
new combined book of maximum effectiveness?" ... "Yes"). Pre-registered 1 Nov 2026 before any result.
ENGINES (only those tradeable on IG spread bets; crypto engines stay research-only — no cheap UK venue):
  IGN   Ignition v1.1, US Tech 100, US hours, no lunch, stop max(45, 1.5 ATR)        risk 2% of equity per trade (rule 186)
  RNG   Range v3 on US Tech 100, NY hours, mid-EMA exit, ladder                       15% of equity as margin per episode
  NEWS  News-day fade, US Tech 100, CPI + FOMC, 15-min wait (doc 156)                 risk 1% per trade (FOMC = explicit blackout exception)
  MV    Minervini VCP pivots, US stocks (book 11 MV), only when above the daily cloud (doc 165)   risk 0.5%, max 10 open
  ETF   Daily trend-line retest, practitioner rules, 60 ETFs (book 12 / doc 168)       risk 1%, max 20 open
POOL (doc 95 / rule 171 / rule 186): one equity, each engine sizes off CURRENT realised equity; total margin <= 60% of equity (a new
  trade is scaled to fit, skipped if under a quarter of its intended size); one engine <= 40% of equity in margin; risk halved while
  equity is >10% below its high; a day whose realised loss reaches -4% takes no further entries; Fed blackout (30 min before to 60 min
  after a 2pm FOMC statement) on IGN and RNG entries.
COSTS: IG spreads (US Tech 100 1 pt in US hours), shares 0.20%/side + 6.5%/yr funding, ETFs 0.05%/side + 6.5%/yr funding; margin 5% index,
  20% shares/ETFs.
WINDOW: the 12 months where every engine has data (Nov 2025 - Oct 2026), start £500. Variants A..F add engines one at a time.
CAVEAT carried from doc 137: Ignition v1.1's lunch skip and stop were fitted on this same year; plan on a third to a half of the result."""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
import paperbook7 as P7, paperbook6 as P6, paperbook8 as P8, news_fade_test as NF
MARGIN = 0.05; FUND_NIGHT = 0.00018
OUT = open("runs/combined_ig_book_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
FOMC_T = [pd.Timestamp(d + " 14:00", tz="America/New_York").tz_convert("UTC") for d in NF.FOMC]
def blackout(t):
    t = pd.Timestamp(t); t = t.tz_localize("UTC") if t.tzinfo is None else t
    return any(T - pd.Timedelta(minutes=30) <= t <= T + pd.Timedelta(minutes=60) for T in FOMC_T)
T = []   # (eng, t_open, t_close, payload)
# ---------------- Ignition v1.1
bars = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d = P7.features(bars); _ny = d.index.tz_convert(P7.NY); m = _ny.hour * 60 + _ny.minute
d["cost"] = np.where((m >= P7.US_OPEN) & (m < P7.US_CLOSE), 0.5, 1.0)
O, H, L, C, cost, atr, sig, day, idx = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values, d.atr.values, d.sig.values, d.day.values, d.index
last = -10**9; cur = None; ntr = 0; dpl = 0
for i in range(300, len(C) - 1):
    if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0
    s = int(sig[i]); t = P7.ny(idx[i]); mm = t.hour * 60 + t.minute
    if s == 0 or np.isnan(atr[i]) or i < last + P7.COOL or ntr >= P7.MAXT or dpl <= -P7.LOSSCAP: continue
    if not (P7.US_OPEN <= mm < P7.US_CLOSE) or t.hour in P7.V11_SKIP_HOURS: continue
    sp = max(P7.STOP, P7.V11_STOP_ATR * atr[i]); r = P7.manage(O, H, L, C, cost, atr, i, s, len(C), sp)
    if r is None: break
    last = i + r[1]; ntr += 1; dpl += r[0]
    if blackout(idx[i + 1]): continue
    T.append(("IGN", idx[i + 1], idx[min(i + 1 + r[1], len(C) - 1)], dict(pts=r[0], stop=sp, px=C[i])))
# ---------------- Range v3, US Tech 100 NY hours
name = "NQ"; path, sp_, src, hours = P8.INSTR[name]
b = P8.load(name); P8.set_costs(name, b); P6.indicators = P8.hours_gate(hours); P6._MED = {}
closed, _ = P6.step(name, b, {}, str(b.index[250]), [10**6]); P6.indicators = P8._orig_ind
for c in closed:
    o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
    if blackout(o): continue
    nights = max(0, (cl.normalize() - o.normalize()).days)
    T.append(("RNG", o, cl, dict(ret=c[4] - nights * FUND_NIGHT)))
# ---------------- News-day fade, US Tech 100 (CPI + FOMC), 15-minute wait — entry and exit times recovered
for dstr, kind, TT in NF.EVENTS:
    f = f"{NF.CACHE}/NQ_{TT:%Y%m%d%H%M}.csv"
    if not os.path.exists(f): continue
    dd = pd.read_csv(f, parse_dates=["t"]).set_index("t"); dd.index = dd.index.tz_localize("UTC") if dd.index.tz is None else dd.index
    r = NF.simulate(dd, TT, 15, lambda p: 1.0)
    if r is None: continue
    T.append(("NEWS", TT + pd.Timedelta(minutes=20), TT + pd.Timedelta(hours=4), dict(R=r[0], px=float(dd.close.iloc[0]))))
# ---------------- daily engines (combo_streams.py)
for eng, f in (("MV", "runs/combo/mv.csv"), ("ETF", "runs/combo/etf.csv")):
    x = pd.read_csv(f, parse_dates=["t_open", "t_close"])
    for r in x.itertuples():
        to = pd.Timestamp(r.t_open).tz_localize("America/New_York") + pd.Timedelta(hours=11)      # MV: after the first hour
        if eng == "ETF": to = pd.Timestamp(r.t_open).tz_localize("America/New_York") + pd.Timedelta(hours=16)
        tc = pd.Timestamp(r.t_close).tz_localize("America/New_York") + pd.Timedelta(hours=16)
        if eng == "MV": T.append(("MV" if r.cloud else "MVx", to.tz_convert("UTC"), tc.tz_convert("UTC"), dict(R=r.R, rf=r.risk)))
        else: T.append(("ETF", to.tz_convert("UTC"), tc.tz_convert("UTC"), dict(R=r.R, rf=r.risk)))
T = [t for t in T if t[1] >= pd.Timestamp("2025-11-01", tz="UTC") and t[1] < pd.Timestamp("2026-10-31", tz="UTC")]
log("trades in the window: " + ", ".join(f"{e} {sum(1 for t in T if t[0] == e)}" for e in ("IGN", "RNG", "NEWS", "MV", "MVx", "ETF")))

def sim(engs, start=500.0, r_ign=0.02, rng_frac=0.15, r_news=0.01, r_mv=0.005, r_etf=0.01, maxmv=10, maxetf=20):
    ev = sorted([t for t in T if t[0] in engs], key=lambda t: t[1])
    eq = start; hi = start; open_ = []; daily = {}; contrib = {e: 0.0 for e in engs}; taken = {e: 0 for e in engs}; mdd = 0.0
    def settle(upto):
        nonlocal eq, hi, mdd
        open_.sort(key=lambda p: p["tc"])
        while open_ and open_[0]["tc"] <= upto:
            p = open_.pop(0); eq += p["pnl"]; contrib[p["eng"]] += p["pnl"]; dk = p["tc"].date(); daily[dk] = daily.get(dk, 0) + p["pnl"]
            hi = max(hi, eq); mdd = min(mdd, eq / hi - 1)
    for eng, to, tc, pl in ev:
        settle(to)
        if eq <= 50: break
        dk = to.date(); sod = eq - daily.get(dk, 0)
        if daily.get(dk, 0) <= -0.04 * sod: continue
        k = 0.5 if eq < 0.9 * hi else 1.0
        used = sum(p["m"] for p in open_); used_e = sum(p["m"] for p in open_ if p["eng"] == eng)
        if eng == "IGN":
            stake = eq * r_ign * k / pl["stop"]; m = stake * pl["px"] * MARGIN; pnl_unit = stake * pl["pts"]
        elif eng == "RNG":
            m = eq * rng_frac * k; pnl_unit = m / MARGIN * pl["ret"]
        elif eng == "NEWS":
            m = eq * r_news * k * 40 * MARGIN; pnl_unit = eq * r_news * k * pl["R"]           # stop ~0.25% of price -> ~40x risk notional
        else:
            if sum(1 for p in open_ if p["eng"] == eng) >= (maxmv if eng.startswith("MV") else maxetf): continue
            rr = (r_mv if eng.startswith("MV") else r_etf) * k; m = eq * rr / max(pl["rf"], 0.005) * 0.20; pnl_unit = eq * rr * pl["R"]
        room = min(0.60 * eq - used, 0.40 * eq - used_e)
        if room <= 0: continue
        f = min(1.0, room / m) if m > 0 else 1.0
        if f < 0.25: continue
        open_.append(dict(eng=eng, tc=tc, m=m * f, pnl=pnl_unit * f)); taken[eng] += 1
    settle(pd.Timestamp("2100-01-01", tz="UTC"))
    s = pd.Series(daily).sort_index(); s.index = pd.to_datetime(s.index)
    mon = s.groupby(s.index.to_period("M")).sum()
    eqc = start + s.cumsum(); mon_ret = (eqc.groupby(eqc.index.to_period("M")).last() / eqc.groupby(eqc.index.to_period("M")).last().shift(1).fillna(start) - 1)
    return eq, mdd, (mon > 0).sum(), len(mon), mon_ret.min(), contrib, taken
log("\nCOMBINED IG BOOK — 12 months Nov 2025 - Oct 2026, start £500 (backtest, not a forecast)")
for lab, engs in (("A  Ignition alone", ["IGN"]), ("B  + Range NQ (doc 137 plan)", ["IGN", "RNG"]), ("C  + News fade", ["IGN", "RNG", "NEWS"]),
                  ("D  + Minervini (cloud)", ["IGN", "RNG", "NEWS", "MV"]), ("E  + ETF retest  = FULL", ["IGN", "RNG", "NEWS", "MV", "ETF"]),
                  ("E' full, Minervini without the cloud", ["IGN", "RNG", "NEWS", "MV", "MVx", "ETF"]), ("F  daily engines only (MV+ETF)", ["MV", "ETF"])):
    eq, dd, pm, nm, wm, con, tk = sim(engs)
    log(f"  {lab:38} end £{eq:,.0f} ({100*(eq/500-1):+.0f}%) maxDD {100*dd:.0f}% | months up {pm}/{nm}, worst month {100*wm:+.1f}% | "
        + " ".join(f"{e} £{v:+.0f} (n{tk[e]})" for e, v in con.items()))
log("\nSensitivity (FULL book): risk per Ignition trade, and Ignition's per-trade result cut in half")
for r in (0.01, 0.02):
    eq, dd, pm, nm, wm, con, tk = sim(["IGN", "RNG", "NEWS", "MV", "ETF"], r_ign=r); log(f"  Ignition risk {100*r:.0f}%: end £{eq:,.0f} ({100*(eq/500-1):+.0f}%) maxDD {100*dd:.0f}% months up {pm}/{nm}")
keep = list(T); mi = np.mean([pl["pts"] for e, a, b, pl in keep if e == "IGN"]); mr = np.mean([pl["ret"] for e, a, b, pl in keep if e == "RNG"])
T[:] = [(e, a, b, (dict(pl, pts=pl["pts"] - mi / 2) if e == "IGN" else (dict(pl, ret=pl["ret"] - mr / 2) if e == "RNG" else pl))) for e, a, b, pl in keep]
for lab, engs in (("B halved", ["IGN", "RNG"]), ("FULL halved", ["IGN", "RNG", "NEWS", "MV", "ETF"])):
    eq, dd, pm, nm, wm, con, tk = sim(engs); log(f"  {lab:12} (Ignition and Range at HALF their backtest edge): end £{eq:,.0f} ({100*(eq/500-1):+.0f}%) maxDD {100*dd:.0f}% months up {pm}/{nm}")
T[:] = keep
log("done")
