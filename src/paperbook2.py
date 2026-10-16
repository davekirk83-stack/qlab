"""
THE PAPER BOOK v2 — the containment range book, two-sided, run once a day.

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading
only. No live order, brokerage or exchange account, credential, authentication,
or committed capital of any size, on any signal, under any circumstance. This
script opens nothing, holds no key, and talks to one public read-only
market-data endpoint. Everything it "does" is a row in a database.

WHY THIS REPLACES v1. The old paper book traded the daily Keltner config from
14-15 October. Everything registered since has superseded it: the switch is
containment rather than low volatility (doc 105/115), exits fill at the worst
tick (107), the stop is on margin not price (109), the book runs both sides
(110), and the whole thing was rebuilt after two accounting bugs (119/120).
Paper-trading the old config would accumulate evidence about a book we no
longer believe in.

HOW A 15-MINUTE BOOK IS PAPER-TRADED ON A DAILY CADENCE. Each run fetches the
most recent 15-minute candles - bars that did not exist when the model was
built - and replays the book across ONLY the bars it has not already seen.
Open inventory carries across runs in the state file. The decisions are
therefore made on genuinely unseen data even though the recording happens
once a day. What this cannot capture is intrabar sequencing, so fills use the
same conservative conventions as the backtest: maker entry, worst-tick exits
on a break.

THE REGISTERED CONFIGURATION
  bars        15-minute
  cooldown    no new episode on a coin/side within 6h of its last close
              (doc 74: re-entries inside 6h lost -0.19%/ep, t=-18; the 6h
              gate lifts the book from 60% to 77% CAGR at 1x, 21/27 coins,
              6/6 years). Added 16 Oct 2026, day one of the record = v2.1
  switch      containment above its own expanding median (doc 115 - NOT
              tightened, and no efficiency/ADX confirmation stacked on it)
  centre      EMA 20, bands +/- 2.0 ATR14
  long        4 bids at +0.30/+0.05/-0.25/-0.55 ATR from the lower band
  short       the mirror at the upper band
  exits       40% at mid, 40% at the band, rest 0.35 ATR beyond
  break       close beyond the band by 1.5 ATR, filled at the worst tick
  stop        15% of posted margin (doc 109)
  hold cap    48 bars
  slots       40, shared between the two sides (doc 120)
  entry       modelled as a CHASE order: 92% fill, 0.05 ATR worse (doc 121/122)

Emits SQL to runs/paper2_<date>.sql rather than writing directly, because the
database is reached through a tool rather than a driver.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, glob, urllib.request, urllib.error
import numpy as np, pandas as pd

DATA = "/home/claude/qlab/data_15m"
RUNS = "/home/claude/qlab/runs"
STATE = f"{RUNS}/paper2_state.json"
BASE = "https://api.exchange.coinbase.com"
UA = {"User-Agent": "Mozilla/5.0"}
GRAN = 900

SLOTS, LEV = 40, 3.0
MK, TAKER, SLIP = 1.5/10000, 4.5/10000, 5/10000
BID = [(0.15, 0.30), (0.25, 0.05), (0.30, -0.25), (0.30, -0.55)]
ASK = [(0.4, "mid"), (0.4, 0.0), (1.0, 0.35)]
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


def universe():
    return sorted(os.path.basename(f)[:-4]
                  for f in glob.glob(f"{DATA}/*USD.csv"))


def refresh(sym):
    """Top up one product's 15-minute file with the newest candles."""
    path = f"{DATA}/{sym}.csv"
    pid = sym[:-3] + "-USD"
    try:
        d = pd.read_csv(path, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True)
    except Exception:
        return None
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
        d.to_csv(path)
    return d


def indicators(d):
    C, H, L = d.close.values, d.high.values, d.low.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    a = pd.Series(tr).rolling(14).mean().bfill().values
    ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
    lo_b, hi_b = ema-2*a, ema+2*a
    inside = ((C <= hi_b) & (C >= lo_b)).astype(float)
    contain = pd.Series(inside).rolling(50).mean()
    allow = (contain > contain.expanding(500).median()).values
    return ema, lo_b, hi_b, a, allow


def step(sym, d, pos, since, slots_free):
    """Replay the book over bars newer than `since`. Mutates pos; returns
    (closed_episodes, new_watermark)."""
    ema, lo_b, hi_b, a, allow = indicators(d)
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
            if age >= CAP_BARS or broke or not ok:
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
    print(f"paper book v2 — {today} — {len(syms)} products, "
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
            halt_lines.append("INSERT INTO pb2_trades (d, sym, side, opened, closed, "
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
                        "INSERT INTO pb2_trades (d, sym, side, opened, closed, "
                        f"ret, how) VALUES ('{today}', '{sql_escape(sym)}', "
                        f"'{side}', '{sql_escape(p['open'])}', '{today}', "
                        f"{r:.6f}, 'halt');")
                    rec["pos"][side] = None; n += 1
            print(f"  flattened {n} positions at the halt", flush=True)
        else:
            print("  holding existing positions, opening nothing", flush=True)
        json.dump(st, open(STATE, "w"), indent=1)
        lines.insert(0, "INSERT OR REPLACE INTO pb2_equity (d, equity, "
                     "open_positions, closed_total) VALUES "
                     f"('{today}', {st['equity']:.4f}, 0, {st['closed']});")
        out = f"{RUNS}/paper2_{today}.sql"
        open(out, "w").write("\n".join(lines))
        print(f"  SQL -> {out}", flush=True)
        raise SystemExit(0)
    open_now = sum(1 for v in st["sym"].values()
                   for k in ("L", "S") if v.get("pos", {}).get(k))
    slots_free = [SLOTS - open_now]
    all_closed = []
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
    # book the P&L: each episode gets one slot's worth of margin
    per = st["equity"]/SLOTS
    for c in all_closed:
        st["equity"] += per*c[4]*LEV
    st["closed"] += len(all_closed)
    open_n = sum(1 for s in st["sym"].values()
                 for k in ("L", "S") if s["pos"].get(k))
    print(f"  closed {len(all_closed)} episodes, {open_n} open, "
          f"equity ${st['equity']:,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)

    lines = halt_lines + [f"INSERT OR REPLACE INTO pb2_equity (d, equity, open_positions, closed_total) "
             f"VALUES ('{today}', {st['equity']:.4f}, {open_n}, {st['closed']});"]
    for c in all_closed[:400]:
        lines.append(
            "INSERT INTO pb2_trades (d, sym, side, opened, closed, ret, how) "
            f"VALUES ('{today}', '{sql_escape(c[0])}', '{c[1]}', "
            f"'{sql_escape(c[2])}', '{sql_escape(c[3])}', {c[4]:.6f}, '{c[5]}');")
    out = f"{RUNS}/paper2_{today}.sql"
    open(out, "w").write("\n".join(lines))
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
