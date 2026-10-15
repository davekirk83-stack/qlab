"""
THE PAPER BOOK — Keltner Range v1, run once a day.

SIMULATED LEDGER ONLY. Standing constraint CAP-021: research and paper trading
only, no live order, brokerage or exchange account, credential, or committed
capital of any size, on any signal, under any circumstance. This script opens
nothing, holds no key, and talks to one public read-only market-data endpoint.
Everything it "does" is a row in a database.

EACH RUN, IN ORDER
  1. refresh the last ~300 daily candles for every product in the universe
  2. mark open positions to today's bar: stop hit, target hit, or 16 days up
  3. evaluate the market gate - equal-weight index above its own 200-day mean,
     using yesterday's value so nothing peeks at today
  4. if the gate is on, scan for entries and fill into free slots
  5. write equity, positions and a one-line log to D1

It emits SQL rather than writing directly, because the database is reached
through a tool rather than a driver. The SQL goes to runs/paper_<date>.sql and
is applied by the caller.

WHY THIS AND NOT A BACKTEST. Eleven years of history says the book works. A
backtest cannot be wrong in public. A paper ledger accumulating day by day,
with every decision written down before the outcome is known, is the only
thing that can be - and it is the only evidence that will mean anything in
six months.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, glob, urllib.request, urllib.error
import numpy as np, pandas as pd

OUT = "/home/claude/qlab/data_daily"
RUNS = "/home/claude/qlab/runs"
BASE = "https://api.exchange.coinbase.com"
UA = {"User-Agent": "Mozilla/5.0"}
GRAN = 86400

SLOTS, LEV = 40, 3.0
KBAND, EFF, T_ATR, S_ATR, HOLD = 2.0, 0.30, 0.5, 3.0, 16
MAKER, TAKER, SLIP = 2/10000, 5/10000, 10/10000
MINBARS = 500


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503): time.sleep(1.2*(k+1)); continue
            return None
        except Exception:
            time.sleep(0.8*(k+1))
    return None


def refresh(symbols):
    """Top up each product's CSV with the most recent candles."""
    n_new = 0
    for s in symbols:
        pid = s[:-3] + "-USD" if s.endswith("USD") else s
        c = get(f"{BASE}/products/{pid}/candles?granularity={GRAN}")
        if not c: continue
        d = pd.DataFrame(c, columns=["ts", "low", "high", "open", "close", "volume"])
        d["t"] = d.ts.astype("int64")*1000
        d = d[["t", "open", "high", "low", "close", "volume"]]
        path = f"{OUT}/{s}.csv"
        if os.path.exists(path):
            old = pd.read_csv(path)
            before = len(old)
            d = pd.concat([old, d]).drop_duplicates("t").sort_values("t")
            n_new += len(d) - before
        d.to_csv(path, index=False)
        time.sleep(0.12)
    return n_new


def load():
    out = {}
    for p in sorted(glob.glob(f"{OUT}/*.csv")):
        d = pd.read_csv(p)
        if len(d) < MINBARS: continue
        d.index = pd.to_datetime(d.t, unit="ms")
        out[os.path.basename(p)[:-4]] = d[["open", "high", "low", "close", "volume"]].sort_index()
    return out


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net/np.where(gross > 0, gross, np.nan)


def gate_on(data):
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    C = C[C.notna().sum(axis=1) >= 8]
    idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
    ma = idx.rolling(200).mean()
    sig = (idx > ma).shift(1)          # yesterday's reading: no peeking
    v = sig.dropna()
    return (bool(v.iloc[-1]), float(idx.iloc[-1]), float(ma.iloc[-1])) if len(v) else (False, np.nan, np.nan)


