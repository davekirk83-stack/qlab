"""Doc 175 part 2 — does book 13 get better with the new IG engines that passed the screen? Same 12 months, £500, same pool rules
(margin <= 60%, one engine <= 40%, total exposure <= 5x equity, -4% day stop, risk halved below -10%), engines added one at a time:
  RUS  Range ladder on the US 500, NY cash hours        15% of equity as margin per episode
  RFT  Range ladder on the FTSE 100, London cash hours  15%
  RDX  Range ladder on Germany 40, London cash hours    15%
  SIDE New York 'side' continuation on the US Tech 100  1% risk per trade
Book 13's engines (IGN, RNG on the Nasdaq, NEWS) come from combined_ig_book_test.py unchanged."""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
src = open("/home/claude/qlab-git/src/combined_ig_book_test.py").read().split("def sim(")[0].replace('OUT = open("runs/combined_ig_book_test.txt", "w")', 'OUT = open("/dev/null", "w")')
src = src.replace('for eng, f in (("MV", "runs/combo/mv.csv"), ("ETF", "runs/combo/etf.csv")):', 'for eng, f in ():')
exec(src)
OUT = open("runs/combined_ig_book2_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
import paperbook6 as P6, paperbook8 as P8
W0, W1 = pd.Timestamp("2025-11-01", tz="UTC"), pd.Timestamp("2026-10-31", tz="UTC")
def load5(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[~d.index.duplicated()].sort_index()
def to15(d): return pd.DataFrame({"open": d.open.resample("15min").first(), "high": d.high.resample("15min").max(), "low": d.low.resample("15min").min(), "close": d.close.resample("15min").last()}).dropna()
def gate(tz, h0, h1):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = P8._orig_ind(d, sym); t = d.index.tz_convert(tz); h = t.hour + t.minute / 60
        return ema, lob, hib, a, allow & ((h >= h0) & (h < h1))
    return ind
for eng, f, sp, tz, h0, h1 in (("RUS", "data_ign/USA500IDXUSD_5m.csv", 0.4, "America/New_York", 9.5, 16), ("RFT", "data_ign/GBRIDXGBP_5m.csv", 1.0, "Europe/London", 8, 16.5),
                               ("RDX", "data_ign/DEUIDXEUR_5m.csv", 1.2, "Europe/London", 8, 16.5)):
    b = to15(load5(f)); px = float(b.close.median()); P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
    P6.indicators = gate(tz, h0, h1); P6._MED = {}
    closed, _ = P6.step(eng, b, {}, str(b.index[250]), [10**6]); P6.indicators = P8._orig_ind
    for c in closed:
        o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
        if blackout(o): continue
        T.append((eng, o, cl, dict(ret=c[4] - max(0, (cl.normalize() - o.normalize()).days) * FUND_NIGHT)))
# NY side continuation on the Nasdaq (doc 175 rule B)
d = load5("data_nq_cache/nq_5m.csv"); d = d[d.index >= "2025-10-25"].copy(); t = d.index.tz_convert("America/New_York")
d["nyd"] = t.normalize().tz_localize(None); d["m"] = t.hour * 60 + t.minute
tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs())); d["atr"] = tr.rolling(20).mean()
days = sorted(d.nyd.unique())
for k in range(1, len(days)):
    day, prev = days[k], days[k - 1]
    ov = d[((d.nyd == prev) & (d.m >= 18 * 60)) | ((d.nyd == day) & (d.m < 9 * 60 + 30))]; ses = d[(d.nyd == day) & (d.m >= 9 * 60 + 30) & (d.m < 16 * 60)]
    if len(ov) < 100 or len(ses) < 70: continue
    hi, lo = ov.high.max(), ov.low.min(); o = ses.open.iloc[0]; near = 1 if (hi - o) < (o - lo) else -1; lvl = hi if near == 1 else lo
    f30 = ses.iloc[:6]; stop_lvl = f30.low.min() if near == 1 else f30.high.max(); win = ses[ses.m < 11 * 60 + 30]
    hit = np.flatnonzero((win.high.values >= lvl) if near == 1 else (win.low.values <= lvl))
    if not len(hit) or hit[0] + 1 >= len(ses): continue
    j = hit[0] + 1; e = ses.open.iloc[j]; a = float(ses.atr.iloc[j]); stop = min(stop_lvl, e - 0.5 * a) if near == 1 else max(stop_lvl, e + 0.5 * a)
    risk = abs(e - stop); px_exit, qx = ses.close.iloc[-1], len(ses) - 1
    for q in range(j, len(ses)):
        if (near == 1 and ses.low.iloc[q] <= stop) or (near == -1 and ses.high.iloc[q] >= stop): px_exit, qx = stop, q; break
    if risk > 0 and not blackout(ses.index[j]): T.append(("SIDE", ses.index[j], ses.index[qx], dict(R=((px_exit - e) * near - 1.0) / risk, e=float(e), risk=float(risk))))
