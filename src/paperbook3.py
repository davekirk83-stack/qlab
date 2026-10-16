"""
THE PAPER BOOK v3 — the containment range book on ETFs, 15-minute bars.

SIMULATED LEDGER ONLY. CAP-021: research and paper trading only. No live order,
brokerage or exchange account, credential, authentication, or committed
capital of any size, on any signal, under any circumstance. This script opens
nothing, holds no key, and reads one public market-data endpoint.

WHY THIS BOOK EXISTS. Doc 133 showed the range book's edge transfers to
equities and commodities - +0.28% an episode over twenty years, two and a
half times the crypto figure - but that daily bars are too infrequent to
compound. The book is specified on 15-minute bars. Only sixty days of
15-minute ETF history is freely available, which cannot backtest anything,
but it can seed a forward record on the right timeframe. That is how the
crypto book is being proven, and it is the only evidence that will count.

So be clear about what this is: a book whose EDGE is validated on daily bars
over twenty years and whose TIMEFRAME is validated on crypto over five, now
run forward on the combination. The combination itself has no backtest. If
the forward record disagrees with both, the forward record wins.

WHAT DIFFERS FROM THE CRYPTO BOOK
  universe    the 37 ETFs of doc 133, minus bonds, which the test showed do
              not oscillate
  hours       bars exist only while the market is open; the book does not
              need to know that, but holds overnight and over weekends, and
              the break exit at the worst tick absorbs the gaps honestly
  costs       2bp a side, liquid-ETF commission-free terms
  shorting    both sides, as tested. In practice shorting an ETF needs margin
              and some are hard to borrow; recorded as a known gap

Same machinery as paperbook2: replay only unseen bars, carry open inventory
in a state file, honour the kill switch, emit SQL.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, urllib.request
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import paperbook2 as PB

DATA = "/home/claude/qlab/data_etf15"
RUNS = "/home/claude/qlab/runs"
STATE = f"{RUNS}/paper3_state.json"
UNIVERSE = ["USO","UNG","XLE","GLD","SLV","CPER","GDX","DBA","CORN","WEAT",
            "SPY","QQQ","IWM","DIA","XLF","XLK","XLV","XLU","XLP","XLI","XLB",
            "XLY","EEM","EFA","FXI","EWJ","EWZ","VXX","UUP","FXE","SLX","XME"]
PB.MK, PB.TAKER, PB.SLIP = 2/10000, 3/10000, 2/10000
PB.STATE = STATE
PB.RUNS = RUNS


def fetch15(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
           f"?interval=15m&range=60d")
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=30) as r:
            j = json.load(r)
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        d = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"],
                          "close": q["close"], "volume": q["volume"]},
                         index=pd.to_datetime(res["timestamp"], unit="s", utc=True))
        return d.dropna(subset=["close"]).astype(float)
    except Exception:
        return None


def refresh(sym):
    os.makedirs(DATA, exist_ok=True)
    path = f"{DATA}/{sym}.csv"
    new = fetch15(sym); time.sleep(0.3)
    old = None
    if os.path.exists(path):
        try:
            old = pd.read_csv(path, index_col=0)
            old.index = pd.to_datetime(old.index, utc=True, format="ISO8601")
        except Exception:
            old = None
    if new is None: return old
    d = pd.concat([old, new]) if old is not None else new
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d.to_csv(path)
    return d


if __name__ == "__main__":
    os.makedirs(RUNS, exist_ok=True)
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    H = PB.halted()
    st = {"equity": PB.START, "sym": {}, "closed": 0, "started": today}
    if os.path.exists(STATE):
        try: st = json.load(open(STATE))
        except Exception: pass
    print(f"paper book v3 (ETF) — {today} — {len(UNIVERSE)} instruments, "
          f"equity ${st['equity']:,.2f}", flush=True)
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
                    st["equity"] += (st["equity"]/PB.SLOTS)*r*PB.LEV
                    lines.append("INSERT INTO pb3_trades (d, sym, side, opened, closed, "
                                 f"ret, how) VALUES ('{today}', '{sym}', '{side}', "
                                 f"'{PB.sql_escape(p['open'])}', '{today}', {r:.6f}, 'halt');")
                    rec["pos"][side] = None; n += 1
            print(f"  flattened {n} positions at the halt", flush=True)
        json.dump(st, open(STATE, "w"), indent=1)
        lines.insert(0, "INSERT OR REPLACE INTO pb3_equity (d, equity, open_positions, "
                     f"closed_total) VALUES ('{today}', {st['equity']:.4f}, 0, {st['closed']});")
        open(f"{RUNS}/paper3_{today}.sql", "w").write("\n".join(lines))
        raise SystemExit(0)

    open_now = sum(1 for v in st["sym"].values()
                   for k in ("L", "S") if v.get("pos", {}).get(k))
    slots_free = [PB.SLOTS - open_now]
    all_closed = []
    for s in UNIVERSE:
        d = refresh(s)
        if d is None or len(d) < 600: continue
        rec = st["sym"].setdefault(s, {"since": None, "pos": {"L": None, "S": None}})
        try:
            closed, wm = PB.step(s, d, rec["pos"], rec["since"], slots_free)
        except Exception as e:
            print(f"  {s}: {e}", flush=True); continue
        rec["since"] = wm
        all_closed.extend(closed)
    per = st["equity"]/PB.SLOTS
    for c in all_closed:
        st["equity"] += per*c[4]*PB.LEV
    st["closed"] += len(all_closed)
    open_n = sum(1 for v in st["sym"].values()
                 for k in ("L", "S") if v["pos"].get(k))
    print(f"  closed {len(all_closed)} episodes, {open_n} open, "
          f"equity ${st['equity']:,.2f}", flush=True)
    json.dump(st, open(STATE, "w"), indent=1)
    lines = ["INSERT OR REPLACE INTO pb3_equity (d, equity, open_positions, closed_total) "
             f"VALUES ('{today}', {st['equity']:.4f}, {open_n}, {st['closed']});"]
    for c in all_closed[:400]:
        lines.append("INSERT INTO pb3_trades (d, sym, side, opened, closed, ret, how) "
                     f"VALUES ('{today}', '{PB.sql_escape(c[0])}', '{c[1]}', "
                     f"'{PB.sql_escape(c[2])}', '{PB.sql_escape(c[3])}', "
                     f"{c[4]:.6f}, '{c[5]}');")
    out = f"{RUNS}/paper3_{today}.sql"
    open(out, "w").write("\n".join(lines))
    print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
