"""LIQ book, DK-ladder version — DRY ONLY (paper). DK 22 Nov: "Yes do all of those on your list" (your scale-in and exits for the LIQ book).
Research (runs/research/liq_book_dk.txt, 15-min BTC 2021-26, Revolut X costs):
  LIQ as built (50/50 bids, target farthest short cluster): +0.076%/trade, halves +0.135/+0.017, 3 of 6 years positive.
  DK scale-in (10/20/30/40% at the cluster, -1%, -2%, -3%) + take-profit +3% above the average: +0.069%, halves +0.073/+0.064, 6 of 6 years positive.
  Random levels with the same ladder: +0.00 to +0.14 (avg ~+0.06) -> most of the gain comes from DK's ladder + exit shape, not from the cluster itself.
Rules: one ladder at a time at the revx_liq setup cluster (any regime; CPI blackout kept); rungs fill only within 48h; one take-profit
+3% above the average fill; stop 4% under the cluster; 7-day time exit. £50 per full ladder. State runs/revx_liq_ladder_dry/.
Also writes the daily liquidation-level snapshot (runs/liq_levels/YYYY-MM.csv) so DK's map levels can be tested later."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import revx_liq as X
ROOT = X.ROOT; OUT = f"{ROOT}/runs/revx_liq_ladder_dry"
RUNGS, W = [1.0, 0.99, 0.98, 0.97], [0.1, 0.2, 0.3, 0.4]
TP, STOP, FILL_H, HOLD_D, USD = 0.03, 0.04, 48, 7, 50.0 * X.USD_PER_GBP
TAKER, SLIP = 0.0009, 0.0005
if os.environ.get("REVX_LIQ_LADDER_LIVE_ENABLED"): sys.exit("revx_liq_ladder is paper only")

def snapshot(longs, shorts, px, now):
    d = f"{ROOT}/runs/liq_levels"; os.makedirs(d, exist_ok=True); f = f"{d}/{now:%Y-%m}.csv"; day = f"{now:%Y-%m-%d}"
    if os.path.exists(f) and day in open(f).read(): return
    rows = [{"date": day, "time_utc": f"{now:%H:%M}", "btc": round(px), "side": s, "level": round(l), "lev": v, "dist_pct": round(100 * (l / px - 1), 2)}
            for s, lst in (("long", longs), ("short", shorts)) for l, v in lst]
    pd.DataFrame(rows).to_csv(f, mode="a", header=not os.path.exists(f), index=False); X.log(f"liq-level snapshot: {len(rows)} levels -> {f}")

def run():
    os.makedirs(OUT, exist_ok=True); f = f"{OUT}/state.json"
    st = json.load(open(f)) if os.path.exists(f) else {"start": str(X.utcnow()), "eq": X.BOOK_GBP * X.USD_PER_GBP, "lad": None, "closed": []}
    rx = X.closed(X.revx15()); px = float(rx.close.iloc[-1]); now = X.utcnow()
    try: feed = X.closed(X.coinbase())
    except Exception: feed = rx
    longs, shorts = X.levels(feed); cs, _ = X.cpi_state(now, X.cpi_times()); snapshot(longs, shorts, px, now)
    new = rx[rx.index > pd.Timestamp(st.get("last_bar", str(rx.index[-2])))]; lad = st["lad"]
    if lad:
        lvl = lad["lvl"]
        for t, b in new.iterrows():
            age = (t - pd.Timestamp(lad["placed"])).total_seconds() / 3600
            for i, (r, w) in enumerate(zip(RUNGS, W)):
                if not lad["fill"][i] and age <= FILL_H and b.low <= lvl * r:
                    lad["fill"][i] = True; q = USD * w / (lvl * r); lad["q"] += q; lad["cost"] += q * lvl * r; X.log(f"rung {i+1} filled at {lvl*r:,.0f}")
            if lad["q"] == 0:
                if age > FILL_H: X.log("no fill in 48h - ladder cancelled"); lad = None; break
                continue
            avg = lad["cost"] / lad["q"]; why = px_out = None
            if b.low <= lvl * (1 - STOP): why, px_out = "stop -4%", lvl * (1 - STOP) * (1 - SLIP) * (1 - TAKER)
            elif b.high >= avg * (1 + TP): why, px_out = "target +3%", avg * (1 + TP)
            elif age >= HOLD_D * 24 or cs == "flat": why, px_out = ("7 days" if age >= HOLD_D * 24 else "CPI"), b.close * (1 - SLIP) * (1 - TAKER)
            if why:
                pnl = lad["q"] * px_out - lad["cost"]; st["eq"] += pnl
                st["closed"].append({"lvl": round(lvl), "opened": lad["placed"], "closed": str(t), "rungs": sum(lad["fill"]), "why": why, "pnl_usd": round(pnl, 2), "pnl_pct": round(100 * pnl / lad["cost"], 2)})
                X.log(f"EXIT ({why}) {sum(lad['fill'])} rungs: ${pnl:+.2f}"); lad = None; break
    if not lad and not cs:
        lvl, lev = X.pick(px, longs, shorts)
        if lvl: lad = {"lvl": lvl, "lev": lev, "placed": str(now), "fill": [False] * 4, "q": 0.0, "cost": 0.0}; X.log(f"ladder at {lvl:,.0f} ({lev}x): " + ", ".join(f"{lvl*r:,.0f}" for r in RUNGS))
    st["lad"], st["last_bar"] = lad, str(rx.index[-1]); json.dump(st, open(f, "w"), indent=1, default=str)
    c = pd.DataFrame(st["closed"]); X.log(f"ladder book ${st['eq']:.2f}; trades {len(c)}" + (f", total ${c.pnl_usd.sum():+.2f}" if len(c) else ""))

if __name__ == "__main__": run()
