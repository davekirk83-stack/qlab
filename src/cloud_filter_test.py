"""Doc 165 — the Ichimoku daily cloud as a FILTER on existing books (doc 163 conclusion: entries fail, the cloud may be a regime filter).
DK 30 Oct: "Sure". Pre-registered 30 Oct 2026 before any result.
CLOUD: classic 9/26/52/26 on daily bars (coins: UTC days from the 15m data; stocks: the daily file). State known at the day's open = the PRIOR
  completed day's close vs that day's plotted (causal) cloud: ABOVE / INSIDE / BELOW.
RULE: longs only on ABOVE days; shorts only on BELOW days. Applied to each book's own trade list (entry day's state); kept vs removed compared.
BOOKS: saucer book 9 (BTC+ETH 3h, no daily filter) and book 10 (10 coins, daily-jaw filter) — doc 145d engine; golden-cross 4h confirmed,
  hold 12 (book 5 lead, golden_verify); range ladder v3 (27 coins, paperbook6.step, long and short); stock book 11 MV and EP (doc 151 engine).
SPLIT: crypto dev < 2025-01-01, holdout after (saucer keeps its own sealed 2025-04-01). Stocks: one window from Dec 2023 (too short to split).
VERDICT per book: filter 'helps' only if kept-trade mean beats the unfiltered mean in BOTH dev and holdout and total P&L is not cut by more
  than the removed trades lost. Usage: python cloud_filter_test.py saucer|golden|range|stocks"""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab/src")
