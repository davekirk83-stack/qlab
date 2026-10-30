"""
THE PAPER BOOK v11 — "Stock pivots": two sub-books on US stocks, registered 28 Oct 2026 (doc 151, DK: "Yes do those").
  MV  Minervini VCP pivot with first-hour confirmation   (doc 151: n1537, +0.09R/trade, beat random 100% over 2 years)
  EP  Qullamaggie / Bonde episodic pivot                 (doc 151: n84, +0.15R/trade, beat random 78%)

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading only. No live order, brokerage or exchange account,
credential, authentication, or committed capital of any size, on any signal, under any circumstance. Public market data only.

THE REGISTERED RULES (identical to doc 151; any change voids the run and restarts the clock)
  universe   runs/stock_universe.json (2,717 US stocks liquid and high-range at some point Nov 2024 - Oct 2026), pinned
  data       Yahoo daily (adjusted, 2 years) for setups; Yahoo hourly (regular session) for the entry day, rescaled to the daily basis
  MV setup   SPY above SMA50 > SMA200 with SMA50 rising (prior close); price >= $10, 20d median $vol >= $5m; Minervini trend template
             (close > SMA150 & SMA200, SMA150 > SMA200, SMA200 up over 21 days, SMA50 > SMA150, close > SMA50, >= 1.3x 52w low,
             >= 0.75x 52w high, 12-month return in the top 30% of the universe); contraction ranges 0-10 < 0.75 x 10-25 < 0.75 x 25-50
             days, last <= 12%; 10-day volume below 50-day. All at the PRIOR close.
  MV entry   after the first hour, buy when price breaks max(first-hour high, prior 10-day high); stop = max(prior 10-day low, entry x 0.925)
  MV manage  half off at +20%; stop to breakeven after a close >= +2R; the rest exits on a close below SMA50
  EP setup   price >= $5, 20d median $vol >= $5m, ADR(20) >= 4%; opens >= 10% above the prior close; first-hour volume >= 50% of the 50-day
             average daily volume; prior 60-day return <= +20%. No market filter.
  EP entry   after the first hour, break of the first-hour high; stop = low of the day so far; skip if the risk exceeds 1 ADR
  EP manage  half off at the close of the 3rd day after entry and stop to breakeven; the rest exits on a close below SMA10
  size       each trade risks 0.5% of that sub-book's equity; at most 10 open per sub-book; candidates taken in order (MV: 12-month
             strength; EP: gap size). Costs 0.20% per side + 6.5%/yr financing (IG share spread bets). $2,000 per sub-book.
  SHADOW     for every real entry, a deterministic pseudo-random eligible stock on the same day, entered on the break of ITS first-hour
             high with the same stop rule and management (the doc 151 control). The verdict is REAL minus SHADOW.
  KILL       flatten=1 or 2 closes everything at the next daily close and blocks entries (long-only books)
  PASS/FAIL  60 closed trades per sub-book or 6 months; PASS if mean R > 0 net AND beats the shadow; early kill if a 20-trade block
             averages below -0.5R.

Emits runs/paper11_<date>.sql (tables pb11_equity, pb11_trades).
LABELLED VARIANT (doc 165, DK 30 Oct "Sure"): each real entry is tagged with the daily Ichimoku cloud state (prior close above the cloud);
cloud_equity compounds only the tagged-above trades, from 30 Oct 2026 (tables pb11_cloud, pb11_trade_cloud). The registered rules are
unchanged. Approximation: slots freed by skipped trades are not re-used. Scored on MV; EP reported but too sparse to judge.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, hashlib, urllib.request, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cloud_gate import cloud_above
from concurrent.futures import ThreadPoolExecutor
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"; STATE = f"{RUNS}/paper11_state.json"
COST, FIN, RISK, MAXOPEN, START = 0.002, 0.065, 0.005, 10, 2000.0
UA = {"User-Agent": "Mozilla/5.0"}

def yget(sym, interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={interval}&includePrePost=false" + ("&events=div,split" if interval == "1d" else "")
    for k in range(3):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            t = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York")
            d = pd.DataFrame({"t": t, "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"]}).dropna()
            if interval == "1d":
                adj = r["indicators"]["adjclose"][0]["adjclose"]; f = pd.Series(adj, index=t).reindex(d.t).values / d.close.values
                for c in ("open", "high", "low", "close"): d[c] = d[c] * f
                d["t"] = d.t.dt.tz_localize(None).dt.normalize(); return d.set_index("t")
            d = d[(d.t.dt.hour >= 9) & (d.t.dt.hour < 16)]; d["day"] = d.t.dt.tz_localize(None).dt.normalize(); return d
        except Exception:
            time.sleep(1.5 * (k + 1))
    return None

def draw(key): return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 10**9 / 10**9

def halted():
    f = f"{RUNS}/HALT.json"
    if not os.path.exists(f): return 0
    try: h = json.load(open(f))
    except Exception: return 1
    if not h.get("active"): return 0
    ra = h.get("resume_after")
    if ra and pd.Timestamp(ra) < pd.Timestamp.utcnow().tz_localize(None).normalize(): return 0
    return int(h.get("flatten", 1)) or 0

def indicators(D, spy):
    s50, s200 = spy.close.rolling(50).mean(), spy.close.rolling(200).mean()
    sok = ((spy.close > s50) & (s50 > s200) & (s50 > s50.shift(10))).shift(1)
    rs = pd.DataFrame({s: d.close / d.close.shift(252) - 1 for s, d in D.items()}).rank(axis=1, pct=True)
    X = {}
    for s, d in D.items():
        o, c, h, l, v = d.open, d.close, d.high, d.low, d.volume
        m10, m50, m150, m200 = (c.rolling(n).mean() for n in (10, 50, 150, 200))
        adr = (h / l - 1).rolling(20).mean(); dv = (c * v).rolling(20).median()
        tt = (c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(21)) & (m50 > m150) & (c > m50) & \
             (c >= 1.3 * l.rolling(252).min()) & (c >= 0.75 * h.rolling(252).max()) & (rs[s].reindex(d.index) >= 0.70)
        rg = lambda a, b: (h.shift(a).rolling(b - a).max() - l.shift(a).rolling(b - a).min()) / h.shift(a).rolling(b - a).max()
        r1, r2, r3 = rg(0, 10), rg(10, 25), rg(25, 50)
        vcp = tt & (r1 < 0.75 * r2) & (r2 < 0.75 * r3) & (r1 <= 0.12) & (v.rolling(10).mean() < v.rolling(50).mean()) & (c >= 10) & (dv >= 5e6)
        el = (c >= 5) & (dv >= 5e6) & (adr >= 0.04)
        P = lambda x: x.shift(1)
        X[s] = pd.DataFrame({"O": o, "H": h, "L": l, "C": c, "m10": m10, "m50": m50, "adr": P(adr), "piv": P(h.rolling(10).max()),
                             "plo": P(l.rolling(10).min()), "v50": P(v.rolling(50).mean()), "rs": P(rs[s].reindex(d.index)),
                             "mv": P(vcp).fillna(False), "el": P(el).fillna(False), "gap": o / c.shift(1) - 1,
                             "r60": c.shift(1) / c.shift(61) - 1, "sok": sok.reindex(d.index).fillna(False),
                             "cloud": cloud_above(d)})
    return X

def entry_day(hb, x, day, pivot):
    """First-hour-confirmed entry on `day`. Returns (entry, stop_so_far, later_lows, first_hour_volume) on the daily basis, or None."""
    g = hb[hb.day == day] if hb is not None else None
    if g is None or len(g) < 3: return None
    k = x.at[day, "C"] / g.close.values[-1]; Hh, Lh, Oh = g.high.values * k, g.low.values * k, g.open.values * k
    trig = Hh[0] if pivot is None else max(Hh[0], pivot)
    for b in range(1, len(Hh)):
        if Hh[b] > trig:
            e = max(trig, Oh[b]); return e, min(Lh[:b + 1].min(), e * 0.999), Lh[b + 1:], float(g.volume.values[0])
    return None

def open_pos(book, sym, day, x, e, stop, later, kind):
    if book == "MV": stop = max(x.at[day, "plo"], e * 0.925)
    risk = (e - stop) / e
    if risk <= 0: return None
    p = {"sym": sym, "opened": str(day.date()), "entry": float(e), "stop": float(stop), "risk": float(risk), "w": 1.0,
         "legs": [], "be": False, "n": 0, "kind": kind}
    if len(later) and later.min() <= stop: p["legs"].append([1.0, float(stop)]); p["w"] = 0.0; p["closed"] = str(day.date()); p["how"] = "stop"
    return p

def manage(book, p, x, day, flatten):
    """Advance an open position by one daily bar."""
    if day not in x.index or p["w"] <= 0: return
    O, H, L, C = (float(x.at[day, k]) for k in ("O", "H", "L", "C")); p["n"] += 1; e = p["entry"]
    def leg(w, px, how):
        p["legs"].append([w, float(px)]); p["w"] -= w
        if p["w"] <= 1e-9: p["w"] = 0.0; p["closed"] = str(day.date()); p["how"] = how
    if flatten: leg(p["w"], C, "halt"); return
    if L <= p["stop"]: leg(p["w"], min(p["stop"], O), "breakeven" if p["be"] else "stop"); return
    if book == "MV":
        if p["w"] == 1.0 and H >= e * 1.2: leg(0.5, max(e * 1.2, O), "partial")
        if C >= e * (1 + 2 * p["risk"]): p["stop"] = max(p["stop"], e); p["be"] = True
        if C < float(x.at[day, "m50"]): leg(p["w"], C, "trail SMA50")
    else:
        if p["n"] == 3 and p["w"] == 1.0: leg(0.5, C, "partial"); p["stop"] = max(p["stop"], e); p["be"] = True
        if p["w"] > 0 and C < float(x.at[day, "m10"]): leg(p["w"], C, "trail SMA10")

def result(p, x):
    eC = p["entry"] * (1 + COST)
    days = (pd.Timestamp(p["closed"]) - pd.Timestamp(p["opened"])).days
    r = sum(w * (px * (1 - COST) / eC - 1) for w, px in p["legs"]) - FIN * days / 365
    return r, r / max(p["risk"], 0.002)

if __name__ == "__main__":
    today = pd.Timestamp.utcnow().tz_convert("America/New_York").tz_localize(None).normalize()
    U = json.load(open(f"{RUNS}/stock_universe.json"))
    st = json.load(open(STATE)) if os.path.exists(STATE) else None
    if st is None: raise SystemExit("paper11_state.json missing — the book must not restart silently")
    fl = halted()
    print(f"paper book v11 (stock pivots) — {today.date()} — MV ${st['MV']['equity']:,.2f} / shadow ${st['MV']['shadow_equity']:,.2f}; "
          f"EP ${st['EP']['equity']:,.2f} / shadow ${st['EP']['shadow_equity']:,.2f}" + (f"  *** HALT flatten={fl} ***" if fl else ""), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(12) as ex: D = dict(zip(U, ex.map(lambda s: yget(s, "1d", "2y"), U)))
    D = {s: d[~d.index.duplicated()] for s, d in D.items() if d is not None and len(d) > 260}
    spy = yget("SPY", "1d", "2y"); qqq_h = yget("QQQ", "60m", "1mo")
    print(f"  daily bars: {len(D)} stocks in {time.time()-t0:.0f}s", flush=True)
    X = indicators(D, spy)
    days = sorted(d for d in set(qqq_h.day) if pd.Timestamp(st["since"]) < d < today)
    print(f"  sessions to process: {[str(d.date()) for d in days]}", flush=True)
    need = set(U) if days else set()
    t0 = time.time()
    with ThreadPoolExecutor(12) as ex: HB = dict(zip(need, ex.map(lambda s: yget(s, "60m", "1mo"), list(need))))
    print(f"  hourly bars: {sum(v is not None for v in HB.values())} stocks in {time.time()-t0:.0f}s", flush=True)
    closed_rows = []
    for day in days:
        for book in ("MV", "EP"):
            B = st[book]
            for side in ("pos", "shadow"):
                for p in B[side]:
                    x = X.get(p["sym"])
                    if x is not None and p["opened"] != str(day.date()): manage(book, p, x, day, fl in (1, 2))
                done = [p for p in B[side] if p["w"] <= 0]; B[side] = [p for p in B[side] if p["w"] > 0]
                for p in done:
                    r, R = result(p, X[p["sym"]]); key = "equity" if side == "pos" else "shadow_equity"
                    B[key] += B[key] * (RISK / p["risk"]) * r
                    B["closed" if side == "pos" else "closed_shadow"] += 1
                    closed_rows.append((book, side == "shadow", p, r, R))
                    if side == "pos" and p.get("cloud") is True:
                        B.setdefault("cloud_equity", START); B["cloud_equity"] += B["cloud_equity"] * (RISK / p["risk"]) * r; B["closed_cloud"] = B.get("closed_cloud", 0) + 1
            if fl in (1, 2): continue
            cands = []
            for s, x in X.items():
                if day not in x.index: continue
                row = x.loc[day]
                if book == "MV" and row.mv and row.sok and row.H > row.piv: cands.append((-(row.rs if row.rs == row.rs else 0), s))
                if book == "EP" and row.el and row.gap >= 0.10 and row.r60 <= 0.20: cands.append((-row.gap, s))
            held = {p["sym"] for p in B["pos"]}; elig_pool = sorted(s for s, x in X.items() if day in x.index and bool(x.at[day, "el"]) and (book == "EP" or bool(x.at[day, "sok"])))
            for _, s in sorted(cands):
                if len(B["pos"]) >= MAXOPEN: break
                if s in held: continue
                x = X[s]; r = entry_day(HB.get(s), x, day, float(x.at[day, "piv"]) if book == "MV" else None)
                if r is None: continue
                e, stop, later, v1 = r
                if book == "EP" and (v1 < 0.5 * float(x.at[day, "v50"]) or (e - stop) / e > float(x.at[day, "adr"])): continue
                p = open_pos(book, s, day, x, e, stop, later, "real")
                if p is None: continue
                p["cloud"] = bool(x.at[day, "cloud"])
                if p["w"] > 0: B["pos"].append(p)
                else:
                    r_, R_ = result(p, x); B["equity"] += B["equity"] * (RISK / p["risk"]) * r_; B["closed"] += 1; closed_rows.append((book, False, p, r_, R_))
                    if p["cloud"]: B.setdefault("cloud_equity", START); B["cloud_equity"] += B["cloud_equity"] * (RISK / p["risk"]) * r_; B["closed_cloud"] = B.get("closed_cloud", 0) + 1
                held.add(s); print(f"  {book} OPEN {s} @ {e:.2f} stop {p['stop']:.2f} ({100*p['risk']:.1f}% risk)", flush=True)
                # shadow: a pseudo-random eligible stock the same day, same mechanics
                for k in range(25):
                    if not elig_pool: break
                    ss = elig_pool[int(draw(f"{book}|{day.date()}|{s}|{k}") * len(elig_pool))]
                    if ss == s: continue
                    rr = entry_day(HB.get(ss), X[ss], day, None)
                    if rr is None: continue
                    q = open_pos(book, ss, day, X[ss], rr[0], rr[1], rr[2], "shadow")
                    if q is None: continue
                    if q["w"] > 0: B["shadow"].append(q)
                    else: B["shadow_equity"] += B["shadow_equity"] * (RISK / q["risk"]) * result(q, X[ss])[0]; B["closed_shadow"] += 1; closed_rows.append((book, True, q, *result(q, X[ss])))
                    break
        st["since"] = str(day.date())
    json.dump(st, open(STATE, "w"), indent=1)
    d = str(today.date()); lines = ["CREATE TABLE IF NOT EXISTS pb11_equity (d TEXT, book TEXT, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER, PRIMARY KEY (d, book));",
         "CREATE TABLE IF NOT EXISTS pb11_trades (d TEXT, book TEXT, sym TEXT, opened TEXT, closed TEXT, ret REAL, r_mult REAL, how TEXT, shadow INTEGER);"]
    for book in ("MV", "EP"):
        B = st[book]
        lines.append(f"INSERT OR REPLACE INTO pb11_equity VALUES ('{d}', '{book}', {B['equity']:.4f}, {B['shadow_equity']:.4f}, {len(B['pos'])}, {B['closed']}, {B['closed_shadow']});")
        print(f"  {book}: equity ${B['equity']:,.2f} / shadow ${B['shadow_equity']:,.2f}; open {len(B['pos'])} ({', '.join(p['sym'] for p in B['pos'])}); closed {B['closed']}", flush=True)
    lines.append("CREATE TABLE IF NOT EXISTS pb11_cloud (d TEXT, book TEXT, cloud_equity REAL, closed_cloud INTEGER, PRIMARY KEY (d, book));")
    lines.append("CREATE TABLE IF NOT EXISTS pb11_trade_cloud (book TEXT, sym TEXT, opened TEXT, cloud INTEGER, PRIMARY KEY (book, sym, opened));")
    for book in ("MV", "EP"):
        B = st[book]; B.setdefault("cloud_equity", START); B.setdefault("closed_cloud", 0)
        lines.append(f"INSERT OR REPLACE INTO pb11_cloud VALUES ('{d}', '{book}', {B['cloud_equity']:.4f}, {B['closed_cloud']});")
        for p in B["pos"]:
            if "cloud" in p: lines.append(f"INSERT OR REPLACE INTO pb11_trade_cloud VALUES ('{book}', '{p['sym']}', '{p['opened']}', {1 if p['cloud'] else 0});")
        print(f"  {book} cloud variant (doc 165): equity ${B['cloud_equity']:,.2f}, {B['closed_cloud']} closed", flush=True)
    for book, sh, p, r, R in closed_rows:
        if not sh and "cloud" in p: lines.append(f"INSERT OR REPLACE INTO pb11_trade_cloud VALUES ('{book}', '{p['sym']}', '{p['opened']}', {1 if p['cloud'] else 0});")
        lines.append(f"INSERT INTO pb11_trades VALUES ('{d}', '{book}', '{p['sym']}', '{p['opened']}', '{p.get('closed','')}', {r:.6f}, {R:.4f}, '{p.get('how','')}', {1 if sh else 0});")
    out = f"{RUNS}/paper11_{d}.sql"; open(out, "w").write("\n".join(lines)); print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
