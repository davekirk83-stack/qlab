"""
EMA CONTRACTION ENGINE for the IG runner — DEMO ONLY (doc 251/252; DK 22 Nov 09:42 "Yes do all of those on your list").
Rule (src/research/ema_contraction_improve.py, 1h, Nov 2025-Nov 2026, IG costs): EMAs 20/50/100/200 on 1-hour bars squeezed together
(their spread / ATR14 in the bottom 20% of the last 500 hours) within the last 6 hours; the hour closes OUT of the bunch (above the
highest EMA, or below the lowest) in the direction of the 200-EMA's 10-hour slope -> market order, stop 1.5 ATR, limit 3 ATR (IG holds
both), time exit after 48 hours. Backtest: US 500 +0.23 ATR/trade, Wall Street +0.35, Germany 40 +0.34, NQ +0.25 (both halves positive
except NQ's second half flat); FTSE and gold excluded (negative / flat).
Bars: the range engine's IG 5-min bars (Wall Street / Germany 40 load as IG_RANGE_DATA_ONLY — bars, no ladder).
Sizing: 1% of book equity at risk per trade (ig_book.BookEquity), IG minimum stake, 5x exposure cap, book day stop. One position per market.
Refuses to start on live. State <OUT>/emac_state.json, trades <OUT>/emac_trades.csv.
"""
import os, json, csv, datetime as dt, traceback
import numpy as np, pandas as pd
from ig_mode import OUT, LIVE
STATE = f"{OUT}/emac_state.json"; TRADES = f"{OUT}/emac_trades.csv"
RISK, STOP_ATR, LIM_ATR, HOLD_H = 0.01, 1.5, 3.0, 48
def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), "[emac]", *a, flush=True)

def signal(b1h):
    """b1h: completed 1-hour bars (open/high/low/close). Returns (side, atr, last_close) for the LAST bar, side 0 = none."""
    if len(b1h) < 260: return 0, np.nan, np.nan
    c = b1h.close; E = pd.concat([c.ewm(span=s, adjust=False).mean() for s in (20, 50, 100, 200)], axis=1)
    tr = np.maximum(b1h.high - b1h.low, np.maximum((b1h.high - c.shift()).abs(), (b1h.low - c.shift()).abs())); A = tr.rolling(14).mean()
    spread = (E.max(axis=1) - E.min(axis=1)) / A
    tight = spread < spread.rolling(500, min_periods=200).quantile(0.2); was = tight.rolling(6).max().fillna(0).astype(bool)
    slope = E.iloc[:, 3].diff(10); hi, lo = E.max(axis=1), E.min(axis=1)
    i = len(c) - 1
    up = was.iloc[i] and c.iloc[i] > hi.iloc[i] and c.iloc[i-1] <= hi.iloc[i-1] and slope.iloc[i] > 0
    dn = was.iloc[i] and c.iloc[i] < lo.iloc[i] and c.iloc[i-1] >= lo.iloc[i-1] and slope.iloc[i] < 0
    return (1 if up else -1 if dn else 0), float(A.iloc[i]), float(c.iloc[i])

