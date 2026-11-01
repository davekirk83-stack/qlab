"""
THE PAPER BOOK v13 — "Combined IG book", registered 1 Nov 2026 (doc 169; DK 1 Nov "Yes" to building a combined book of maximum
effectiveness). The £500 IG account as one pool, run on paper.

SIMULATED LEDGER ONLY. Standing constraint CAP-021 (demo amendment 20 Oct): no live account, live key, or real money. Public data only.

THE REGISTERED RULES (any change voids the run and restarts the clock)
  engines   IGN  Ignition v1.1 on US Tech 100 (paperbook7 engine, US hours, no 12-15 NY entries, stop max(45, 1.5 ATR)) — risk 2%
            RNG  Range v3 on US Tech 100, NY hours (paperbook8 'NQ' engine, mid-EMA exit, ladder) — 15% of equity as margin per episode
            NEWS News-day fade on US Tech 100 after CPI (8:30 NY) and FOMC (2pm NY) releases, 15-minute wait (doc 156 rules) — risk 1%
  pool      start £500 on 1 Nov 2026; each trade sizes off current realised equity; TOTAL OPEN EXPOSURE <= 5 x EQUITY (DK 1 Nov 16:02,
            amended before any trade; a trade is scaled to fit); total margin <= 60% of equity (a trade is scaled to
            fit, skipped if under a quarter of its size); one engine <= 40% of equity in margin; risk halved while equity is >10% below
            its high; a day whose realised loss reaches -4% takes no further entries; Fed blackout (30 min before to 60 min after a
            statement) on IGN and RNG entries — NEWS is the registered exception.
  costs     IG US Tech 100: 1 pt per side in US hours (2 outside), overnight funding 0.018%/night on range holds; margin 5%.
  data      data_nq_cache/nq_5m.csv (kept current by STEP 3e); event dates in runs/event_blackouts.json (fomc, cpi).
  replay    the whole book is REPLAYED from 1 Nov 2026 every run (book 7's anti-leak pattern) — reproducible by construction.
  compare   reported beside "Ignition alone" at the same 2% risk (does pooling add?); verdict after 3 months: PASS if the pool beats
            Ignition alone with a max drawdown no worse than -15%, and is positive in at least 2 of 3 months.
Backtest (doc 169, Nov 2025 - Oct 2026, £500): with the 5x exposure cap £805 (+61%, maxDD -12%, worst month -£41); uncapped it was
£938 (+88%) but peaked at 11x exposure. IGN alone £718 (+44%, maxDD -2%);
with Ignition and Range at half their backtest edge, +18%. Ignition v1.1 was fitted on that year: plan on a third to a half.
Emits runs/paper13_<date>.sql (pb13_equity, pb13_trades, pb13_v2).
VARIANT v2 (doc 175, DK 1 Nov "Excellent"): the same pool plus the Range ladder on the US 500 (New York hours) and the FTSE 100 (London
hours), 15% of equity as margin per episode, from 1 Nov 2026; data topped up from Dukascopy into data_ig_cache/. Backtest (12 months,
5x cap): £500 -> £1,381, maxDD -10%, 11/12 months up, worst month -£12, ~63 trades a month. Reported beside book 13 (pb13_v2).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paperbook7 as P7, paperbook6 as P6, paperbook8 as P8
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"
START = pd.Timestamp(os.environ.get("PB13_START", "2026-11-01"), tz="UTC"); EQ0 = 500.0; MARGIN = 0.05; FUND_NIGHT = 0.00018
MAX_LEV = 5.0   # DK 1 Nov 16:02: "I'm happy with 2x but if you are confident in using 5x sensibly then that's fine (but no more)"
EV = json.load(open(f"{RUNS}/event_blackouts.json"))
FOMC_T = [pd.Timestamp(d + " 14:00", tz="America/New_York").tz_convert("UTC") for d in EV["fomc"]]
CPI_T = [pd.Timestamp(d + " 08:30", tz="America/New_York").tz_convert("UTC") for d in EV.get("cpi", [])]
def blackout(t): return any(T - pd.Timedelta(minutes=30) <= t <= T + pd.Timedelta(minutes=60) for T in FOMC_T)

def fade(d, T, W=15, cost=1.0):
    """doc 156 rule on 5-minute bars; returns (R, t_entry, t_exit) or None."""
    pre = d[d.index < T]; post = d[d.index >= T]
    if len(pre) < 3 or len(post) < 49: return None                 # need the full 4 hours after the release
    P = float(pre.close.iloc[-1]); end = T + pd.Timedelta(hours=4)
    w = post[post.index < T + pd.Timedelta(minutes=W)]
    if len(w) < 2: return None
    s = 1 if (w.high.max() - P) >= (P - w.low.min()) else -1; X = w.high.max() if s == 1 else w.low.min()
    a = post[(post.index >= T + pd.Timedelta(minutes=W)) & (post.index < end)]; H, L, C, ix = a.high.values, a.low.values, a.close.values, a.index
    k0 = None
    for k in range(1, len(C)):
        X = max(X, H[k]) if s == 1 else min(X, L[k])
        if (C[k] - P) * s <= 0: return None
        if (s == 1 and C[k] < L[k - 1]) or (s == -1 and C[k] > H[k - 1]): k0 = k; break
    if k0 is None: return None
    e = C[k0]; stop = X * (1 + 0.0002 * s); side = -s; risk = abs(stop - e)
    if risk <= 0: return None
    px, kx = C[-1], len(C) - 1
    for k in range(k0 + 1, len(C)):
        if (side == -1 and H[k] >= stop) or (side == 1 and L[k] <= stop): px, kx = stop, k; break
        if (side == -1 and L[k] <= P) or (side == 1 and H[k] >= P): px, kx = P, k; break
    return ((px - e) * side - 2 * cost) / risk, ix[k0], ix[kx], e, risk

def trades():
    T = []
    bars = pd.read_csv(f"{ROOT}/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
    last_bar = bars.index[-1]
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
        if idx[i + 1] < START or blackout(idx[i + 1]): continue
        T.append(("IGN", idx[i + 1], idx[min(i + 1 + r[1], len(C) - 1)], dict(pts=float(r[0]), stop=float(sp), px=float(C[i]), side=s)))
    path, sp_, src, hours = P8.INSTR["NQ"]
    b = P8.load("NQ"); P8.set_costs("NQ", b); P6.indicators = P8.hours_gate(hours); P6._MED = {}
    closed, _ = P6.step("NQ", b, {}, str(b.index[250]), [10**6]); P6.indicators = P8._orig_ind
    for c in closed:
        o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
        if o < START or blackout(o): continue
        T.append(("RNG", o, cl, dict(ret=float(c[4]) - max(0, (cl.normalize() - o.normalize()).days) * FUND_NIGHT, side=c[1])))
    # doc 175 variant (v2): the same ladder on the US 500 (New York hours) and the FTSE 100 (London hours)
    for eng, f, sp, tz, h0, h1 in (("RUS", "USA500IDXUSD", 0.4, "America/New_York", 9.5, 16), ("RFT", "GBRIDXGBP", 1.0, "Europe/London", 8, 16.5)):
        path = f"{ROOT}/data_ig_cache/{f}_5m.csv"
        if not os.path.exists(path): print(f"  {eng}: no data file", flush=True); continue
        d5 = pd.read_csv(path, index_col=0); d5.index = pd.to_datetime(d5.index, utc=True); d5 = d5[~d5.index.duplicated()].sort_index()
        b2 = pd.DataFrame({"open": d5.open.resample("15min").first(), "high": d5.high.resample("15min").max(), "low": d5.low.resample("15min").min(), "close": d5.close.resample("15min").last()}).dropna()
        px = float(b2.close.median()); P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
        def ind(dd, sym=None, tz=tz, h0=h0, h1=h1):
            ema, lob, hib, a, allow = P8._orig_ind(dd, sym); tt = dd.index.tz_convert(tz); hh = tt.hour + tt.minute / 60
            return ema, lob, hib, a, allow & ((hh >= h0) & (hh < h1))
        P6.indicators = ind; P6._MED = {}
        cl2, _ = P6.step(eng, b2, {}, str(b2.index[250]), [10**6]); P6.indicators = P8._orig_ind
        for c in cl2:
            o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
            if o < START or blackout(o): continue
            T.append((eng, o, cl, dict(ret=float(c[4]) - max(0, (cl.normalize() - o.normalize()).days) * FUND_NIGHT, side=c[1])))
    for TT in FOMC_T + CPI_T:
        if TT < START or TT + pd.Timedelta(hours=4) > last_bar: continue
        w = bars[(bars.index >= TT - pd.Timedelta(hours=2)) & (bars.index < TT + pd.Timedelta(hours=5))]
        r = fade(w, TT)
        if r: T.append(("NEWS", r[1], r[2], dict(R=float(r[0]), e=float(r[3]), risk=float(r[4]))))
    return sorted(T, key=lambda t: t[1]), last_bar

def pool(T, engs, r_ign=0.02, rng_frac=0.15, r_news=0.01):
    eq = hi = EQ0; open_ = []; daily = {}; rows = []; mdd = 0.0
    def settle(upto):
        nonlocal eq, hi, mdd
        open_.sort(key=lambda p: p["tc"])
        while open_ and open_[0]["tc"] <= upto:
            p = open_.pop(0); eq += p["pnl"]; dk = p["tc"].date(); daily[dk] = daily.get(dk, 0) + p["pnl"]; hi = max(hi, eq); mdd = min(mdd, eq / hi - 1)
            rows.append(p)
    for eng, to, tc, pl in T:
        if eng not in engs: continue
        settle(to); dk = to.date(); sod = eq - daily.get(dk, 0)
        if daily.get(dk, 0) <= -0.04 * sod: continue
        k = 0.5 if eq < 0.9 * hi else 1.0
        used = sum(p["m"] for p in open_); used_e = sum(p["m"] for p in open_ if p["eng"] == eng)
        if eng == "IGN": stake = eq * r_ign * k / pl["stop"]; m = stake * pl["px"] * MARGIN; pnl = stake * pl["pts"]
        elif eng in ("RNG", "RUS", "RFT"): m = eq * rng_frac * k; pnl = m / MARGIN * pl["ret"]
        else: stake = eq * r_news * k / pl["risk"]; m = stake * pl["e"] * MARGIN; pnl = eq * r_news * k * pl["R"]
        room = min(0.60 * eq - used, 0.40 * eq - used_e)
        if room <= 0: continue
        f = min(1.0, room / m) if m > 0 else 1.0
        nroom = MAX_LEV * eq - used / MARGIN                     # total open exposure (notional) <= 5 x equity
        f = min(f, nroom / (m / MARGIN)) if m > 0 else f
        if f < 0.25: continue
        open_.append(dict(eng=eng, to=to, tc=tc, m=m * f, pnl=pnl * f, x=pl))
    settle(pd.Timestamp.utcnow())
    return eq, mdd, rows, open_

if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    import subprocess
    y = (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    for ins in ("USA500IDXUSD", "GBRIDXGBP"):                   # top up the v2 markets from Dukascopy (incremental)
        try: subprocess.run([sys.executable, f"{os.path.dirname(os.path.abspath(__file__))}/pull_duka.py", ins, "1000", "2026-10-30", y], timeout=1500, check=False)
        except Exception as e: print(f"  pull {ins}: {e}", flush=True)
    T, last_bar = trades()
    now = last_bar
    done = [t for t in T if t[2] <= now]
    eq, mdd, rows, op = pool(done, {"IGN", "RNG", "NEWS"}); eqI, mddI, _, _ = pool(done, {"IGN"})
    eq2, mdd2, rows2, _ = pool(done, {"IGN", "RNG", "NEWS", "RUS", "RFT"})   # doc 175 variant v2
    print(f"paper book v13 (combined IG book) — {today} — bars to {last_bar} — equity £{eq:,.2f} (maxDD {100*mdd:.1f}%) "
          f"vs Ignition alone £{eqI:,.2f}", flush=True)
    for e in ("IGN", "RNG", "NEWS"):
        rr = [p for p in rows if p["eng"] == e]; print(f"  {e}: {len(rr)} closed, £{sum(p['pnl'] for p in rr):+.2f}", flush=True)
    print(f"  v2 (+ US 500 and FTSE ladders, doc 175): £{eq2:,.2f} (maxDD {100*mdd2:.1f}%), {len(rows2)} closed — "
          + ", ".join(f"{e} £{sum(p['pnl'] for p in rows2 if p['eng'] == e):+.2f}" for e in ("IGN", "RNG", "NEWS", "RUS", "RFT")), flush=True)
    lines = ["CREATE TABLE IF NOT EXISTS pb13_v2 (d TEXT PRIMARY KEY, equity REAL, max_dd REAL, closed_total INTEGER);",
             f"INSERT OR REPLACE INTO pb13_v2 VALUES ('{today}', {eq2:.4f}, {mdd2:.4f}, {len(rows2)});",
             "CREATE TABLE IF NOT EXISTS pb13_equity (d TEXT PRIMARY KEY, equity REAL, ignition_alone REAL, max_dd REAL, closed_total INTEGER);",
             "CREATE TABLE IF NOT EXISTS pb13_trades (d TEXT, eng TEXT, opened TEXT, closed TEXT, pnl REAL, margin REAL);",
             f"INSERT OR REPLACE INTO pb13_equity VALUES ('{today}', {eq:.4f}, {eqI:.4f}, {mdd:.4f}, {len(rows)});",
             f"DELETE FROM pb13_trades;"]
    for p in rows:
        lines.append(f"INSERT INTO pb13_trades VALUES ('{today}', '{p['eng']}', '{p['to']}', '{p['tc']}', {p['pnl']:.4f}, {p['m']:.4f});")
    out = f"{RUNS}/paper13_{today}.sql"; open(out, "w").write("\n".join(lines)); print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
