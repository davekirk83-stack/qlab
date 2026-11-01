"""Doc 173 — what the crypto books make as LONG-ONLY SPOT on Revolut X (DK 1 Nov: "Okay I've downloaded Revolut x", after doc 172).
Costs: Revolut X 0% maker / 0.09% taker, plus 0.10% slippage per taker fill (thin book, conservative). No shorts, no leverage.
Books re-run on their own engines, long side only:
  RNG  Range v3 ladder (paperbook6), 27 registered coins, 15-min — bids are limit orders (maker 0%), exit at the mid EMA (limit, maker),
       stop/regime/cap exits are taker. MK=0, TAKER=0.09%, SLIP=0.10%.
  SAU  AO saucer v9.1 (10 coins + daily jaw filter, 3h) — buy-stop entries and trend-flip exits are taker: 0.19% per side.
  GC   Golden-cross 4h confirmed, hold 18 bars — taker both sides: 0.38% round trip.
  CVD  BTC 1h bullish CVD divergence, hold 72h — taker both sides: 0.19% per side.
Then ONE £500 spot pool: each trade takes 10% of current equity, at most 10 open at once (no leverage), trades taken in time order.
Windows: last 12 months (Nov 2025 - Oct 2026) and the full history."""
import sys, os, json, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
OUT = open("runs/spot_crypto_revolutx_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
SL, TK = 0.0010, 0.0009; SIDE = TK + SL
T = []
# ---- Range v3, longs
import paperbook6 as P
P.MK, P.TAKER, P.SLIP = 0.0, TK, SL
syms = json.load(open("runs/range_universe.json"))["registered_universe"]
for s in syms:
    d = pd.read_csv(f"data_15m/{s}.csv"); d["ts"] = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d.set_index("ts")[["open", "high", "low", "close"]].astype(float)
    P._MED = {}
    try: closed, _ = P.step(s, d, {}, str(d.index[250]), [40])
    except Exception as e: log(f"{s} range error {e}"); continue
    for c in closed:
        if c[1] == "L": T.append(("RNG", s, pd.Timestamp(c[2]), pd.Timestamp(c[3]), float(c[4])))
    print("range", s, flush=True)
# ---- AO saucer v9.1 (daily filter), 10 coins
_src = open("/home/claude/qlab-git/src/saucer_refine_test.py").read().split("def eligible")[0].replace("COST = 0.0015", f"COST = {SIDE}")
_src = _src.replace("def close(p, px, i): tr.append((idx[p[2]], px * (1 - COST) / p[0] - 1))", "def close(p, px, i): tr.append((idx[p[2]], px * (1 - COST) / p[0] - 1, idx[i]))")
assert "idx[i]))" in _src; exec(_src)
for s in TEN:
    d = load(s); B = build(d); tr = []
    ao, ema, state, O, H, L, C = B; idx = d.index
    for t0, r, t1 in run(d, B, daily=True):
        T.append(("SAU", s, pd.Timestamp(t0), pd.Timestamp(t1), r))
# ---- Golden cross 4h confirmed, hold 18
import crossover as X, golden_scaled as G, golden_tight as GT, golden_tight2 as T2
X.CAP = 180; X.X_MIN_GAP = 2; X.COST = 2 * SIDE; G.COST = 2 * SIDE
Pg = GT.build(X.load(), "4h")
for s in Pg:
    p = Pg[s]; last = -10**9
    for i in T2.entries(Pg, s, "bull+confirmed"):
        if i - last < X.X_MIN_GAP: continue
        last = i; r, b, _ = G.hold(p["C"], p["H"], p["L"], p["a"], i, 1, 18)
        T.append(("GC", s, pd.Timestamp(p["idx"][i]), pd.Timestamp(p["idx"][min(i + b, len(p["C"]) - 1)]), r))
# ---- BTC 1h bullish CVD divergence, X72
src = open("/home/claude/qlab-git/src/cvd_div_trade_test.py").read().split("lines = []")[0]; exec(src)
d = load("BTCUSDT", "1h"); res = run(d, 5, 24, True, SIDE)
for t0, Rm, r in res["X72"][True]: T.append(("CVD", "BTC", pd.Timestamp(t0), pd.Timestamp(t0) + pd.Timedelta(hours=77), r))
# ---- report
R = pd.DataFrame(T, columns=["eng", "sym", "to", "tc", "r"])
for c in ("to", "tc"): R[c] = pd.to_datetime(R[c], utc=True)
W0 = pd.Timestamp("2025-11-01", tz="UTC"); W1 = pd.Timestamp("2026-10-31", tz="UTC")
log("PER-TRADE, long only, Revolut X costs (0% maker / 0.09% taker + 0.10% slippage per taker fill)")
for e, g in R.groupby("eng"):
    yrs = max((g.to.max() - g.to.min()).days / 365, 0.1); w = g[(g.to >= W0) & (g.to < W1)]
    log(f"  {e:4} all: n{len(g):6} ({len(g)/yrs:5.0f}/yr) mean {100*g.r.mean():+.3f}% win {100*(g.r>0).mean():.0f}% | last 12m: n{len(w):5} mean {100*w.r.mean():+.3f}% win {100*(w.r>0).mean():.0f}%")
def pool(df, start=500.0, frac=0.10, maxopen=10):
    df = df.sort_values("to"); eq = start; hi = start; mdd = 0; open_ = []; mon = {}
    for r in df.itertuples():
        open_.sort(key=lambda x: x[0])
        while open_ and open_[0][0] <= r.to:
            tc, pnl = open_.pop(0); eq += pnl; hi = max(hi, eq); mdd = min(mdd, eq / hi - 1); mon[tc.strftime("%Y-%m")] = mon.get(tc.strftime("%Y-%m"), 0) + pnl
        if len(open_) >= maxopen: continue
        open_.append((r.tc, eq * frac * r.r))
    for tc, pnl in open_: eq += pnl; mon[tc.strftime("%Y-%m")] = mon.get(tc.strftime("%Y-%m"), 0) + pnl
    return eq, mdd, pd.Series(mon).sort_index()
log("\n£500 SPOT POOL, last 12 months (10% of equity per trade, max 10 open, no leverage)")
for lab, engs in (("Range v3 longs only", ["RNG"]), ("Saucer only", ["SAU"]), ("Golden cross only", ["GC"]), ("CVD only", ["CVD"]),
                  ("ALL FOUR", ["RNG", "SAU", "GC", "CVD"]), ("Range + saucer + CVD", ["RNG", "SAU", "CVD"])):
    df = R[R.eng.isin(engs) & (R.to >= W0) & (R.to < W1)]
    eq, dd, mon = pool(df)
    log(f"  {lab:24} trades {len(df):5} ({len(df)/12:.0f}/month) end £{eq:,.0f} ({100*(eq/500-1):+.0f}%) maxDD {100*dd:.0f}% | months up {(mon>0).sum()}/{len(mon)} | median month £{mon.median():+.0f}, worst £{mon.min():+.0f}")
eq, dd, mon = pool(R[R.eng.isin(["RNG", "SAU", "GC", "CVD"])])
log(f"\nALL FOUR over the full history ({R.to.min():%Y-%m} -> {R.to.max():%Y-%m}): £500 -> £{eq:,.0f}, maxDD {100*dd:.0f}%, months up {(mon>0).sum()}/{len(mon)}")
yr = mon.groupby(mon.index.str[:4]).sum(); log("  £ by year (compounding from £500): " + " ".join(f"{k}:{v:+,.0f}" for k, v in yr.items()))
log("done")
