"""
WILLIAMS VOLATILITY BREAKOUT ENGINE for the IG runner — DEMO (doc 228 part 2; DK 11 Nov "Continue work on these").
Larry Williams' day-trade breakout, as tested on 5-min bars at IG costs (US Tech 100: k 0.5 +28.8 pts/trade, 55% win, both halves +, 10/14 months;
USD/JPY: every k positive, both halves +):
  - at the cash-session open: BUY STOP at open + k x the previous session's range and SELL STOP at open - k x that range (k = 0.5, Williams' own);
  - each order carries its stop at the other side of the bracket (stop distance 2k x range); one-cancels-the-other: when one fills, the other is cancelled;
  - flat at the cash close (market), every day. One trade per market per session.
Sessions: US Tech 100 09:30-16:00 New York; USD/JPY 08:00-16:30 London. Bars: the range engine's IG 5-min bars (no extra history calls).
Sizing: 2% of book equity at risk (ig_book.BookEquity), IG minimum stake floor, 5x exposure cap, -4% book day stop.
Demo only: refuses to start on live. State: <OUT>/wvb_state.json; trades: <OUT>/wvb_trades.csv.
"""
import os, json, csv, datetime as dt, traceback
import numpy as np, pandas as pd
from ig_mode import OUT, LIVE

STATE = f"{OUT}/wvb_state.json"; TRADES = f"{OUT}/wvb_trades.csv"
SESS = {"NQ": ("America/New_York", 570, 960), "USDJPY": ("Europe/London", 480, 990), "US500": ("America/New_York", 570, 960)}
K, RISK = 0.5, 0.02

def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), "[wvb]", *a, flush=True)