PART = sys.argv[1]
OUT = open(f"runs/cloud_filter_{PART}.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
def cloud_state(dy):
    mid = lambda n: (dy.high.rolling(n).max() + dy.low.rolling(n).min()) / 2
    A = ((mid(9) + mid(26)) / 2).shift(26); B = mid(52).shift(26)
    top, bot = np.maximum(A, B), np.minimum(A, B)
    st = pd.Series(np.where(dy.close > top, 1, np.where(dy.close < bot, -1, 0)), index=dy.index).where(top.notna())
    st = st.shift(1); st.index = pd.DatetimeIndex(st.index).tz_localize(None) if st.index.tz is not None else st.index
    return st
_CL = {}
def coin_state(sym):
    if sym not in _CL:
        d = pd.read_csv(f"data_15m/{sym}.csv"); d["t"] = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d.set_index("t")
        dy = d.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        _CL[sym] = cloud_state(dy)
    return _CL[sym]
def tag(df, getstate):
    days = pd.DatetimeIndex(pd.to_datetime(df.ts, utc=True)).tz_localize(None).normalize()
    df["state"] = [getstate(s).reindex([dd], method="ffill").iloc[0] for s, dd in zip(df.sym, days)]
    return df
def compare(name, df, split=pd.Timestamp("2025-01-01", tz="UTC"), unit="%"):
    df = df.dropna(subset=["state"]).copy(); k = 100 if unit == "%" else 1
    df["keep"] = ((df.side == 1) & (df.state == 1)) | ((df.side == -1) & (df.state == -1))
    ts = pd.to_datetime(df.ts, utc=True)
    segs = [("all", np.ones(len(df), bool))] if split is None else [("dev", (ts < split).values), ("hold", (ts >= split).values)]
    log(f"\n{name}")
    for seg, m in segs:
        a = df[m]; kk, rr = a[a.keep].val, a[~a.keep].val
        if len(a) < 5: log(f"  {seg}: n{len(a)}"); continue
        t = (kk.mean() - rr.mean()) / np.sqrt(kk.var() / max(len(kk), 1) + rr.var() / max(len(rr), 1)) if len(kk) > 2 and len(rr) > 2 else np.nan
        log(f"  {seg}: UNFILTERED n{len(a)} mean {k*a.val.mean():+.3f}{unit} sum {k*a.val.sum():+.1f}{unit} | KEPT n{len(kk)} mean {k*kk.mean():+.3f}{unit} "
            f"sum {k*kk.sum():+.1f}{unit} | REMOVED n{len(rr)} mean {k*rr.mean():+.3f}{unit} sum {k*rr.sum():+.1f}{unit} (t {t:+.1f})")
        for sd in sorted(a.side.unique()):
            b = a[a.side == sd]
            log("     " + ("long " if sd == 1 else "short") + " by state: " + " | ".join(
                f"{lab} n{(b.state == v).sum()} {k*b[b.state == v].val.mean():+.3f}{unit}" for lab, v in (("above", 1), ("inside", 0), ("below", -1))))
# ----------------------------------------------------------------------------------------------------------------
if PART == "saucer":
    exec(open("src/saucer_refine_test.py").read().split("def eligible")[0])
    for nm, syms, daily in (("SAUCER book 9 (BTC+ETH 3h, no daily filter)", ["BTCUSD", "ETHUSD"], False),
                            ("SAUCER book 10 (10 coins 3h, daily-jaw filter)", TEN, True)):
        rows = []
        for s in syms:
            d = load(s); B = build(d)
            rows += [(s, t, r, 1) for t, r in run(d, B, daily=daily)]
        df = tag(pd.DataFrame(rows, columns=["sym", "ts", "val", "side"]), coin_state)
        compare(nm, df, split=HOLD)
elif PART == "golden":
    import crossover as X, golden_scaled as G, golden_tight as T, golden_tight2 as T2
    X.CAP = 180; X.X_MIN_GAP = 2
    P = T.build(X.load(), "4h"); rows = []
    for s in P:
        p = P[s]; last = -10**9
        for i in T2.entries(P, s, "confirmed"):
            if i - last < X.X_MIN_GAP: continue
            last = i; r, _, _ = G.hold(p["C"], p["H"], p["L"], p["a"], i, 1, 12); rows.append((s, p["idx"][i], r, 1))
    df = tag(pd.DataFrame(rows, columns=["sym", "ts", "val", "side"]), coin_state)
    compare(f"GOLDEN CROSS 4h confirmed, hold 12 ({len(P)} coins)", df)
elif PART == "range":
    import json, paperbook6 as P
    syms = json.load(open("runs/range_universe.json"))["registered_universe"]; rows = []
    for s in syms:
        d = pd.read_csv(f"data_15m/{s}.csv"); d["ts"] = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d.set_index("ts")[["open", "high", "low", "close"]].astype(float)
        P._MED = {}; pos = {}
        try: closed, _ = P.step(s, d, pos, str(d.index[250]), [40])
        except Exception as e: log(f"{s} ERROR {e}"); continue
        rows += [(s, c[2], c[4], 1 if c[1] == "L" else -1) for c in closed]; print(s, len(closed), flush=True)
    df = tag(pd.DataFrame(rows, columns=["sym", "ts", "val", "side"]), coin_state)
    compare("RANGE LADDER v3 (27 coins, per-episode return)", df)
elif PART == "stocks":
    src = open("src/legends_faithful_test.py").read().split("import multiprocessing as mp")[0]
    a = 'out.append((x["idx"][i], res[0], res[1], res[2]))'; assert src.count(a) == 1
    exec(src.replace(a, 'out.append((x["idx"][i], res[0], res[1], res[2], s))'))
    ST = {}
    def stk_state(s):
        if s not in ST:
            x = X[s]; ST[s] = cloud_state(pd.DataFrame({"high": x["H"], "low": x["L"], "close": x["C"]}, index=pd.DatetimeIndex(x["idx"])))
        return ST[s]
    for nm, setup in (("STOCK book 11 MV (Minervini VCP, SPY filter)", "MV"), ("STOCK book 11 EP (episodic pivot, QQQ filter)", "EP")):
        t, _ = run(setup, None)
        df = pd.DataFrame([(q[4], q[0], q[1] / max(q[2], 0.002), 1) for q in t], columns=["sym", "ts", "val", "side"])
        df = tag(df, stk_state); compare(nm + " — R per trade", df, split=None, unit="R")
log("done")
