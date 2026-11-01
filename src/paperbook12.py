"""
THE PAPER BOOK v12 — "Daily trend-line retest", registered 1 Nov 2026 (doc 168; DK 31 Oct: "Yes sounds good").
Replaces the hourly diagonal retest tracker (retired, doc 126/168). Rules = arm P of src/retest_faithful_test.py (causal pivots).

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading only. No live order, brokerage or exchange account,
credential, authentication, or committed capital of any size, on any signal, under any circumstance. Public market data only.

THE REGISTERED RULES (any change voids the run and restarts the clock)
  universe   the 27 registered coins (runs/range_universe.json; Coinbase daily, UTC days, data_daily/ rebuilt by STEP 1) and the 59
             clean ETFs (Yahoo daily). Completed bars only.
  line       a falling line through two pivot highs >= 10 bars apart, each pivot usable only once CONFIRMED (5 bars passed AND its
             2-ATR right-hand drop has happened); >= 3 points (one touch within 0.4 ATR besides the anchors) before the break.
  break      a close more than 0.4 ATR above the line, within 400 bars of the second pivot.
  retest     within 20 bars a bar trades back to within 0.4 ATR of the line and closes above it (void if a close is 0.4 ATR under).
  entry      the first bar from the retest (within 5) that closes above the line, above its open and above the prior bar's high:
             buy that close (void if a close falls 0.4 ATR under the line first).
  stop       the lowest low since the break - 0.2 ATR, and at least 1 ATR below entry.
  target     the highest high of the 60 bars before the break; skip the trade if it is less than 1.5R away.
  exit       stop (checked first, worst case) or target, or the close of the 120th bar.
  size       each trade risks 1% of equity; at most 20 open; one position per symbol. Costs 0.10%/side crypto, 0.05%/side ETFs.
  SHADOW     for every real entry, a deterministic pseudo-random other symbol of the same kind on the same date, entered at that close
             with stop = 10-bar low - 0.2 ATR (>= 1 ATR) and target = 60-bar high (>= 1.5R, else the next draw), same exits.
             The verdict is REAL minus SHADOW, in R.
  KILL       flatten=1 or 2 closes everything at the next close and blocks entries (long-only book); flatten=0 blocks entries.
  PASS/FAIL  minimum 60 closed trades or 6 months; PASS if mean R > 0 net AND beats the shadow; early kill if a 20-trade block
             averages below -0.6R.
Backtest (doc 168, causal): crypto daily +0.27R / +0.59R (dev to 2024 / holdout 2025-26), edge over random +0.20 / +0.58R;
ETF daily +0.25R / +0.24R, edge +0.10 / +0.15R.

Emits runs/paper12_<date>.sql (tables pb12_equity, pb12_trades). State runs/paper12_state.json.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, hashlib, urllib.request, numpy as np, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"; STATE = f"{RUNS}/paper12_state.json"
DATA = os.environ.get("QLAB_DATA", "/home/claude/qlab")
RISK, MAXOPEN, START, CAP = 0.01, 20, 2000.0, 120
COST = {"coin": 0.001, "etf": 0.0005}
ETFS = sorted("""SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV ACWI XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK TLT IEF SHY LQD HYG AGG TIP BND EMB MUB GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER
URA VNQ IYR VXX""".split())

def atr(d, n=14):
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().values

def causal_highs(H, L, a, prominence=2.0, window=5):
    n = len(H); out = []
    for i in range(window, n - window):
        if H[i] != H[i - window:i + window + 1].max(): continue
        if H[i] - L[max(0, i - 60):i].min() <= prominence * a[i]: continue
        drop = np.flatnonzero(H[i] - np.minimum.accumulate(L[i:min(n, i + 60)]) > prominence * a[i])
        if not len(drop): continue
        out.append((i, max(i + window, i + int(drop[0]))))
    return out

def entry_today(d):
    """The practitioner retest entry, if the LAST bar of d is a confirmation bar. Returns (entry, stop, target) or None."""
    H, L, C, O = d.high.values, d.low.values, d.close.values, d.open.values; n = len(C)
    if n < 200: return None
    a = atr(d); highs = causal_highs(H, L, a)
    for ai in range(len(highs) - 1):
        for bi in range(ai + 1, min(ai + 6, len(highs))):
            (i1, _), (i2, k2) = highs[ai], highs[bi]
            if i2 - i1 < 10 or H[i2] >= H[i1]: continue
            slope = (H[i2] - H[i1]) / (i2 - i1); line = lambda j: H[i1] + slope * (j - i1)
            touches, brk = 0, None
            for j in range(k2, min(n, i2 + 400)):
                lv = line(j)
                if lv <= 0: break
                if C[j] > lv + 0.4 * a[j]: brk = j; break
                if abs(H[j] - lv) <= 0.4 * a[j]: touches += 1
            if brk is None or touches < 1: continue
            touch = None
            for j in range(brk + 1, min(brk + 21, n)):
                lv = line(j)
                if C[j] < lv - 0.4 * a[j]: break
                if L[j] <= lv + 0.4 * a[j] and C[j] > lv: touch = j; break
            if touch is None: continue
            conf = None
            for j in range(touch, min(touch + 6, n)):
                lv = line(j)
                if C[j] < lv - 0.4 * a[j]: break
                if C[j] > lv and C[j] > O[j] and C[j] > H[j - 1]: conf = j; break
            if conf == n - 1:
                e = C[conf]; st = min(L[brk:conf + 1].min() - 0.2 * a[conf], e - a[conf]); tg = H[max(0, brk - 60):brk].max()
                if e - st > 0 and (tg - e) / (e - st) >= 1.5: return float(e), float(st), float(tg)
            break                                          # one line per anchor (as in the backtest)
    return None

def shadow_levels(d):
    H, L, C = d.high.values, d.low.values, d.close.values; a = atr(d); i = len(C) - 1
    if i < 70: return None
    e = C[i]; st = min(L[i - 9:i + 1].min() - 0.2 * a[i], e - a[i]); tg = H[i - 60:i].max()
    if e - st <= 0 or (tg - e) / (e - st) < 1.5: return None
    return float(e), float(st), float(tg)

def draw(key): return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 10**9 / 10**9

def yget(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5y&interval=1d"
    for _ in range(2):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
            r = j["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            d = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"]},
                             index=pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize())
            d = d.dropna(); d = d[~d.index.duplicated(keep="last")]
            now = pd.Timestamp.now(tz="America/New_York")
            if now.hour * 60 + now.minute < 16 * 60 + 30: d = d[d.index < now.tz_localize(None).normalize()]   # drop a live session
            return d
        except Exception:
            pass
    return None

def coin(sym):
    f = f"{DATA}/data_daily/{sym}.csv"
    if not os.path.exists(f): return None
    d = pd.read_csv(f); d["t"] = pd.to_datetime(d.t, unit="ms"); d = d.set_index("t").sort_index()[["open", "high", "low", "close"]].astype(float)
    return d[d.index < pd.Timestamp.utcnow().tz_localize(None).normalize()]          # completed UTC days only

def halted():
    f = f"{RUNS}/HALT.json"
    if not os.path.exists(f): return None
    try: h = json.load(open(f))
    except Exception: return {"flatten": 1, "reason": "HALT.json unreadable"}
    if not h.get("active"): return None
    ra = h.get("resume_after")
    if ra and pd.Timestamp(ra) < pd.Timestamp.utcnow().tz_localize(None).normalize(): return None
    return h

def step(p, d, day, fl):
    """Advance an open position by the bar dated `day`. Returns (R, how) when it closes, else None."""
    if day not in d.index: return None
    i = d.index.get_loc(day); H, L, C = d.high.values[i], d.low.values[i], d.close.values[i]; p["n"] += 1
    cR = 2 * COST[p["kind"]] * p["entry"] / (p["entry"] - p["stop"]); risk = p["entry"] - p["stop"]
    if fl in (1, 2): return (C - p["entry"]) / risk - cR, "halt"
    if L <= p["stop"]: return -1 - cR, "stop"
    if H >= p["target"]: return (p["target"] - p["entry"]) / risk - cR, "target"
    if p["n"] >= CAP: return (C - p["entry"]) / risk - cR, "cap"
    return None

if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H_ = halted(); fl = (H_.get("flatten", 1) if H_ else None)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {
        "started": today, "equity": START, "shadow_equity": START, "since": {}, "pos": [], "shadow": [], "closed": 0, "closed_shadow": 0,
        "spec": "daily trend-line retest, practitioner rules (doc 168)"}
    print(f"paper book v12 (daily trend-line retest) — {today} — equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}"
          + (f"  *** HALT flatten={fl} ***" if H_ else ""), flush=True)
    U = json.load(open(f"{RUNS}/range_universe.json"))["registered_universe"]
    D = {}
    for s in U:
        d = coin(s)
        if d is not None and len(d) > 200: D[s] = ("coin", d)
    nc = len(D)
    for s in ETFS:
        d = yget(s)
        if d is not None and len(d) > 200: D[s] = ("etf", d)
    print(f"  data: {nc} coins, {len(D) - nc} ETFs", flush=True)
    first = not st["since"]
    if first:
        for s, (k, d) in D.items(): st["since"][s] = str(d.index[-1].date())
        print("  first run — watermarks set at each symbol's last completed bar, nothing traded", flush=True)
    events = sorted({(dd, s) for s, (k, d) in D.items() for dd in d.index if s in st["since"] and dd > pd.Timestamp(st["since"][s])})
    for s, (k, d) in D.items():
        if s not in st["since"]: st["since"][s] = str(d.index[-1].date())         # a symbol that returns starts from now
    days = sorted({e[0] for e in events}); closed = []
    for day in days:
        for side in ("pos", "shadow"):
            keep = []
            for p in st[side]:
                if p["sym"] not in D: keep.append(p); continue
                r = step(p, D[p["sym"]][1], day, fl)
                if r is None: keep.append(p); continue
                R, how = r; key = "equity" if side == "pos" else "shadow_equity"
                st[key] += st[key] * RISK * R; st["closed" if side == "pos" else "closed_shadow"] += 1
                closed.append((side == "shadow", p, str(day.date()), R, how))
            st[side] = keep
        if H_: continue
        for s in sorted(s for dd, s in events if dd == day):
            if len(st["pos"]) >= MAXOPEN: break
            if any(p["sym"] == s for p in st["pos"]): continue
            k, d = D[s]; sig = entry_today(d[d.index <= day])
            if sig is None: continue
            e, sp, tg = sig
            st["pos"].append({"sym": s, "kind": k, "opened": str(day.date()), "entry": e, "stop": sp, "target": tg, "n": 0})
            print(f"  OPEN {s} ({k}) {day.date()} @ {e:.4g} stop {sp:.4g} target {tg:.4g} ({(tg-e)/(e-sp):.1f}R)", flush=True)
            pool = sorted(x for x, (kk, dd) in D.items() if kk == k and x != s and day in dd.index)
            for j in range(20):
                if not pool: break
                ss = pool[int(draw(f"v12|{day.date()}|{s}|{j}") * len(pool))]; dd = D[ss][1]; lv = shadow_levels(dd[dd.index <= day])
                if lv is None: continue
                st["shadow"].append({"sym": ss, "kind": k, "opened": str(day.date()), "entry": lv[0], "stop": lv[1], "target": lv[2], "n": 0})
                break
    for s, (k, d) in D.items(): st["since"][s] = str(max(pd.Timestamp(st["since"][s]), d.index[-1]).date())
    json.dump(st, open(STATE, "w"), indent=1)
    print(f"  closed {sum(1 for c in closed if not c[0])} real / {sum(1 for c in closed if c[0])} shadow; open {len(st['pos'])} "
          f"({', '.join(p['sym'] for p in st['pos'])}); equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}", flush=True)
    lines = ["CREATE TABLE IF NOT EXISTS pb12_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);",
             "CREATE TABLE IF NOT EXISTS pb12_trades (d TEXT, sym TEXT, kind TEXT, opened TEXT, closed TEXT, entry REAL, stop REAL, target REAL, r_mult REAL, how TEXT, shadow INTEGER);",
             f"INSERT OR REPLACE INTO pb12_equity VALUES ('{today}', {st['equity']:.4f}, {st['shadow_equity']:.4f}, {len(st['pos'])}, {st['closed']}, {st['closed_shadow']});"]
    for sh, p, cd, R, how in closed:
        lines.append(f"INSERT INTO pb12_trades VALUES ('{today}', '{p['sym']}', '{p['kind']}', '{p['opened']}', '{cd}', {p['entry']:.6g}, {p['stop']:.6g}, {p['target']:.6g}, {R:.4f}, '{how}', {1 if sh else 0});")
    out = f"{RUNS}/paper12_{today}.sql"; open(out, "w").write("\n".join(lines)); print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
