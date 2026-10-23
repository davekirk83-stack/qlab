"""
THE PAPER BOOK v3 — "Range v3, single mid-EMA target" (registered 19 Oct 2026, doc 91).
IDENTICAL to Range v2.2 (paperbook2.py) in universe (registered 27), switch, cooldown, bids
(15/25/30/30% at +0.30/+0.05/-0.25/-0.55 ATR), stop and costs. The ONE change: every lot exits
at the mid EMA instead of the three-step scale-out (40% mid / 40% band / 20% band+0.35).
Five-year backtest: +0.207%/ep (t 63), 72% win, median +0.49%, hold ~1h, 100% of coins, 100% of
months; over the live window 16-19 Oct +0.028%/ep where v2.2 did -0.014%. Runs BESIDE v2.2,
never instead of it (rule 165 spirit). State runs/paper6_state.json, D1 pb6_equity / pb6_trades.
"""

import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, glob, urllib.request, urllib.error
import numpy as np, pandas as pd

DATA = "/home/claude/qlab/data_15m"
RUNS = "/home/claude/qlab/runs"
STATE = f"{RUNS}/paper6_state.json"
BASE = "https://api.exchange.coinbase.com"
UA = {"User-Agent": "Mozilla/5.0"}
GRAN = 900

SLOTS, LEV = 40, 3.0
MK, TAKER, SLIP = 1.5/10000, 4.5/10000, 5/10000
BID = [(0.15, 0.30), (0.25, 0.05), (0.30, -0.25), (0.30, -0.55)]
ASK = [(1.0, "mid")]          # v3 (doc 91): ONE target at the mid EMA; the only change from v2.2
CAP_BARS, MARGIN_STOP = 48, 0.15
COOLDOWN_H = 6
LONGS_OFF = False  # kill switch flatten=2: shorts only (DK, 16 Oct: 'squeaky bum time')   # doc 74: no new episode on a coin/side within 6h of its last close
CHASE_FILL, CHASE_PREM = 0.92, 0.05
START = 2000.0


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=25) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503): time.sleep(1.5*(k+1)); continue
            return None
        except Exception:
            time.sleep(1.0*(k+1))
    return None


CACHE = "/home/claude/qlab/data_15m_cache"   # last ~1,500 bars per coin, committed to the repo
MEDIANS = f"{RUNS}/contain_median.json"      # per-coin containment median from the full 5y history
_MED = {}
try: _MED = json.load(open(MEDIANS))
except Exception: pass


def universe():
    full = {os.path.basename(f)[:-4] for f in glob.glob(f"{DATA}/*USD.csv")}
    cached = {os.path.basename(f)[:-7] for f in glob.glob(f"{CACHE}/*USD.csv.gz")}
    # v2.2: the universe is the REGISTERED 27 — the coins every range-book
    # backtest was measured on (runs/range_universe.json). Not whatever is
    # cached. A young coin joins only after it has a backtest of its own.
    try:
        reg = set(json.load(open(f"{RUNS}/range_universe.json"))["registered_universe"])
    except Exception:
        reg = set()
    return sorted((full | cached) & reg) if reg else []


def _load(sym):
    """Full 5y file if this container has it, else the committed cache."""
    for path in (f"{DATA}/{sym}.csv", f"{CACHE}/{sym}.csv.gz"):
        try:
            d = pd.read_csv(path, index_col=0)
            d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
            return d[~d.index.duplicated(keep="last")].sort_index()
        except Exception:
            continue
    return None


def refresh(sym):
    """Top up one product's 15-minute file with the newest candles."""
    path = f"{DATA}/{sym}.csv"
    pid = sym[:-3] + "-USD"
    d = _load(sym)
    if d is None: return None
    last = d.index.max()
    now = pd.Timestamp.utcnow().floor("15min")
    if (now - last) < pd.Timedelta(minutes=30):
        return d
    t = now; got = []
    span = pd.Timedelta(seconds=GRAN*300)
    while t > last and t > now - pd.Timedelta(days=12):
        a = max(t-span, last)
        c = get(f"{BASE}/products/{pid}/candles?granularity={GRAN}"
                f"&start={a.isoformat()}&end={t.isoformat()}")
        time.sleep(0.15)
        if c: got.extend(c)
        t = a
    if got:
        n = pd.DataFrame(got, columns=["t","low","high","open","close","volume"])
        n.index = pd.to_datetime(n.t, unit="s", utc=True)
        n = n[["open","high","low","close","volume"]].astype(float)
        d = pd.concat([d, n])
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if os.path.exists(path): d.to_csv(path)
        os.makedirs(CACHE, exist_ok=True)
        d.tail(3000).to_csv(f"{CACHE}/{sym}.csv.gz", compression="gzip")
    return d


