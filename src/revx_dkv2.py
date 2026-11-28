"""DK v2 longs — PAPER ONLY on Revolut X BTC (docs 272-274; promotion rule: 2 weeks / 20+ trades on paper inside the backtest range
before any money). Backtest (src/research/dk_v2_improve.py run(ny=True), BTC 15-min 2021-26, Revolut X costs, 27 Nov checker fix):
+0.201%/campaign of the ladder budget, 274 campaigns, halves +0.209 / +0.193, max drawdown -8.7%.
Rules, exactly as the backtest:
  WHEN   at 07:00 and 13:00 UTC: level = lowest low of the previous 24h x 0.997 ("just under the obvious low"); only if the last close is
         within 3% above it; only in a deep flush (last daily close <= 85% of the 20-day high) or an uptrend (last daily close above the
         50- and 200-day means). One campaign at a time.
  LADDER 4 resting bids at level x (1 - step x r), r = 0..3, weights 10/20/30/40%; step = 0.3 x the 14-day ATR% (clipped 0.6%-3%);
         bids live 48h; maker (no fee).
  EXITS  a third off at +1.5% over the average fill (not on the first fill bar); the rest at +3%; stop one step under the deepest rung
         (taker 0.09% + 0.05% slip); flat before a US CPI release; 7-day limit.
£50 per full ladder (paper). State and ledger: runs/revx_dkv2_dry/."""
import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import revx_liq as X
if os.environ.get("REVX_DKV2_LIVE_ENABLED"): sys.exit("revx_dkv2 is paper only")
ROOT = X.ROOT; OUT = f"{ROOT}/runs/revx_dkv2_dry"; USD = 50.0 * X.USD_PER_GBP; TAKER, SLIP = 0.0009, 0.0005
W = (0.1, 0.2, 0.3, 0.4)

def daily():
    r = json.load(urllib.request.urlopen("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=400", timeout=30))
    d = pd.DataFrame(r).iloc[:, :5]; d.columns = ["t", "o", "h", "l", "c"]; d.index = pd.to_datetime(d.t, unit="ms", utc=True); d = d[["o", "h", "l", "c"]].astype(float)
    return d[d.index + pd.Timedelta("1D") <= X.utcnow()]                       # completed days only

def context(D, day):
    D = D[D.index < day]
    tr = np.maximum(D.h - D.l, np.maximum((D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs()))
    atrp = float((tr.rolling(14).mean() / D.c).iloc[-1]); c = D.c.iloc[-1]
    up = c > D.c.rolling(50).mean().iloc[-1] and c > D.c.rolling(200, min_periods=120).mean().iloc[-1]
    deep = c <= D.h.rolling(20).max().iloc[-1] * 0.85
    return atrp, bool(up), bool(deep)

def ledger(row):
    f = f"{OUT}/trades.csv"; new = not os.path.exists(f)
    pd.DataFrame([row]).to_csv(f, mode="a", header=new, index=False)

def run():
    os.makedirs(OUT, exist_ok=True); f = f"{OUT}/state.json"
    st = json.load(open(f)) if os.path.exists(f) else {"start": str(X.utcnow()), "camp": None, "busy_until": None, "last_bar": None}
    rx = X.closed(X.revx15()); now = X.utcnow(); cpis = X.cpi_times()
    last = pd.Timestamp(st["last_bar"]) if st["last_bar"] else rx.index[-2]
    new = rx[rx.index > last]; D = daily()
    for t, b in new.iterrows():
        c = st["camp"]
        if c:
            age_h = (t - pd.Timestamp(c["placed"])).total_seconds() / 3600
            for i, r in enumerate(c["rungs"]):
                if not c["fill"][i] and age_h < 48 and b.low <= r:
                    c["fill"][i] = True; q = USD * W[i] / r; c["q"] += q; c["cost"] += q * r; c.setdefault("first_fill", str(t)); X.log(f"DKv2 rung {i+1} filled at {r:,.0f}")
            if c["q"] > 0:
                avg = c["cost"] / c["q"]; why = px = None
                cs, _ = X.cpi_state(t + pd.Timedelta(minutes=15), cpis)
                if b.low <= c["stop"]: why, px = "stop", c["stop"] * (1 - SLIP) * (1 - TAKER)
                elif cs: why, px = "flat before CPI", b.close * (1 - SLIP) * (1 - TAKER)
                else:
                    if not c["part"] and t > pd.Timestamp(c["first_fill"]) and b.high >= avg * 1.015:
                        q = c["q"] / 3; c["pnl"] += q * avg * 0.015; c["q"] -= q; c["cost"] = avg * c["q"]; c["part"] = True; X.log(f"DKv2 a third off at {avg*1.015:,.0f}")
                    if t > pd.Timestamp(c["first_fill"]) and b.high >= avg * 1.03: why, px = "target +3%", avg * 1.03
                    elif age_h >= 24 * 7: why, px = "7 days", b.close * (1 - SLIP) * (1 - TAKER)
                if why:
                    pnl = c["pnl"] + c["q"] * (px - avg); pct = 100 * pnl / USD
                    ledger(dict(placed=c["placed"], closed=str(t), level=round(c["lvl"]), fills=sum(c["fill"]), avg=round(avg), exit=round(px), why=why, pnl_usd=round(pnl, 2), pct_budget=round(pct, 3), ctx=c["ctx"]))
                    X.log(f"DKv2 CLOSED {why}: {pct:+.3f}% of the ladder (${pnl:+.2f})"); st["camp"] = None; st["busy_until"] = str(max(t, pd.Timestamp(c["placed"]) + pd.Timedelta("1D")))
            elif age_h >= 48:
                X.log("DKv2 ladder expired unfilled"); st["camp"] = None; st["busy_until"] = str(pd.Timestamp(c["placed"]) + pd.Timedelta("1D"))
        if st["camp"] is None and t.minute == 0 and t.hour in (7, 13) and (st["busy_until"] is None or t > pd.Timestamp(st["busy_until"])):
            hist = rx[rx.index < t]
            if len(hist) < 96: continue
            lvl = float(hist.low.iloc[-96:].min()) * 0.997; lastc = float(hist.close.iloc[-1])
            atrp, up, deep = context(D, t.normalize())
            if lastc > lvl * 1.03 or not (up or deep): X.log(f"DKv2 {t:%H:%M}: no ladder (close {lastc:,.0f} vs level {lvl:,.0f}; uptrend {up}, deep flush {deep})"); continue
            step = float(np.clip(0.3 * atrp, 0.006, 0.03)); rungs = [lvl * (1 - step * r) for r in range(4)]
            st["camp"] = dict(placed=str(t), lvl=lvl, rungs=rungs, stop=rungs[-1] * (1 - step), fill=[False] * 4, q=0.0, cost=0.0, pnl=0.0, part=False, ctx="uptrend" if up else "deep flush")
            X.log(f"DKv2 LADDER at {t:%Y-%m-%d %H:%M}: {', '.join(f'{r:,.0f}' for r in rungs)}; stop {rungs[-1]*(1-step):,.0f} ({st['camp']['ctx']})")
            for i, r in enumerate(rungs):                                   # the start bar itself can fill (as in the backtest)
                if b.low <= r: st["camp"]["fill"][i] = True; q = USD * W[i] / r; st["camp"]["q"] += q; st["camp"]["cost"] += q * r; st["camp"]["first_fill"] = str(t)
    st["last_bar"] = str(rx.index[-1]); json.dump(st, open(f, "w"), indent=1, default=str)

if __name__ == "__main__":
    run()
