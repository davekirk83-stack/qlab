"""
THE PAPER BOOK v5 — "Golden-cross long v1". Pre-registered 19 Oct 2026 (doc 83).

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading
only. No live order, brokerage or exchange account, credential, authentication,
or committed capital of any size, on any signal, under any circumstance. This
script opens nothing, holds no key, and talks to one public read-only
market-data endpoint. Everything it "does" is a row in a database.

WHAT IT TESTS (finding 152, doc 83). The CONFIRMED golden cross on 4-hour
bars - the 20/50 cross has happened and within 20 bars the ribbon has opened
(EMA20 more than 0.5 ATR above EMA50) with the close above EMA20 - taken only
while BTC is above its own 4h EMA200, held 18 bars (3 days) with a 3-ATR
safety stop: +1.49%/episode (t=5.2) vs +0.21% for a random long with the same
exit, 78% of coins, split-half +0.8/+1.1. A fat-tail trade: the top 5% of
trades carry more than all the profit, so the shadow matters. The old text
below is the short book this was cloned from; the code is the long version.

ORIGINAL (v4): On 4-hour bars the anticipated 20/50
death cross - fast EMA still above the slow one, within 0.25 ATR of it and
converging for three bars - followed by a 3-ATR trailing stop earned
+1.09%/episode (t=5.3) against +0.18% for a random short with the same exit,
in 85% of coins and in four of six years with two ties. The first trend-style
entry in this project to beat random. This book finds out whether it holds on
bars the model has never seen.

THE REGISTERED CONFIGURATION
  bars       4-hour, built from the 15-minute cache
  universe   the registered 27 minus BTC and ETH (DK: no directional short on
             either) = 25 alts
  signal     EMA20 > EMA50, gap < 0.25 ATR14, gap shrinking for 3 bars, first
             bar it qualifies (one signal per approach)
  entry      short at the close of the signal bar, 4.5bp taker
  exit       stop 3 x ATR14(at entry) above the lowest low since entry, checked
             every bar at the worst tick; 180-bar (30-day) cap at the close;
             4.5bp taker out
  one position per coin; up to 20 open; each gets equity/20 of margin at 3x
  SHADOW     for every real entry a random coin from the universe is shorted at
             the same bar with the identical exit - the time-matched control.
             The measured quantity is REAL minus SHADOW, not the raw P&L.
  KILL       flatten=1 closes everything at the close and blocks entries;
             flatten=2 (shorts only) leaves this book running - it is a short
  PASS/FAIL  minimum 120 closed trades or 6 months; PASS if mean > 0 net of
             costs AND beats the shadow; FAIL otherwise; early kill if any
             25-trade block is worse than -3%
  Any change to the above voids the run and restarts the clock.

Emits SQL to runs/paper5_<date>.sql (tables pb5_equity, pb5_trades).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, hashlib
import numpy as np, pandas as pd
import paperbook2 as PB

RUNS = PB.RUNS
STATE = f"{RUNS}/paper5_state.json"
COST = 4.5/10000
SLOTS, LEV, START = 20, 3.0, 2000.0
K_STOP, HOLD, OPEN_ATR, CONFIRM_WIN = 3.0, 18, 0.5, 20
EXCLUDE = set()


def universe():
    return [s for s in PB.universe() if s not in EXCLUDE]


def bars4h(d):
    d4 = d.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    # only COMPLETED 4h bars: drop the last one if it is still forming
    now = pd.Timestamp.utcnow()
    if len(d4) and d4.index[-1] + pd.Timedelta(hours=4) > now:
        d4 = d4.iloc[:-1]
    return d4


def indicators(d4):
    C, H, L = d4.close.values, d4.high.values, d4.low.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    a = pd.Series(tr).rolling(14).mean().bfill().values
    ef = pd.Series(C).ewm(span=20, adjust=False).mean().values
    es = pd.Series(C).ewm(span=50, adjust=False).mean().values
    diff = ef - es
    gap = np.abs(diff)/np.maximum(a, 1e-12)
    up = (diff > 0) & (np.roll(diff, 1) <= 0)
    e200 = pd.Series(C).ewm(span=200, adjust=False).mean().values
    sig = np.zeros(len(C), dtype=bool)
    for i in np.where(up)[0]:
        if i < 60: continue
        for k in range(i+1, min(i+CONFIRM_WIN+1, len(C))):
            if ef[k] < es[k]: break
            if C[k] > ef[k] > es[k] and (ef[k]-es[k]) > OPEN_ATR*a[k]: sig[k] = True; break
    return C, H, L, a, sig, e200


def manage(pos, H, L, C, i, idx):
    """Advance one open short through bar i. Returns (closed_row or None)."""
    stop = pos["entry"] - K_STOP*pos["atr"]
    pos["bars"] += 1
    if L[i] <= stop:
        px = min(stop, C[i]) if pos["bars"] == 1 else stop
        ret = (px*(1-COST))/(pos["entry"]*(1+COST)) - 1
        return (pos["sym"], pos["opened"], str(idx[i]), ret, "stop", pos["shadow"])
    if pos["bars"] >= HOLD:
        ret = (C[i]*(1-COST))/(pos["entry"]*(1+COST)) - 1
        return (pos["sym"], pos["opened"], str(idx[i]), ret, "hold", pos["shadow"])
    return None


def pick_shadow(syms, key):
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return syms[h % len(syms)]


if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H_ = PB.halted()
    st = {"equity": START, "shadow_equity": START, "sym": {}, "shadow": {}, "closed": 0,
          "closed_shadow": 0, "started": today, "spec": "Golden-cross long v1 (doc 83)"}
    if os.path.exists(STATE):
        try: st = json.load(open(STATE))
        except Exception: pass
    syms = universe()
    print(f"paper book v5 (golden-cross long) — {today} — {len(syms)} alts, "
          f"equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}", flush=True)
    flatten = H_.get("flatten", 1) if H_ else 0
    if H_: print(f"  *** HALT: {H_.get('reason')} (flatten={flatten}) ***", flush=True)
    block_entries = flatten in (1, 2)  # a LONG book: shorts-only mode blocks it too

    data = {}
    for s in syms:
        d = PB.refresh(s)
        if d is None or len(d) < 600: continue
        d4 = bars4h(d)
        if len(d4) < 80: continue
        data[s] = indicators(d4) + (d4.index,)
    btc = data.get("BTCUSD")

    closed, closed_sh = [], []
    open_real = sum(1 for v in st["sym"].values() if v.get("pos"))
    for s, (C, H, L, a, sig, e200, idx) in data.items():
        rec = st["sym"].setdefault(s, {"since": None, "pos": None})
        start = 0 if rec["since"] is None else int(np.searchsorted(idx, pd.Timestamp(rec["since"]), side="right"))
        if rec["since"] is None:
            # first sight of this coin: set the watermark at the frontier, open nothing
            rec["since"] = str(idx[-1]); continue
        for i in range(start, len(C)):
            # 1. manage the open real position on this coin
            if rec["pos"]:
                row = manage(rec["pos"], H, L, C, i, idx)
                if row: closed.append(row); rec["pos"] = None; open_real -= 1
            # 2. manage shadow positions that live on this coin
            for key, sp in list(st["shadow"].items()):
                if sp["sym"] != s or sp.get("done"): continue
                if pd.Timestamp(sp["opened"]) >= idx[i]: continue
                row = manage(sp, H, L, C, i, idx)
                if row: closed_sh.append(row); st["shadow"].pop(key)
            # 3. flatten on a halt (1 = everything, 2 = all longs - this is a long)
            if flatten in (1, 2) and rec["pos"]:
                p = rec["pos"]; ret = (C[i]*(1-COST))/(p["entry"]*(1+COST)) - 1
                closed.append((s, p["opened"], str(idx[i]), ret, "halt", False)); rec["pos"] = None; open_real -= 1
            # 4. new signal
            bull = True
            if btc is not None:
                kb = int(np.searchsorted(btc[6], idx[i], side="right")) - 1
                bull = kb >= 0 and btc[0][kb] > btc[5][kb]
            if sig[i] and bull and not rec["pos"] and not block_entries and open_real < SLOTS:
                rec["pos"] = {"sym": s, "opened": str(idx[i]), "entry": float(C[i]), "atr": float(a[i]),
                              "best": float(C[i]), "bars": 0, "shadow": False}
                open_real += 1
                # time-matched shadow: a random coin at the same bar, same exit
                sh = pick_shadow(syms, f"{s}|{idx[i]}")
                if sh in data:
                    C2, H2, L2, a2, _, _, idx2 = data[sh]
                    j = int(np.searchsorted(idx2, idx[i], side="right")) - 1
                    if j >= 0:
                        st["shadow"][f"{s}|{idx[i]}"] = {"sym": sh, "opened": str(idx2[j]), "entry": float(C2[j]),
                                                        "atr": float(a2[j]), "best": float(C2[j]), "bars": 0, "shadow": True}
        rec["since"] = str(idx[-1])

    # v1.1 parallel arm (doc 132, DK 26 Oct): identical signal, exit and shadow, but gated on the COIN'S OWN 4h EMA200
    # instead of BTC's. v1 above is untouched; this ledger opens from its first run (watermark adopted, nothing traded).
    v = st.setdefault("v11", {"equity": START, "shadow_equity": START, "sym": {}, "shadow": {}, "closed": 0, "closed_shadow": 0, "started": today})
    c11, cs11 = [], []; open11 = sum(1 for x in v["sym"].values() if x.get("pos"))
    for s, (C, H, L, a, sig, e200, idx) in data.items():
        rec = v["sym"].setdefault(s, {"since": None, "pos": None})
        if rec["since"] is None: rec["since"] = str(idx[-1]); continue
        start = int(np.searchsorted(idx, pd.Timestamp(rec["since"]), side="right"))
        for i in range(start, len(C)):
            if rec["pos"]:
                row = manage(rec["pos"], H, L, C, i, idx)
                if row: c11.append(row); rec["pos"] = None; open11 -= 1
            for key, sp in list(v["shadow"].items()):
                if sp["sym"] != s or pd.Timestamp(sp["opened"]) >= idx[i]: continue
                row = manage(sp, H, L, C, i, idx)
                if row: cs11.append(row); v["shadow"].pop(key)
            if flatten in (1, 2) and rec["pos"]:
                p = rec["pos"]; ret = (C[i]*(1-COST))/(p["entry"]*(1+COST)) - 1
                c11.append((s, p["opened"], str(idx[i]), ret, "halt", False)); rec["pos"] = None; open11 -= 1
            if sig[i] and C[i] > e200[i] and not rec["pos"] and not block_entries and open11 < SLOTS:
                rec["pos"] = {"sym": s, "opened": str(idx[i]), "entry": float(C[i]), "atr": float(a[i]), "best": float(C[i]), "bars": 0, "shadow": False}
                open11 += 1
                sh = pick_shadow(syms, f"{s}|{idx[i]}|v11")
                if sh in data:
                    C2, H2, L2, a2, _, _, idx2 = data[sh]; j = int(np.searchsorted(idx2, idx[i], side="right")) - 1
                    if j >= 0: v["shadow"][f"{s}|{idx[i]}"] = {"sym": sh, "opened": str(idx2[j]), "entry": float(C2[j]), "atr": float(a2[j]), "best": float(C2[j]), "bars": 0, "shadow": True}
        rec["since"] = str(idx[-1])
    for c in c11: v["equity"] += v["equity"]/SLOTS*c[3]*LEV
    for c in cs11: v["shadow_equity"] += v["shadow_equity"]/SLOTS*c[3]*LEV
    v["closed"] += len(c11); v["closed_shadow"] += len(cs11)
    print(f"  v1.1 (own EMA200 gate): closed {len(c11)} real / {len(cs11)} shadow, {open11} open, equity ${v['equity']:,.2f} / shadow ${v['shadow_equity']:,.2f}", flush=True)

    per = st["equity"]/SLOTS
    for c in closed: st["equity"] += per*c[3]*LEV
    per_s = st["shadow_equity"]/SLOTS
    for c in closed_sh: st["shadow_equity"] += per_s*c[3]*LEV
    st["closed"] += len(closed); st["closed_shadow"] += len(closed_sh)
    open_n = sum(1 for v in st["sym"].values() if v.get("pos"))
    print(f"  closed {len(closed)} real / {len(closed_sh)} shadow, {open_n} open, "
          f"equity ${st['equity']:,.2f} / shadow ${st['shadow_equity']:,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)

    lines = [f"INSERT OR REPLACE INTO pb5_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) "
             f"VALUES ('{today}', {st['equity']:.4f}, {st['shadow_equity']:.4f}, {open_n}, {st['closed']}, {st['closed_shadow']});"]
    lines.append("CREATE TABLE IF NOT EXISTS pb5_v11_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);")
    lines.append(f"INSERT OR REPLACE INTO pb5_v11_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('{today}', {v['equity']:.4f}, {v['shadow_equity']:.4f}, {open11}, {v['closed']}, {v['closed_shadow']});")
    for c in c11 + cs11:
        lines.append("INSERT INTO pb5_trades (d, sym, opened, closed, ret, how, shadow) "
                     f"VALUES ('{today}', '{PB.sql_escape(c[0])}@v11', '{PB.sql_escape(c[1])}', '{PB.sql_escape(c[2])}', {c[3]:.6f}, '{c[4]}', {1 if c[5] else 0});")
    for c in (closed + closed_sh)[:400]:
        lines.append("INSERT INTO pb5_trades (d, sym, opened, closed, ret, how, shadow) "
                     f"VALUES ('{today}', '{PB.sql_escape(c[0])}', '{PB.sql_escape(c[1])}', '{PB.sql_escape(c[2])}', "
                     f"{c[3]:.6f}, '{c[4]}', {1 if c[5] else 0});")
    out = f"{RUNS}/paper5_{today}.sql"
    open(out, "w").write("\n".join(lines))
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