def indicators(d, sym=None):
    C, H, L = d.close.values, d.high.values, d.low.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    a = pd.Series(tr).rolling(14).mean().bfill().values
    ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
    lo_b, hi_b = ema-2*a, ema+2*a
    inside = ((C <= hi_b) & (C >= lo_b)).astype(float)
    contain = pd.Series(inside).rolling(50).mean()
    # The switch: containment above its own median. The median is taken over
    # the coin's full five-year history (runs/contain_median.json, refreshed
    # monthly); a fresh container only carries the last ~1,500 bars, and the
    # expanding median of those would not be the registered threshold.
    m = _MED.get(sym, {}).get("median") if sym else None
    thr = m if m is not None else contain.expanding(500).median()
    allow = (contain > thr).values
    return ema, lo_b, hi_b, a, allow


def step(sym, d, pos, since, slots_free, hold_regime=False):
    """hold_regime=True is the v3.1 variant (doc 120): a regime switch no longer forces an exit; positions leave only at the mid, a break, the cap or the stop. v3 itself is unchanged (hold_regime=False)."""
    """Replay the book over bars newer than `since`. Mutates pos; returns
    (closed_episodes, new_watermark)."""
    ema, lo_b, hi_b, a, allow = indicators(d, sym)
    C, H, L = d.close.values, d.high.values, d.low.values
    idx = d.index
    if since is None:
        # FIRST RUN: adopt the current bar as the watermark and trade nothing.
        # Replaying history here would book five years of backtest into the
        # paper ledger, which is exactly what a paper book exists not to do.
        return [], str(idx[-1])
    w = idx.searchsorted(pd.Timestamp(since)) + 1
    start = max(int(w), 250)
    closed = []
    for i in range(start, len(C)):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        for side in ("L", "S"):
            p = pos.get(side)
            if p is None: continue
            held = sum(x["sz"] for x in p["inv"])
            if held > 0:
                cost = sum(x["px"]*x["sz"] for x in p["inv"])/held
                stp = cost*(1-MARGIN_STOP/LEV) if side == "L" \
                      else cost*(1+MARGIN_STOP/LEV)
                hit = (L[i] <= stp) if side == "L" else (H[i] >= stp)
                if hit:
                    r = ((stp*(1-SLIP-TAKER))/(cost*(1+MK))-1) if side == "L" \
                        else ((cost*(1-MK))/(stp*(1+SLIP+TAKER))-1)
                    p["pnl"] += r*held
                    closed.append((sym, side, p["open"], str(idx[i]),
                                   p["pnl"]/max(p["intended"], 1e-9), "stop"))
                    pos[side] = None; slots_free[0] += 1; pos.setdefault('cool', {})[side] = str(idx[i]); continue
            broke = (C[i] < lo_b[i]-1.5*a[i]) or (C[i] > hi_b[i]+1.5*a[i])
            age = i - p["i0"]
            if age >= CAP_BARS or broke or (not ok and not hold_regime):
                if held > 0:
                    cost = sum(x["px"]*x["sz"] for x in p["inv"])/held
                    px = L[i] if side == "L" else H[i]
                    r = ((px*(1-SLIP-TAKER))/(cost*(1+MK))-1) if side == "L" \
                        else ((cost*(1-MK))/(px*(1+SLIP+TAKER))-1)
                    p["pnl"] += r*held
                closed.append((sym, side, p["open"], str(idx[i]),
                               p["pnl"]/max(p["intended"], 1e-9),
                               "break" if broke else ("cap" if age >= CAP_BARS
                                                      else "regime")))
                pos[side] = None; slots_free[0] += 1; pos.setdefault('cool', {})[side] = str(idx[i]); continue
            # scale out
            for k, (frac, lvl) in enumerate(ASK):
                if k in p["sold"]: continue
                if side == "L":
                    tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                    fire = H[i] >= tgt
                else:
                    tgt = ema[i] if lvl == "mid" else lo_b[i]-lvl*a[i]
                    fire = L[i] <= tgt
                if fire and p["inv"]:
                    sz = sum(x["sz"] for x in p["inv"]); sell = min(sz*frac, sz)
                    cost = sum(x["px"]*x["sz"] for x in p["inv"])/sz
                    r = ((tgt*(1-MK))/(cost*(1+MK))-1) if side == "L" \
                        else ((cost*(1-MK))/(tgt*(1+MK))-1)
                    p["pnl"] += r*sell
                    p["sold"].append(k)
                    for x in p["inv"]: x["sz"] *= (1-sell/sz)
                    p["inv"] = [x for x in p["inv"] if x["sz"] > 1e-9]
                    if not p["inv"]:
                        closed.append((sym, side, p["open"], str(idx[i]),
                                       p["pnl"]/max(p["intended"], 1e-9), "sold"))
                        pos[side] = None; slots_free[0] += 1; pos.setdefault('cool', {})[side] = str(idx[i]); break
        if not ok: continue
        for side in ("L", "S"):
            p = pos.get(side)
            if p is None:
                if LONGS_OFF and side == "L": continue
                ct = pos.get("cool", {}).get(side)
                if ct and idx[i] < pd.Timestamp(ct) + pd.Timedelta(hours=COOLDOWN_H):
                    continue
                p = {"open": str(idx[i]), "i0": i, "inv": [], "sold": [],
                     "intended": 0.0, "pnl": 0.0, "tried": []}
            for k, (frac, off) in enumerate(BID):
                if k in p["tried"]: continue
                price = (lo_b[i]+off*a[i]) if side == "L" else (hi_b[i]-off*a[i])
                touched = (L[i] < price) if side == "L" else (H[i] > price)
                if not touched: continue
                p["tried"].append(k)
                p["intended"] += frac
                px = price + (CHASE_PREM*a[i] if side == "L" else -CHASE_PREM*a[i])
                p["inv"].append({"px": float(px), "sz": frac*CHASE_FILL})
                if pos.get(side) is None:
                    if slots_free[0] <= 0: break
                    p["i0"] = i; pos[side] = p; slots_free[0] -= 1
            if p["intended"] > 0 and pos.get(side) is None:
                if slots_free[0] <= 0: continue
                p["i0"] = i; pos[side] = p; slots_free[0] -= 1
    return closed, str(idx[-1])


