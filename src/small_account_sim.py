"""Optimising a £500-1,000 IG spread-bet account (DK 26 Oct: "find ways to optimise that ... by keeping trade times as efficient as possible").
Real IG parameters (demo, 26 Oct): US Tech 100 min £0.01/pt, Wall Street / Germany 40 / US 500 min £0.04/pt, index margin 5%.
Engines, last year of data, IG costs:
  Ignition v1.1 on US Tech 100 (US hours, no lunch), 5-min, stop max(45, 1.5 ATR) — intraday, flat by 21:00, no overnight funding.
  Range v3-IDX episodes (US Tech 100 NY hours, Wall Street, Germany 40) — 15-min, up to 12 h, overnight funding ~0.018%/night of notional.
Measures: P&L per trade, hours in the market, return on margin per hour held (capital efficiency), and a fixed-fractional account sim
(rule 186: risk r% of current equity per trade, halve after -10% from the high), starting £500 and £1,000, margin capped at 60% of equity."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import paperbook7 as P7, paperbook6 as P6
MARGIN = 0.05; FUND_NIGHT = 0.00018
# ---------------- Ignition trades with timestamps
bars = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d = P7.features(bars); m = d.index.hour*60 + d.index.minute; d["cost"] = np.where((m >= P7.US_OPEN) & (m < P7.US_CLOSE), 0.5, 1.0)
O, H, L, C, cost, atr, sig, day, idx = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values, d.atr.values, d.sig.values, d.day.values, d.index
ign = []; last = -10**9; cur = None; ntr = 0; dpl = 0
for i in range(300, len(C)-1):
    if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0
    s = int(sig[i]); t = idx[i]; mm = t.hour*60 + t.minute
    if s == 0 or np.isnan(atr[i]) or i < last + P7.COOL or ntr >= P7.MAXT or dpl <= -P7.LOSSCAP: continue
    if not (P7.US_OPEN <= mm < P7.US_CLOSE) or t.hour in P7.V11_SKIP_HOURS: continue
    sp = max(P7.STOP, P7.V11_STOP_ATR*atr[i]); r = P7.manage(O, H, L, C, cost, atr, i, s, len(C), sp)
    if r is None: break
    ign.append(dict(t=idx[i+1], pts=r[0], stop=sp, px=C[i], hours=r[1]*5/60, eng="Ignition NQ")); last = i + r[1]; ntr += 1; dpl += r[0]
ign = pd.DataFrame(ign)
# ---------------- Range episodes on the three indices (paperbook8 machinery)
import paperbook8 as P8
rng_rows = []
for name, (path, sp_, src, hours) in P8.INSTR.items():
    b = P8.load(name); P8.set_costs(name, b); P6.indicators = P8.hours_gate(hours); P6._MED = {}
    closed, _ = P6.step(name, b, {}, str(b.index[250]), [10**6])
    for c in closed:
        o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); hrs = (cl - o)/pd.Timedelta(hours=1)
        nights = max(0, (cl.normalize() - o.normalize()).days) + (1 if (o.hour < 22 <= cl.hour and cl.date() == o.date()) else 0)
        rng_rows.append(dict(t=cl, ret=c[4] - nights*FUND_NIGHT, hours=max(hrs, 0.25), eng=f"Range {name}", px=float(b.close.median())))
P6.indicators = P8._orig_ind
rng = pd.DataFrame(rng_rows)
print(f"Ignition: {len(ign)} trades {ign.t.min().date()} -> {ign.t.max().date()};  Range: {len(rng)} episodes {rng.t.min().date()} -> {rng.t.max().date()}")
# ---------------- capital efficiency: return on margin per hour held
print("\n== capital efficiency (return on margin employed, per trade and per hour in the market)")
ign["rom"] = ign.pts/ign.px/MARGIN            # move / margin fraction = return on margin
print(f"  Ignition NQ        n {len(ign):4d}  avg hold {ign.hours.mean():.1f} h  return on margin {ign.rom.mean()*100:+.2f}%/trade  -> {ign.rom.sum()/ign.hours.sum()*100:+.3f}% per margin-hour  (trades/yr ~{len(ign)/((ign.t.max()-ign.t.min()).days/365):.0f})")
for e, g in rng.groupby("eng"):
    rom = g.ret/MARGIN*1.0   # episode return is on intended position; on margin it is /5%
    yrs = (g.t.max()-g.t.min()).days/365
    print(f"  {e:18s} n {len(g):4d}  avg hold {g.hours.mean():.1f} h  return on margin {rom.mean()*100:+.2f}%/episode -> {rom.sum()/g.hours.sum()*100:+.3f}% per margin-hour  (episodes/yr ~{len(g)/max(yrs,0.1):.0f})")
# ---------------- account simulation
def sim(start, risk, use_range, range_frac):
    ev = [("I", r.t, r.pts, r.stop, r.px) for r in ign.itertuples()]
    if use_range: ev += [("R", r.t, r.ret, None, r.px) for r in rng[rng.eng == "Range NQ"].itertuples()]
    ev.sort(key=lambda x: x[1]); eq = start; hi = start; low = start; mdd = 0; skipped = 0
    for k, t, x, stop, px in ev:
        rr = risk*(0.5 if eq < 0.9*hi else 1.0)
        if k == "I":
            stake = max(0.01, round(eq*rr/stop, 2)); marg = stake*px*MARGIN
            if marg > 0.6*eq: stake = round(0.6*eq/(px*MARGIN), 2); skipped += stake < 0.01
            if stake < 0.01: continue
            eq += stake*x
        else:
            notional = min(eq*range_frac/MARGIN, 0.6*eq/MARGIN)        # range_frac of equity as margin
            eq += notional*x
        hi = max(hi, eq); mdd = min(mdd, eq/hi - 1)
    return eq, mdd
print("\n== one-year account simulation (rule 186 sizing, margin capped at 60% of equity)")
for start in (500, 1000):
    for risk in (0.01, 0.02):
        for use_r, rf in ((False, 0), (True, 0.10), (True, 0.20)):
            e, dd = sim(start, risk, use_r, rf)
            print(f"  start £{start:<5} risk {risk*100:.0f}%/Ignition trade{'' if not use_r else f' + Range NQ at {rf*100:.0f}% of equity as margin':<40}  end £{e:,.0f} ({(e/start-1)*100:+.0f}%)  max drawdown {dd*100:.0f}%")