def todays_signals(data):
    out = []
    for s, d in data.items():
        if len(d) < 150: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr_np(H, L, C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - KBAND*a
        eff = efficiency(C)
        i = len(C)-1
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        if not (eff[i] < EFF): continue
        if not (C[i] <= lower[i] and C[i-1] > lower[i-1]): continue
        stop = C[i]-S_ATR*a[i]
        if stop <= 0: continue
        out.append(dict(sym=s, px=float(C[i]), atr=float(a[i]),
                        stop=float(stop), target=float(C[i]+T_ATR*a[i]),
                        asof=str(d.index[i].date())))
    return out


def q(x):
    return "NULL" if x is None else ("'" + str(x).replace("'", "''") + "'")


if __name__ == "__main__":
    state_path = f"{RUNS}/paper_state.json"
    st = json.load(open(state_path)) if os.path.exists(state_path) else \
        dict(equity=2000.0, positions=[], started=None)

    data = load()
    syms = list(data)
    print(f"universe {len(syms)} products", flush=True)
    if "--refresh" in sys.argv:
        print(f"refreshed {refresh(syms)} new candles", flush=True)
        data = load()

    today = max(d.index[-1] for d in data.values())
    tstr = str(today.date())
    on, idx, ma = gate_on(data)
    print(f"as of {tstr}: gate {'ON' if on else 'OFF'} "
          f"(index {idx:.3f} vs 200d mean {ma:.3f})", flush=True)

    sql = []
    # ---- 2. mark open positions ----
    closed = 0
    still = []
    for p in st["positions"]:
        d = data.get(p["sym"])
        if d is None or d.index[-1] <= pd.Timestamp(p["opened"]):
            still.append(p); continue
        seg = d[d.index > pd.Timestamp(p["opened"])]
        exit_px = reason = None
        for ts, row in seg.iterrows():
            if row.low <= p["stop"]:
                exit_px, reason = p["stop"]*(1-SLIP-TAKER), "stop"; break
            if row.high >= p["target"]:
                exit_px, reason = p["target"]*(1-MAKER), "target"; break
            if (ts - pd.Timestamp(p["opened"])).days >= HOLD:
                exit_px, reason = float(row.close)*(1-MAKER), "time"; break
        if exit_px is None:
            still.append(p); continue
        r = exit_px/(p["entry"]*(1+MAKER)) - 1
        pnl = max(r*LEV*p["margin"], -p["margin"])
        st["equity"] += pnl
        closed += 1
        sql.append("UPDATE pb_positions SET status='closed', closed={}, exit_px={}, "
                   "exit_reason={}, ret={}, pnl={} WHERE sym={} AND opened={} AND status='open';"
                   .format(q(tstr), round(exit_px, 8), q(reason), round(r, 6),
                           round(pnl, 2), q(p["sym"]), q(p["opened"])))
    st["positions"] = still

    # ---- 3/4. entries ----
    sigs = todays_signals(data) if on else []
    held = {p["sym"] for p in st["positions"]}
    taken = dropped = 0
    for s in sigs:
        if s["sym"] in held: dropped += 1; continue
        if len(st["positions"]) >= SLOTS: dropped += 1; continue
        margin = st["equity"]/SLOTS
        if margin <= 0: dropped += 1; continue
        pos = dict(sym=s["sym"], opened=tstr, entry=s["px"], stop=s["stop"],
                   target=s["target"], atr=s["atr"], margin=margin)
        st["positions"].append(pos); held.add(s["sym"]); taken += 1
        sql.append("INSERT INTO pb_positions (sym,opened,entry,stop,target,atr,margin,lev,status) "
                   "VALUES ({},{},{},{},{},{},{},{},'open');".format(
                       q(s["sym"]), q(tstr), round(s["px"], 8), round(s["stop"], 8),
                       round(s["target"], 8), round(s["atr"], 8), round(margin, 2), LEV))

    note = (f"{len(sigs)} signals, {taken} taken, {dropped} dropped, "
            f"{closed} closed, {len(st['positions'])} open")
    sql.append("INSERT OR REPLACE INTO pb_equity (d,equity,open_pos,gate,signals_seen,taken,dropped,note) "
               "VALUES ({},{},{},{},{},{},{},{});".format(
                   q(tstr), round(st["equity"], 2), len(st["positions"]), int(on),
                   len(sigs), taken, dropped, q(note)))

    if st["started"] is None: st["started"] = tstr
    json.dump(st, open(state_path, "w"), indent=1)
    out = f"{RUNS}/paper_{tstr}.sql"
    open(out, "w").write("\n".join(sql))

    print(f"\nEQUITY ${st['equity']:,.2f}   open {len(st['positions'])}/{SLOTS}")
    print(note)
    if sigs and on:
        print("\ntoday's signals:")
        for s in sigs[:20]:
            print(f"  {s['sym']:<12} px {s['px']:>12,.4f}  stop {s['stop']:>12,.4f}  "
                  f"target {s['target']:>12,.4f}")
    print(f"\nSQL -> {out} ({len(sql)} statements)")