T = [x for x in T if W0 <= x[1] < W1]
log("trades in the window: " + ", ".join(f"{e} {sum(1 for x in T if x[0] == e)}" for e in ("IGN", "RNG", "NEWS", "RUS", "RFT", "RDX", "SIDE")))

def sim(engs, start=500.0, r_ign=0.02, rng_frac=0.15, r_news=0.01, r_side=0.01, LEV=5.0):
    ev = sorted([x for x in T if x[0] in engs], key=lambda x: x[1]); eq = hi = start; open_ = []; daily = {}; contrib = {e: 0.0 for e in engs}; taken = {e: 0 for e in engs}; mdd = 0.0
    def settle(upto):
        nonlocal eq, hi, mdd
        open_.sort(key=lambda p: p["tc"])
        while open_ and open_[0]["tc"] <= upto:
            p = open_.pop(0); eq += p["pnl"]; contrib[p["eng"]] += p["pnl"]; dk = p["tc"].date(); daily[dk] = daily.get(dk, 0) + p["pnl"]; hi = max(hi, eq); mdd = min(mdd, eq / hi - 1)
    for eng, to, tc, pl in ev:
        settle(to); dk = to.date(); sod = eq - daily.get(dk, 0)
        if daily.get(dk, 0) <= -0.04 * sod: continue
        k = 0.5 if eq < 0.9 * hi else 1.0; used = sum(p["m"] for p in open_); used_e = sum(p["m"] for p in open_ if p["eng"] == eng)
        if eng == "IGN": stake = eq * r_ign * k / pl["stop"]; m = stake * pl["px"] * MARGIN; pnl = stake * pl["pts"]
        elif eng in ("RNG", "RUS", "RFT", "RDX"): m = eq * rng_frac * k; pnl = m / MARGIN * pl["ret"]
        elif eng == "NEWS": m = eq * r_news * k * 40 * MARGIN; pnl = eq * r_news * k * pl["R"]
        else: stake = eq * r_side * k / pl["risk"]; m = stake * pl["e"] * MARGIN; pnl = eq * r_side * k * pl["R"]
        room = min(0.60 * eq - used, 0.40 * eq - used_e)
        if room <= 0: continue
        f = min(1.0, room / m); f = min(f, (LEV * eq - used / MARGIN) / (m / MARGIN))
        if f < 0.25: continue
        open_.append(dict(eng=eng, tc=tc, m=m * f, pnl=pnl * f)); taken[eng] += 1
    settle(pd.Timestamp("2100-01-01", tz="UTC"))
    s = pd.Series(daily).sort_index(); s.index = pd.to_datetime(s.index); mon = s.groupby(s.index.to_period("M")).sum()
    return eq, mdd, mon, contrib, taken
log("\nBOOK 13 + NEW ENGINES — 12 months Nov 2025 - Oct 2026, £500, 5x exposure cap (backtest, not a forecast)")
base = ["IGN", "RNG", "NEWS"]
for lab, engs in (("book 13 as registered", base), ("+ US 500 ladder", base + ["RUS"]), ("+ FTSE ladder", base + ["RFT"]), ("+ Germany 40 ladder", base + ["RDX"]),
                  ("+ NY side (Nasdaq)", base + ["SIDE"]), ("+ US 500 + FTSE", base + ["RUS", "RFT"]), ("+ US 500 + FTSE + side", base + ["RUS", "RFT", "SIDE"]),
                  ("+ all four", base + ["RUS", "RFT", "RDX", "SIDE"])):
    eq, dd, mon, con, tk = sim(engs)
    log(f"  {lab:28} end £{eq:,.0f} ({100*(eq/500-1):+.0f}%) maxDD {100*dd:.0f}% | months up {(mon>0).sum()}/{len(mon)} median £{mon.median():+.0f} worst £{mon.min():+.0f} | trades {sum(tk.values())/12:.0f}/month | "
        + " ".join(f"{e} £{v:+.0f}" for e, v in con.items()))
log("done")
