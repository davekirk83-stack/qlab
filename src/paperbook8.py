"""
THE PAPER BOOK v8 — "Range v3-IDX" (registered 22 Oct 2026, doc 116). The Range v3 engine (paperbook6.step: containment
switch vs the instrument's own median, 4-rung ladder, single mid-EMA exit, two-sided, 48-bar cap, 6-h cooldown) on
IG-tradeable index markets, 15-minute bars built from Dukascopy 5-minute mids:
  Wall Street (USA30IDXUSD)  all hours      spread 2.0 pts
  Germany 40  (DEUIDXEUR)    all hours      spread 1.2 pts
  US Tech 100 (nq_5m.csv)    NY hours only  spread 1.0 pt   (13:00-20:00 UTC; the only cut that held in both halves)
COSTS: IG spread bet = half the spread each way + half a spread of slippage on market exits.
LEDGER: $2,000, SLOTS 12 (3 instruments x 2 sides x 2), LEV 3 — same accounting as the crypto range books.
SHADOW: 5 time-matched random episodes per real one (same side, same hold, same costs) — the verdict is REAL minus SHADOW.
DATA: each run pulls yesterday's day for the three Dukascopy instruments (src/pull_duka.py, incremental) and tops up nq_5m.csv
via paperbook7's pull. First run adopts the current bar as the watermark and trades nothing (paperbook6 rule).
SIMULATED ONLY (CAP-021). State runs/paper8_state.json; D1 pb8_equity / pb8_trades.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, subprocess
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import paperbook6 as P
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"; STATE = f"{RUNS}/paper8_state.json"
START, SLOTS, LEV, NCTRL = 2000.0, 12, 3.0, 5
INSTR = {  # name: (5-min csv, spread pts, point, UTC hours for NEW episodes or None)
    "WALLST": (f"{ROOT}/data_ig_cache/USA30IDXUSD_5m.csv", 2.0, "USA30IDXUSD", None),
    "DAX":    (f"{ROOT}/data_ig_cache/DEUIDXEUR_5m.csv", 1.2, "DEUIDXEUR", None),
    "NQ":     (f"{ROOT}/data_nq_cache/nq_5m.csv", 1.0, None, (9, 16)),   # New York local hours (= 13-20 UTC in summer)
}

def pull(name):
    src = INSTR[name][2]
    if src is None: return
    y = (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    try: subprocess.run([sys.executable, f"{ROOT}/src/pull_duka.py", src, "1000", "2026-04-15", y], timeout=1500, check=False)
    except Exception as e: print(f"  pull {name}: {e}", flush=True)

def load(name):
    d = pd.read_csv(INSTR[name][0], index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True)
    b = pd.DataFrame({"open": d.open.resample("15min").first(), "high": d.high.resample("15min").max(), "low": d.low.resample("15min").min(), "close": d.close.resample("15min").last()}).dropna()
    return b

def set_costs(name, b):
    sp = INSTR[name][1]; px = float(b.close.median()); hs = sp/2/px
    P.MK, P.TAKER, P.SLIP = hs, hs, sp*0.5/px

_orig_ind = P.indicators
def hours_gate(hours):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = _orig_ind(d, sym)
        if hours is None: return ema, lob, hib, a, allow
        ix = d.index if d.index.tz is not None else d.index.tz_localize("UTC")
        h = ix.tz_convert("America/New_York").hour; return ema, lob, hib, a, allow & ((h >= hours[0]) & (h < hours[1]))
    return ind

def shadow(b, closed, rng):
    """Time-matched random episodes: same side, same hold, same costs, from the trailing 30 days."""
    C = b.close.values; idx = b.index; out = []
    for (sym, side, o, c, ret, how) in closed:
        i = idx.searchsorted(pd.Timestamp(o)); k = max(int((pd.Timestamp(c) - pd.Timestamp(o)) / pd.Timedelta(minutes=15)), 1)
        lo = max(250, i - 30*96)
        if lo >= i - k - 1: continue
        for j in rng.choice(np.arange(lo, i - k), size=min(NCTRL, i - k - lo), replace=False):
            e = min(j + k, len(C) - 1); s = 1 if side == "L" else -1
            out.append(s*(C[e]/C[j] - 1) - 2*P.MK - P.SLIP)
    return out

if __name__ == "__main__":
    os.makedirs(RUNS, exist_ok=True)
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H = P.halted()
    st = {"equity": START, "shadow_equity": START, "sym": {}, "closed": 0, "closed_shadow": 0, "started": today, "spec": "Range v3-IDX (doc 116)"}
    if os.path.exists(STATE):
        try: st = json.load(open(STATE))
        except Exception: pass
    print(f"paper book v8 Range v3-IDX — {today} — equity ${st['equity']:,.2f} shadow ${st['shadow_equity']:,.2f}", flush=True)
    if H:
        flat = int(H.get("flatten", 1)); print(f"  *** HALT: {H.get('reason')} flatten={flat} ***", flush=True)
    if "--no-pull" not in sys.argv:
        for name in INSTR: pull(name)
    open_now = sum(1 for v in st["sym"].values() for k in ("L", "S") if v.get("pos", {}).get(k))
    slots_free = [SLOTS - open_now]; all_closed = []; all_shadow = []; rng = np.random.default_rng(int(pd.Timestamp(today).value % 2**32))
    for name, (path, sp, src, hours) in INSTR.items():
        if not os.path.exists(path): print(f"  {name}: no data", flush=True); continue
        b = load(name)
        if len(b) < 600: continue
        set_costs(name, b); P.indicators = hours_gate(hours); P._MED = {}
        P.LONGS_OFF = bool(H and int(H.get("flatten", 1)) == 2)
        rec = st["sym"].setdefault(name, {"since": None, "pos": {"L": None, "S": None}})
        if H and int(H.get("flatten", 1)) == 1:
            for side in ("L", "S"):
                p = rec["pos"].get(side)
                if p:
                    r = p["pnl"]/max(p["intended"], 1e-9); all_closed.append((name, side, p["open"], str(b.index[-1]), r, "halt")); rec["pos"][side] = None
            rec["since"] = str(b.index[-1]); continue
        try: closed, wm = P.step(name, b, rec["pos"], rec["since"], slots_free)
        except Exception as e: print(f"  {name}: {e}", flush=True); continue
        rec["since"] = wm; all_closed.extend(closed); all_shadow.extend(shadow(b, closed, rng))
        print(f"  {name}: bars to {b.index[-1]}, closed {len(closed)}, open {sum(1 for k in ('L','S') if rec['pos'].get(k))}", flush=True)
    P.indicators = _orig_ind
    per = st["equity"]/SLOTS
    for c in all_closed: st["equity"] += per*c[4]*LEV
    sper = st["shadow_equity"]/SLOTS
    for r in all_shadow: st["shadow_equity"] += sper*r*LEV/NCTRL
    st["closed"] += len(all_closed); st["closed_shadow"] += len(all_shadow)
    open_n = sum(1 for s in st["sym"].values() for k in ("L", "S") if s["pos"].get(k))
    print(f"  closed {len(all_closed)} episodes, {open_n} open, equity ${st['equity']:,.2f} shadow ${st['shadow_equity']:,.2f} gap {st['equity']-st['shadow_equity']:+,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)
    lines = ["CREATE TABLE IF NOT EXISTS pb8_equity (d TEXT PRIMARY KEY, equity REAL, shadow_equity REAL, open_positions INTEGER, closed_total INTEGER, closed_shadow INTEGER);",
             "CREATE TABLE IF NOT EXISTS pb8_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, d TEXT, sym TEXT, side TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT);",
             f"INSERT OR REPLACE INTO pb8_equity (d, equity, shadow_equity, open_positions, closed_total, closed_shadow) VALUES ('{today}', {st['equity']:.4f}, {st['shadow_equity']:.4f}, {open_n}, {st['closed']}, {st['closed_shadow']});"]
    for c in all_closed[:400]:
        lines.append(f"INSERT INTO pb8_trades (d, sym, side, opened, closed, ret, how) VALUES ('{today}', '{P.sql_escape(c[0])}', '{c[1]}', '{P.sql_escape(c[2])}', '{P.sql_escape(c[3])}', {c[4]:.6f}, '{c[5]}');")
    out = f"{RUNS}/paper8_{today}.sql"; open(out, "w").write("\n".join(lines) + "\n")
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