def sql_escape(s): return str(s).replace("'", "''")


def halted():
    """The kill switch. The scheduled task reads pb_halt from D1 and writes
    runs/HALT.json before any book runs; this honours it. Fail-safe: if the
    file is unreadable we treat it as a halt, because the failure mode of
    trading when told not to is worse than the failure mode of skipping a day."""
    f = f"{RUNS}/HALT.json"
    if not os.path.exists(f): return None
    try:
        h = json.load(open(f))
    except Exception:
        return {"reason": "HALT.json unreadable — treating as halted",
                "flatten": 1, "resume_after": None}
    if not h.get("active"): return None
    ra = h.get("resume_after")
    if ra and pd.Timestamp(ra, tz="UTC") < pd.Timestamp.utcnow().normalize():
        return None                      # the agreed period has expired
    return h


if __name__ == "__main__":
    os.makedirs(RUNS, exist_ok=True)
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H = halted()
    st = {"equity": START, "sym": {}, "closed": 0, "started": today}
    if os.path.exists(STATE):
        try: st = json.load(open(STATE))
        except Exception: pass
    syms = universe()
    print(f"paper book v3 (mid target) — {today} — {len(syms)} products, "
          f"equity ${st['equity']:,.2f}", flush=True)
    halt_lines = []
    if H and int(H.get("flatten", 1)) == 2:
        # SHORTS ONLY: close every long, open no longs, let shorts run.
        print(f"  *** SHORTS ONLY: {H.get('reason')} ***", flush=True)
        LONGS_OFF = True; n = 0
        for sym, rec in st["sym"].items():
            p = rec["pos"].get("L")
            if not p: continue
            r = p["pnl"]/max(p["intended"], 1e-9)
            st["equity"] += (st["equity"]/SLOTS)*r*LEV
            halt_lines.append("INSERT INTO pb6_trades (d, sym, side, opened, closed, "
                              f"ret, how) VALUES ('{today}', '{sql_escape(sym)}', 'L', "
                              f"'{sql_escape(p['open'])}', '{today}', {r:.6f}, 'halt');")
            rec["pos"]["L"] = None; rec["pos"].setdefault("cool", {})["L"] = today; n += 1
        print(f"  closed {n} longs; shorts continue", flush=True)
        H = None
    if H:
        print(f"  *** HALTED: {H.get('reason')} ***", flush=True)
        lines = []
        if H.get("flatten", 1):
            n = 0
            for sym, rec in st["sym"].items():
                for side in ("L", "S"):
                    p = rec["pos"].get(side)
                    if not p: continue
                    r = p["pnl"]/max(p["intended"], 1e-9)
                    st["equity"] += (st["equity"]/SLOTS)*r*LEV
                    lines.append(
                        "INSERT INTO pb6_trades (d, sym, side, opened, closed, "
                        f"ret, how) VALUES ('{today}', '{sql_escape(sym)}', "
                        f"'{side}', '{sql_escape(p['open'])}', '{today}', "
                        f"{r:.6f}, 'halt');")
                    rec["pos"][side] = None; n += 1
            print(f"  flattened {n} positions at the halt", flush=True)
        else:
            print("  holding existing positions, opening nothing", flush=True)
        json.dump(st, open(STATE, "w"), indent=1)
        lines.insert(0, "INSERT OR REPLACE INTO pb6_equity (d, equity, "
                     "open_positions, closed_total) VALUES "
                     f"('{today}', {st['equity']:.4f}, 0, {st['closed']});")
        out = f"{RUNS}/paper6_{today}.sql"
        open(out, "w").write("\n".join(lines))
        print(f"  SQL -> {out}", flush=True)
        raise SystemExit(0)
    open_now = sum(1 for v in st["sym"].values()
                   for k in ("L", "S") if v.get("pos", {}).get(k))
    slots_free = [SLOTS - open_now]
    all_closed = []
    # v3.1 ledger (doc 120): same coins, same bars, hold through the regime switch. Runs BESIDE v3; its own equity and positions.
    v31 = st.setdefault("v31", {"started": today, "equity": START, "sym": {}, "closed": 0, "spec": "Range v3.1 hold-through-regime (doc 120)"})
    open31 = sum(1 for v in v31["sym"].values() for k in ("L", "S") if v.get("pos", {}).get(k)); slots31 = [SLOTS - open31]; closed31 = []
    for s in syms:
        d = refresh(s)
        if d is None or len(d) < 600: continue
        rec = st["sym"].setdefault(s, {"since": None, "pos": {"L": None, "S": None}})
        try:
            closed, wm = step(s, d, rec["pos"], rec["since"], slots_free)
        except Exception as e:
            print(f"  {s}: {e}", flush=True); continue
        rec["since"] = wm
        all_closed.extend(closed)
        rec31 = v31["sym"].setdefault(s, {"since": None, "pos": {"L": None, "S": None}})
        try:
            c31, wm31 = step(s, d, rec31["pos"], rec31["since"], slots31, hold_regime=True)
        except Exception as e:
            print(f"  {s} v31: {e}", flush=True); continue
        rec31["since"] = wm31; closed31.extend(c31)
    # book the P&L: each episode gets one slot's worth of margin
    per = st["equity"]/SLOTS
    for c in all_closed:
        st["equity"] += per*c[4]*LEV
    st["closed"] += len(all_closed)
    per31 = v31["equity"]/SLOTS
    for c in closed31: v31["equity"] += per31*c[4]*LEV
    v31["closed"] += len(closed31)
    open31_n = sum(1 for v in v31["sym"].values() for k in ("L", "S") if v["pos"].get(k))
    print(f"  v3.1: closed {len(closed31)} episodes, {open31_n} open, equity ${v31['equity']:,.2f} (v3 minus v3.1 = {st['equity']-v31['equity']:+,.2f})", flush=True)
    open_n = sum(1 for s in st["sym"].values()
                 for k in ("L", "S") if s["pos"].get(k))
    print(f"  closed {len(all_closed)} episodes, {open_n} open, "
          f"equity ${st['equity']:,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)

    lines = halt_lines + [f"INSERT OR REPLACE INTO pb6_equity (d, equity, open_positions, closed_total, equity_v31, open_v31, closed_v31) "
             f"VALUES ('{today}', {st['equity']:.4f}, {open_n}, {st['closed']}, {v31['equity']:.4f}, {open31_n}, {v31['closed']});"]
    for c in closed31[:200]:
        lines.append(
            "INSERT INTO pb6_trades (d, sym, side, opened, closed, ret, how) "
            f"VALUES ('{today}', '{sql_escape(c[0])}@v31', '{c[1]}', "
            f"'{sql_escape(c[2])}', '{sql_escape(c[3])}', {c[4]:.6f}, '{c[5]}');")
    for c in all_closed[:400]:
        lines.append(
            "INSERT INTO pb6_trades (d, sym, side, opened, closed, ret, how) "
            f"VALUES ('{today}', '{sql_escape(c[0])}', '{c[1]}', "
            f"'{sql_escape(c[2])}', '{sql_escape(c[3])}', {c[4]:.6f}, '{c[5]}');")
    out = f"{RUNS}/paper6_{today}.sql"
    open(out, "w").write("\n".join(lines))
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
