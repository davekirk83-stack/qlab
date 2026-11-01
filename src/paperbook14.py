"""
THE PAPER BOOK v14 — "Range longs on Revolut X", registered 1 Nov 2026 (doc 173; DK 1 Nov "aim for another £500" and "Yes").
The £500 spot-crypto pot run on paper: Range v3 (paperbook6 engine, unchanged, registered contain_median.json) LONG SIDE ONLY, on
REVOLUT X'S OWN 15-minute candles, so its fills are the prices that venue actually printed — not Coinbase's.

SIMULATED LEDGER ONLY. CAP-021: no account, key or money; Revolut X public market data only (no authentication).

THE REGISTERED RULES (any change voids the run and restarts the clock)
  universe   the 27 registered coins less ZEC (not listed on Revolut X): 26 coins, X/USD pairs
  data       Revolut X public candles (revx.revolut.com/api/1.0/public/candles/<COIN>-USD?interval=15, last ~1,000 bars) merged into
             data_rx_cache/<COIN>USD.csv.gz each run; the book needs 250 bars of warm-up, so it trades from its start date onward
  engine     paperbook6.step, longs only (short episodes are discarded — spot cannot short)
  costs      Revolut X: 0% maker (ladder bids, mid-EMA exit), 0.09% taker + 0.10% slippage on taker fills (stops, regime, cap)
  pool       start £500 on 1 Nov 2026; each episode takes 10% of current equity; at most 10 open; taken in time order; no leverage
  twin       the SAME rules on Coinbase candles (data_15m_cache) over the same days — the gap between the two is the venue's fill cost
  replay     replayed from 1 Nov 2026 every run (no state file); the cache is the memory
  verdict    after 3 months: PASS if the Revolut X pool is positive with max drawdown no worse than -15%, up in at least 2 of 3 months,
             and within half of its Coinbase twin's return (i.e. the venue does not eat more than half the edge)
Backtest (doc 173, last 12 months, Coinbase prices, Revolut X costs): £500 -> £2,887, maxDD -7%, 12/12 months up. Revolut X candles
track Coinbase closely (median close gap 0.02-0.3%) but reach Coinbase's lows within 0.05% on only ~60-86% of bars, so fewer fills.
Emits runs/paper14_<date>.sql (pb14_equity, pb14_trades).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, urllib.request, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); RUNS = f"{ROOT}/runs"; RXC = f"{ROOT}/data_rx_cache"; CBC = f"{ROOT}/data_15m_cache"
import paperbook6 as P
START = pd.Timestamp(os.environ.get("PB14_START", "2026-11-01"), tz="UTC"); EQ0, FRAC, MAXOPEN = 500.0, 0.10, 10
TK, SL = 0.0009, 0.0010

def rx_get(path):
    for k in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request("https://revx.revolut.com/api/" + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
        except Exception as e:
            if "429" in str(e): time.sleep(10 * (k + 1)); continue
            raise

def refresh(sym):
    os.makedirs(RXC, exist_ok=True); f = f"{RXC}/{sym}.csv.gz"
    old = pd.read_csv(f, index_col=0, parse_dates=True) if os.path.exists(f) else pd.DataFrame()
    try:
        d = rx_get(f"1.0/public/candles/{sym[:-3]}-USD?interval=15")["data"]
        new = pd.DataFrame(d); new.index = pd.to_datetime(new.start, unit="ms", utc=True); new = new[["open", "high", "low", "close", "volume"]].astype(float)
        new = new[new.index < pd.Timestamp.utcnow().floor("15min")]                       # completed bars only
        b = pd.concat(([old] if len(old) else []) + [new]); b.index = pd.to_datetime(b.index, utc=True)
        b = b[~b.index.duplicated(keep="last")].sort_index(); b.to_csv(f)
    except Exception as e:
        print(f"  {sym}: Revolut X fetch failed ({e}) — using cache", flush=True); b = old
    if len(b): b.index = pd.to_datetime(b.index, utc=True)
    return b

def episodes(d, sym):
    if d is None or len(d) < 300: return []
    d = d[["open", "high", "low", "close"]].astype(float)
    closed, _ = P.step(sym, d, {}, str(d.index[250]), [40])
    out = []
    for c in closed:
        o, cl = pd.Timestamp(c[2]), pd.Timestamp(c[3]); o = o.tz_localize("UTC") if o.tzinfo is None else o; cl = cl.tz_localize("UTC") if cl.tzinfo is None else cl
        if c[1] == "L" and o >= START: out.append((sym, o, cl, float(c[4]), c[5]))
    return out

def pool(E):
    eq = hi = EQ0; mdd = 0.0; open_ = []; rows = []
    for sym, o, cl, r, how in sorted(E, key=lambda x: x[1]):
        open_.sort(key=lambda x: x[0])
        while open_ and open_[0][0] <= o:
            tc, pnl, row = open_.pop(0); eq += pnl; hi = max(hi, eq); mdd = min(mdd, eq / hi - 1); rows.append(row)
        if len(open_) >= MAXOPEN: continue
        pnl = eq * FRAC * r; open_.append((cl, pnl, (sym, o, cl, r, how, pnl)))
    for tc, pnl, row in sorted(open_, key=lambda x: x[0]): eq += pnl; hi = max(hi, eq); mdd = min(mdd, eq / hi - 1); rows.append(row)
    return eq, mdd, rows

if __name__ == "__main__":
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    P.MK, P.TAKER, P.SLIP = 0.0, TK, SL
    U = [s for s in json.load(open(f"{RUNS}/range_universe.json"))["registered_universe"] if s != "ZECUSD"]
    RX, CB = [], []
    for s in U:
        b = refresh(s); time.sleep(1.5)
        if len(b) and b.index.max() < pd.Timestamp.utcnow() - pd.Timedelta(hours=6): print(f"  {s}: Revolut X data stale ({b.index.max()})", flush=True)
        RX += episodes(b, s)
        f = f"{CBC}/{s}.csv.gz" if os.path.exists(f"{CBC}/{s}.csv.gz") else f"{CBC}/{s}.csv"
        if os.path.exists(f):
            c = pd.read_csv(f); c.index = pd.to_datetime(c.iloc[:, 0], utc=True, format="ISO8601")
            if len(b): c = c[c.index <= b.index.max()]                                    # same days as the Revolut X record
            CB += episodes(c, s)
    eq, mdd, rows = pool(RX); eqc, mddc, rowsc = pool(CB)
    print(f"paper book v14 (Range longs on Revolut X) — {today} — Revolut X £{eq:,.2f} ({len(rows)} episodes, maxDD {100*mdd:.1f}%) | "
          f"Coinbase twin £{eqc:,.2f} ({len(rowsc)} episodes) | gap £{eq - eqc:+.2f}", flush=True)
    lines = ["CREATE TABLE IF NOT EXISTS pb14_equity (d TEXT PRIMARY KEY, rx_equity REAL, cb_equity REAL, rx_closed INTEGER, cb_closed INTEGER, rx_max_dd REAL);",
             "CREATE TABLE IF NOT EXISTS pb14_trades (d TEXT, venue TEXT, sym TEXT, opened TEXT, closed TEXT, ret REAL, how TEXT, gbp REAL);",
             f"INSERT OR REPLACE INTO pb14_equity VALUES ('{today}', {eq:.4f}, {eqc:.4f}, {len(rows)}, {len(rowsc)}, {mdd:.4f});", "DELETE FROM pb14_trades;"]
    for venue, rr in (("RX", rows), ("CB", rowsc)):
        for sym, o, cl, r, how, pnl in rr:
            lines.append(f"INSERT INTO pb14_trades VALUES ('{today}', '{venue}', '{sym}', '{o}', '{cl}', {r:.6f}, '{how}', {pnl:.4f});")
    out = f"{RUNS}/paper14_{today}.sql"; open(out, "w").write("\n".join(lines)); print(f"  SQL -> {out} ({len(lines)} statements)", flush=True)