class EMACEngine:
    def __init__(self, ig, ccy, dry, range_engine, book, notional_fn, markets):
        if LIVE: raise SystemExit("EMA contraction engine is DEMO ONLY (doc 252)")
        self.ig, self.ccy, self.dry, self.eng, self.beq, self.notional_fn = ig, ccy, dry, range_engine, book, notional_fn
        self.markets = [m for m in markets if m in range_engine.mkt and m not in range_engine.disabled]
        self.st = json.load(open(STATE)) if os.path.exists(STATE) else {}
        for m in self.markets: self.st.setdefault(m, {"pos": None, "last_hour": None})
        log("markets:", self.markets or "none (needs the range engine's bars)")

    def on_bar5(self, epic, c):
        name = self.eng.epic2name.get(epic)
        if name not in self.markets: return
        try: self.step(name, c)
        except Exception: log(name, "step error:", traceback.format_exc())

    def step(self, name, c):
        st = self.st[name]; ts = pd.Timestamp(c["ts"])
        self.sync(name, c)
        if ts.minute != 55: return                                  # the 5-min bar that completes the hour
        hour = str(ts.floor("1h"))
        if st.get("last_hour") == hour: return
        st["last_hour"] = hour
        b = self.eng.bars5[name]; b = b[b.index < ts.floor("1h") + pd.Timedelta(hours=1)]
        b1h = b.resample("1h").agg(dict(open="first", high="max", low="min", close="last")).dropna()
        p = st["pos"]
        if p and (ts - pd.Timestamp(p["opened"])) >= pd.Timedelta(hours=HOLD_H): self.close(name, "time_48h"); return
        if p: self.save(); return
        side, atr, px = signal(b1h)
        log(name, f"hour {ts.floor('1h'):%d %b %H:%M} close {px:.1f} atr {atr:.1f} signal {side:+d}")
        if side == 0 or not np.isfinite(atr) or atr <= 0: self.save(); return
        if self.beq and not self.beq.day_ok(): log(name, "book day stop — no entry"); self.save(); return
        mk = self.eng.mkt[name]; dist = max(STOP_ATR * atr, mk.get("minstop", 0)); lim = LIM_ATR * atr
        size = max(mk["min"], round(self.beq.eq * RISK * self.beq.k / dist, 2)) if self.beq else mk["min"]
        if self.beq: size = self.beq.cap(size, px, self.notional_fn() if self.notional_fn else 0.0, mk["min"], floor=0.0)
        if size <= 0: log(name, "5x exposure cap — no entry"); self.save(); return
        if self.dry:
            st["pos"] = dict(deal_id="dry", side=side, px=px, stop=px - side * dist, lim=px + side * lim, sz=size, opened=str(ts))
            log(name, f"dry ENTRY {'BUY' if side > 0 else 'SELL'} {size}/pt at {px:.1f}, stop {dist:.1f}, limit {lim:.1f}"); self.save(); return
        try:
            r = self.ig.create_open_position(currency_code=self.ccy, direction="BUY" if side > 0 else "SELL", epic=mk["epic"], expiry=mk["expiry"],
                                             force_open=True, guaranteed_stop=False, level=None, limit_distance=round(lim, 1), limit_level=None,
                                             order_type="MARKET", quote_id=None, size=size, stop_distance=round(dist, 1), stop_level=None,
                                             trailing_stop=False, trailing_stop_increment=None)
        except Exception as ex: log(name, "order:", ex); self.save(); return
        if r.get("dealStatus") == "ACCEPTED":
            st["pos"] = dict(deal_id=r.get("dealId"), side=side, px=float(r.get("level") or px), stop=None, lim=None, sz=size, opened=str(ts))
            log(name, f"ENTRY {'BUY' if side > 0 else 'SELL'} {size}/pt at {st['pos']['px']}, stop {dist:.1f}, limit {lim:.1f}")
        else: log(name, "order rejected:", r.get("reason"))
        self.save()

    def sync(self, name, c):
        p = self.st[name]["pos"]
        if not p: return
        if self.dry:
            s = p["side"]
            if (s > 0 and c["low"] <= p["stop"]) or (s < 0 and c["high"] >= p["stop"]): self.book(name, p["stop"], "stop(dry)")
            elif (s > 0 and c["high"] >= p["lim"]) or (s < 0 and c["low"] <= p["lim"]): self.book(name, p["lim"], "limit(dry)")
            return
        try: ids = {x["position"]["dealId"] for x in self.ig.fetch_open_positions()["positions"]}
        except Exception as ex: log(name, "sync:", ex); return
        if p["deal_id"] not in ids:
            lv = self.eng.exit_levels(name, [dict(deal_id=p["deal_id"], px=p["px"], sz=p["sz"])])
            self.book(name, lv.get(p["deal_id"], float(c["close"])), "ig_stop_or_limit")

    def close(self, name, how):
        p = self.st[name]["pos"]; px = float(self.eng.bars5[name].close.iloc[-1])
        if not self.dry:
            try:
                r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] > 0 else "BUY", epic=None, expiry=None, level=None,
                                                order_type="MARKET", quote_id=None, size=p["sz"]); px = float(r.get("level") or px)
            except Exception as ex: log(name, "close:", ex); return
        self.book(name, px, how)

    def book(self, name, px, how):
        st = self.st[name]; p = st["pos"]; st["pos"] = None
        pts = p["side"] * (px - p["px"]); gbp = pts * p["sz"]
        hdr = not os.path.exists(TRADES)
        with open(TRADES, "a", newline="") as f:
            w = csv.writer(f)
            if hdr: w.writerow(["market", "side", "opened", "closed", "entry", "exit", "size", "pts", "gbp", "how"])
            w.writerow([name, p["side"], p["opened"], utcnow().isoformat(timespec="seconds"), p["px"], px, p["sz"], f"{pts:.1f}", f"{gbp:.2f}", how])
        if self.beq and np.isfinite(gbp): self.beq.add(gbp, "emac")
        log(name, f"CLOSED ({how}) {pts:+.1f} pts, {gbp:+.2f} {self.ccy}"); self.save()

    def end_of_job(self): self.save()          # positions carry over between jobs (IG holds the stop and limit)
    def save(self): json.dump(self.st, open(STATE, "w"), indent=1, default=str)