class WVBEngine:
    def __init__(self, ig, ccy, dry, range_engine, book, notional_fn, markets):
        if LIVE: raise SystemExit("Williams breakout engine is demo-only until DK decides (doc 228)")
        self.ig, self.ccy, self.dry, self.eng, self.beq, self.notional_fn = ig, ccy, dry, range_engine, book, notional_fn
        self.markets = [m for m in markets if m in SESS and m in range_engine.mkt and m not in range_engine.disabled]
        self.st = json.load(open(STATE)) if os.path.exists(STATE) else {}
        for m in self.markets: self.st.setdefault(m, {"day": None, "orders": {}, "pos": None, "done": False})
        log("markets:", self.markets or "none (needs the range engine's bars)")

    def session(self, name, ts):
        tz, o, c = SESS[name]; lt = pd.Timestamp(ts).tz_convert(tz); mm = lt.hour * 60 + lt.minute
        return str(lt.date()), mm - o, c - o, lt.dayofweek

    def prev_range(self, name, day):
        tz, o, c = SESS[name]; b = self.eng.bars5[name]; lt = b.index.tz_convert(tz); mm = lt.hour * 60 + lt.minute
        s = b[(mm >= o) & (mm < c)]; dd = pd.Series(s.index.tz_convert(tz).date, index=s.index).astype(str)
        g = s.groupby(dd.values).agg(h=("high", "max"), l=("low", "min"), n=("high", "size")); g = g[(g.index < day) & (g.n >= 0.6 * g.n.max())]
        return float(g.h.iloc[-1] - g.l.iloc[-1]) if len(g) else None

    def on_bar5(self, epic, c):
        name = self.eng.epic2name.get(epic)
        if name not in self.markets: return
        try: self.step(name, c)
        except Exception: log(name, "step error:", traceback.format_exc())

    def step(self, name, c):
        st = self.st[name]; ts = pd.Timestamp(c["ts"]); day, m, end, dow = self.session(name, ts)
        if dow >= 5: return
        if st["day"] != day: st.update(day=day, orders={}, pos=None, done=False, open=None)
        if m < 0: return
        if m + 5 >= end:                                           # the bar that just closed ends the session: flat
            self.flatten(name, "cash_close"); return
        if st["done"]: return
        if st.get("open") is None and m == 0:                      # first bar of the session: its open is the session open
            st["open"] = float(c["open"]); self.place(name, ts)
        elif st.get("open") is None: return                        # joined mid-session without the open bar: no trade today
        self.sync(name, c)
        self.save()

    def place(self, name, ts):
        st = self.st[name]; mk = self.eng.mkt[name]; R = self.prev_range(name, st["day"])
        if not R or R <= 0: log(name, "no previous session range — no bracket today"); st["done"] = True; return
        if self.beq and not self.beq.day_ok(): log(name, "book day stop — no bracket today"); st["done"] = True; return
        o = st["open"]; a = K * R; up, dn, dist = o + a, o - a, 2 * a
        dist = max(dist, mk.get("minstop", 0))
        size = max(mk["min"], round(self.beq.eq * RISK * self.beq.k / dist, 2)) if self.beq else mk["min"]
        if self.beq: size = self.beq.cap(size, o, self.notional_fn() if self.notional_fn else 0.0, mk["min"])
        if size <= 0: log(name, "5x exposure cap — no bracket"); st["done"] = True; return
        st.update(up=up, dn=dn, dist=dist, size=size, R=R)
        log(name, f"session open {o:.1f}, previous range {R:.1f}: BUY STOP {up:.1f} / SELL STOP {dn:.1f}, stop distance {dist:.1f}, {size}/pt")
        for side, lvl in (("BUY", up), ("SELL", dn)):
            if self.dry: st["orders"][side] = {"deal_id": "dry", "level": lvl}; continue
            try:
                r = self.ig.create_working_order(currency_code=self.ccy, direction=side, epic=mk["epic"], expiry=mk["expiry"], guaranteed_stop=False,
                                                 level=round(lvl, 1), size=size, time_in_force="GOOD_TILL_CANCELLED", order_type="STOP",
                                                 stop_distance=round(dist, 1), force_open=True)
                if r.get("dealStatus") != "ACCEPTED": log(name, side, "STOP order rejected:", r.get("reason")); continue
                st["orders"][side] = {"deal_id": r.get("dealId"), "ref": r.get("dealReference"), "level": lvl}
            except Exception as ex: log(name, side, "working order:", ex)

    def sync(self, name, c):
        st = self.st[name]
        if st["pos"] is None and st["orders"]:
            if self.dry:                                            # play the stop orders against the bar that just closed (both = worst case: long, stopped)
                hu, hd = c["high"] >= st["up"], c["low"] <= st["dn"]
                if hu or hd:
                    s = 1 if hu else -1; e = st["up"] if s == 1 else st["dn"]
                    st["pos"] = {"deal_id": "dry", "side": s, "px": e, "stop": e - s * st["dist"], "sz": st["size"], "bar": str(c["ts"])}; st["orders"] = {}
                    log(name, f"dry FILL {'BUY' if s == 1 else 'SELL'} at {e:.1f}")
                    if hu and hd: self.book(name, st["pos"]["stop"], "both_in_one_bar(dry)"); st["done"] = True; return
            else:
                try:
                    opn = self.ig.fetch_open_positions()["positions"]; wo = {x["workingOrderData"]["dealId"] for x in self.ig.fetch_working_orders().get("workingOrders", [])}
                except Exception as ex: log(name, "sync:", ex); return
                byref = {x["position"].get("dealReference"): x["position"] for x in opn}
                for side, o in list(st["orders"].items()):
                    if o["deal_id"] in wo: continue
                    p = byref.get(o.get("ref"))
                    if p:
                        s = 1 if side == "BUY" else -1
                        st["pos"] = {"deal_id": p["dealId"], "side": s, "px": float(p["level"]), "stop": float(p.get("stopLevel") or 0), "sz": float(p["size"]), "bar": str(c["ts"])}
                        log(name, f"FILLED {side} {p['size']}/pt at {p['level']}")
                        for other, oo in list(st["orders"].items()):
                            if other != side:
                                try: self.ig.delete_working_order(oo["deal_id"]); log(name, "cancelled the", other, "stop order")
                                except Exception as ex: log(name, "cancel", other, ex)
                        st["orders"] = {}; break
        if st["pos"] is not None:
            p = st["pos"]
            if self.dry:
                if (p["side"] == 1 and c["low"] <= p["stop"]) or (p["side"] == -1 and c["high"] >= p["stop"]): self.book(name, p["stop"], "stop(dry)"); st["done"] = True
            else:
                try: ids = {x["position"]["dealId"] for x in self.ig.fetch_open_positions()["positions"]}
                except Exception as ex: log(name, "sync:", ex); return
                if p["deal_id"] not in ids:
                    lv = self.eng.exit_levels(name, [dict(deal_id=p["deal_id"], px=p["px"], sz=p["sz"])]); self.book(name, lv.get(p["deal_id"], np.nan), "ig_stop"); st["done"] = True

    def flatten(self, name, how):
        st = self.st[name]
        for side, o in list(st["orders"].items()):
            if not self.dry and o.get("deal_id") not in (None, "dry"):
                try: self.ig.delete_working_order(o["deal_id"])
                except Exception as ex: log(name, "cancel", side, ex)
        st["orders"] = {}
        p = st["pos"]
        if p:
            px = np.nan
            if self.dry: px = float(self.eng.bars5[name].close.iloc[-1])
            else:
                try:
                    r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] == 1 else "BUY", epic=None, expiry=None, level=None,
                                                    order_type="MARKET", quote_id=None, size=p["sz"]); px = float(r.get("level") or np.nan)
                except Exception as ex: log(name, "close:", ex)
            self.book(name, px, how)
        st["done"] = True; self.save()

    def book(self, name, px, how):
        st = self.st[name]; p = st["pos"]; st["pos"] = None
        pts = p["side"] * (px - p["px"]) if np.isfinite(px) else np.nan; gbp = pts * p["sz"] if np.isfinite(pts) else np.nan
        hdr = not os.path.exists(TRADES)
        with open(TRADES, "a", newline="") as f:
            w = csv.writer(f)
            if hdr: w.writerow(["market", "side", "opened_bar", "closed", "entry", "exit", "size", "pts", "gbp", "how"])
            w.writerow([name, p["side"], p["bar"], utcnow().isoformat(timespec="seconds"), p["px"], px, p["sz"], f"{pts:.1f}", f"{gbp:.2f}", how])
        if self.beq and np.isfinite(gbp): self.beq.add(gbp, "wvb")
        log(name, f"CLOSED ({how}) {pts:+.1f} pts, {gbp:+.2f} {self.ccy}"); self.save()

    def end_of_job(self):
        """Positions and the bracket orders carry over to the next job of the same session (IG holds them); the cash close flattens."""
        self.save()

    def save(self): json.dump(self.st, open(STATE, "w"), indent=1, default=str)
