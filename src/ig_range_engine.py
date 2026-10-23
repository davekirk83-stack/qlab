"""
RANGE ENGINE for the IG demo runner — Range v3 (doc 91) on IG index spread bets, DEMO ONLY (CAP-021 as amended 20 Oct 2026).
Registered as paper book 8 "Range v3-IDX" (doc 116): Wall Street and Germany 40 all hours, US Tech 100 in NY hours (13-20 UTC),
15-minute bars, the paperbook6 ladder (4 rungs below the lower Keltner band / above the upper), every lot exits at the mid EMA,
break exit beyond band + 1.5 ATR, 48-bar cap, 6-hour cooldown, two-sided.

How the ladder is placed on IG (per instrument, per side, at each 15-minute bar close):
  - a rung the bar has not reached: a LIMIT working order at the rung price (BUY below market / SELL above), size per rung;
  - a rung the close is already beyond: a MARKET order now (the paper book's "touched -> filled at rung + 0.05 ATR");
  - every lot carries limit_level = mid EMA (the target) and stop_level = the break level (band +/- 1.5 ATR), both re-set each bar,
    so the two price-based exits also work while no job is running (the demo jobs cover 13:10-21:00 UTC only);
  - regime switch and 48-bar cap close the side's lots at MARKET during a job; working orders are cancelled at job end.
Governors are shared with Ignition through the runner's state (8 trades/day, -200 £/day). State: runs/ig_demo/range_state.json.
"""
import os, json, time, datetime as dt, traceback
import numpy as np, pandas as pd
import paperbook6 as P6

ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); OUT = "runs/ig_demo"
STATE = f"{OUT}/range_state.json"; TRADES = f"{OUT}/range_trades.csv"
RANGE_SIZE = float(os.environ.get("IG_RANGE_SIZE", "1.0"))     # full-ladder £/pt; each rung = max(min size, frac x this)
INSTR = {  # name: candidate epics, search text, 5-min cache, UTC hours for NEW episodes (None = all hours)
    "NQ":     dict(epics=["IX.D.NASDAQ.CASH.IP"], search="US Tech 100", cache=f"{ROOT}/data_nq_cache/nq_5m.csv", hours=(13, 20)),
    "WALLST": dict(epics=["IX.D.DOW.DAILY.IP", "IX.D.DOW.CASH.IP"], search="Wall Street", cache=f"{ROOT}/data_ig_cache/USA30IDXUSD_5m.csv", hours=None),
    "DAX":    dict(epics=["IX.D.DAX.DAILY.IP", "IX.D.DAX.CASH.IP"], search="Germany 40", cache=f"{ROOT}/data_ig_cache/DEUIDXEUR_5m.csv", hours=None),
}
MAXT, LOSSCAP = 8, 200.0


def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), "[range]", *a, flush=True)


def retry(fn, what, tries=4, wait=15):
    """IG throttles bursts of non-trading requests (ApiExceededException); back off and retry."""
    for k in range(tries):
        try: return fn()
        except Exception as ex:
            name = type(ex).__name__
            if "Exceeded" not in name or k == tries - 1: raise
            log(what, "throttled — waiting", wait, "s"); time.sleep(wait)


def to15(b5):
    b = pd.DataFrame({"open": b5.open.resample("15min").first(), "high": b5.high.resample("15min").max(),
                      "low": b5.low.resample("15min").min(), "close": b5.close.resample("15min").last()}).dropna()
    return b


class RangeEngine:
    def __init__(self, ig, ccy, dry, gov, rest_history, primary=None):
        """ig: IGService on the spread-bet demo; gov: the runner's daily state dict (ntr, dpl); rest_history(epic, res, n) -> 5-min DataFrame;
        primary: (epic, DataFrame) of 5-min bars the runner already holds, so that epic needs no second history call."""
        self.ig, self.ccy, self.dry, self.gov, self.rest, self.primary = ig, ccy, dry, gov, rest_history, primary or (None, None)
        self.st = json.load(open(STATE)) if os.path.exists(STATE) else {}
        self.mkt, self.bars5, self.bars15 = {}, {}, {}
        for name, m in INSTR.items():
            epic, info = self.resolve(m)
            if not epic: log(name, "no epic found — instrument skipped"); continue
            self.mkt[name] = info
            self.st.setdefault(name, {"since": None, "pos": {"L": None, "S": None}, "cool": {}, "orders": {}})
            self.seed(name, epic, m)
        self.epic2name = {v["epic"]: k for k, v in self.mkt.items()}
        log("instruments:", {k: f"{v['epic']} min {v['min']} {self.ccy}/pt" for k, v in self.mkt.items()})

    # ------------------------------------------------------------------ setup
    def resolve(self, m):
        def search():
            out = []
            try:
                res = retry(lambda: self.ig.search_markets(m["search"]), "search"); ms = res.get("markets", []) if isinstance(res, dict) else []
                log("search", m["search"], "->", [(x.get("epic"), x.get("instrumentName")) for x in ms][:8])
                for r in ms:
                    e = r.get("epic", "")
                    if e.startswith("IX.") and (e.endswith(".DAILY.IP") or e.endswith(".CASH.IP")): out.append(e)
            except Exception as ex: log("search", m["search"], f"{type(ex).__name__}: {ex!r}"[:200])
            return out
        cands = list(m["epics"]); searched = False
        while cands:
            e = cands.pop(0); time.sleep(1.5)
            try:
                mk = retry(lambda: self.ig.fetch_market_by_epic(e), f"market {e}"); ins, rules = mk["instrument"], mk["dealingRules"]
                if ins.get("type") not in (None, "INDICES"): continue
                cc = [c["code"] for c in ins.get("currencies", [])]
                if cc and self.ccy not in cc: continue
                return e, dict(epic=e, name=ins["name"], expiry=ins["expiry"], min=float(rules["minDealSize"]["value"]),
                               minstop=float(rules.get("minNormalStopOrLimitDistance", {}).get("value", 0) or 0), status=mk["snapshot"]["marketStatus"])
            except Exception as ex: log("epic", e, "->", f"{type(ex).__name__}: {ex!r}"[:200])
            if not cands and not searched: searched = True; cands = [x for x in search() if x not in m["epics"]]
        return None, None

    def seed(self, name, epic, m):
        """15-min history: the 5-min cache (Dukascopy, offset to IG's level at the join) plus the last 300 IG 5-min bars by REST."""
        try: c = pd.read_csv(m["cache"], index_col=0, parse_dates=True); c.index = pd.to_datetime(c.index, utc=True); c = c[["open", "high", "low", "close"]]
        except Exception as ex: log(name, "cache", ex); c = pd.DataFrame()
        try:
            if epic == self.primary[0] and self.primary[1] is not None and len(self.primary[1]): r = self.primary[1][["open", "high", "low", "close"]].copy(); log(f"{name}: using the runner's own {len(r)} IG bars")
            else: time.sleep(2); r = retry(lambda: self.rest(epic, "5Min", 300), f"{name} history")[["open", "high", "low", "close"]]
        except Exception as ex: log(name, "rest history", f"{type(ex).__name__}: {ex!r}"[:200]); r = pd.DataFrame()
        if len(c) and len(r):
            j = c.index.searchsorted(r.index[0]); k = min(max(j - 1, 0), len(c) - 1)
            off = float(r.close.iloc[0] - c.close.iloc[k]); c = c + off; c = c[c.index < r.index[0]]
            log(f"{name}: cache {len(c)} bars offset {off:+.1f} to IG level, REST {len(r)} bars to {r.index[-1]}")
        b5 = pd.concat([c, r]).sort_index(); b5 = b5[~b5.index.duplicated(keep="last")]
        # today's own 5-min bars logged by an earlier job
        f = f"{OUT}/bars_{name}_{utcnow():%Y-%m-%d}.csv"
        if os.path.exists(f):
            t = pd.read_csv(f, header=None, names="ts,open,high,low,close,vol,delta,spread".split(",")); t.index = pd.to_datetime(t.ts, utc=True)
            b5 = pd.concat([b5, t[["open", "high", "low", "close"]]]); b5 = b5[~b5.index.duplicated(keep="last")].sort_index()
        self.bars5[name] = b5.tail(4000); self.bars15[name] = to15(self.bars5[name]).tail(1500)
        # containment median from the full cache (the registered switch threshold, doc 91)
        try:
            full = to15(c if len(c) else b5); ema, lo, hi, a, _ = P6.indicators(full)
            C = full.close.values; inside = ((C <= hi) & (C >= lo)).astype(float); cont = pd.Series(inside).rolling(50).mean().dropna()
            P6._MED[name] = {"median": float(cont.median())}; log(f"{name}: containment median {cont.median():.3f} over {len(full)} 15-min bars")
        except Exception as ex: log(name, "median", ex)

    # ------------------------------------------------------------------ bars
    def on_bar5(self, epic, c):
        name = self.epic2name.get(epic)
        if not name: return
        row = pd.DataFrame([dict(open=c["open"], high=c["high"], low=c["low"], close=c["close"])], index=[pd.Timestamp(c["ts"])])
        self.bars5[name] = pd.concat([self.bars5[name], row]); self.bars5[name] = self.bars5[name][~self.bars5[name].index.duplicated(keep="last")].tail(4000)
        with open(f"{OUT}/bars_{name}_{c['ts']:%Y-%m-%d}.csv", "a") as f:
            f.write(f"{c['ts'].isoformat()},{c['open']:.2f},{c['high']:.2f},{c['low']:.2f},{c['close']:.2f},{c['vol']},{c['delta']},{c['spread_sum']/max(c['vol'],1):.2f}\n")
        if c["ts"].minute % 15 == 10:
            self.bars15[name] = to15(self.bars5[name]).tail(1500)
            try: self.step(name)
            except Exception: log(name, "step error:", traceback.format_exc())

    # ------------------------------------------------------------------ the book, one 15-min bar
    def step(self, name):
        d = self.bars15[name]; st = self.st[name]; mk = self.mkt[name]; hours = INSTR[name]["hours"]
        if len(d) < 300: log(name, "not enough bars", len(d)); return
        ema, lo_b, hi_b, a, allow = P6.indicators(d, name); i = len(d) - 1; ts = d.index[i]
        C, H, L = d.close.values, d.high.values, d.low.values
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        if st["since"] is None:
            st["since"] = str(ts); self.save(); log(f"{name}: first bar {ts:%H:%M} — watermark adopted, no trade (paperbook6 rule)"); return
        if not np.isfinite(a[i]) or a[i] <= 0: return
        self.sync(name)
        log(f"{name} {ts:%H:%M} c {C[i]:.1f} ema {ema[i]:.1f} band {lo_b[i]:.1f}-{hi_b[i]:.1f} atr {a[i]:.1f} regime {'ON' if ok else 'off'} "
            f"L {len((st['pos']['L'] or {}).get('lots', []))} S {len((st['pos']['S'] or {}).get('lots', []))} orders {len(st['orders'])}")
        for side in ("L", "S"):
            p = st["pos"].get(side)
            if not p: continue
            s = 1 if side == "L" else -1
            broke = (C[i] < lo_b[i] - 1.5*a[i]) or (C[i] > hi_b[i] + 1.5*a[i]); age = int((ts - pd.Timestamp(p["open"])) / pd.Timedelta(minutes=15))
            if broke or age >= P6.CAP_BARS or not ok:
                how = "break" if broke else ("cap" if age >= P6.CAP_BARS else "regime")
                self.close_side(name, side, how); continue
            tgt = round(float(ema[i]), 1); brk = round(float(lo_b[i] - 1.5*a[i]) if side == "L" else float(hi_b[i] + 1.5*a[i]), 1)
            for lot in p["lots"]:
                if abs(lot.get("tgt", 0) - tgt) >= 0.5 or abs(lot.get("brk", 0) - brk) >= 0.5:
                    if not self.dry:
                        try:
                            r = self.ig.update_open_position(limit_level=tgt, stop_level=brk, deal_id=lot["deal_id"])
                            if r.get("dealStatus", "ACCEPTED") != "ACCEPTED": log(name, "update lot:", r.get("reason")); continue
                        except Exception as ex: log(name, "update lot:", ex); continue
                    lot["tgt"], lot["brk"] = tgt, brk
        # entries
        for side in ("L", "S"):
            if hours and not (hours[0] <= ts.hour < hours[1]): continue
            if not ok or (P6.LONGS_OFF and side == "L"):
                self.cancel_orders(name, side); continue
            ct = st["cool"].get(side)
            if ct and ts < pd.Timestamp(ct) + pd.Timedelta(hours=P6.COOLDOWN_H): continue
            p = st["pos"].get(side)
            if p is None and (self.gov["ntr"] >= MAXT or self.gov["dpl"] <= -LOSSCAP): continue
            tried = set(p["tried"]) if p else set(); s = 1 if side == "L" else -1
            for k, (frac, off) in enumerate(P6.BID):
                if k in tried: continue
                price = round(float(lo_b[i] + off*a[i]) if side == "L" else float(hi_b[i] - off*a[i]), 1)
                size = max(mk["min"], round(frac*RANGE_SIZE, 2)); key = f"{side}{k}"
                beyond = (C[i] <= price) if side == "L" else (C[i] >= price)
                if beyond: self.cancel_orders(name, side, k); self.fill_market(name, side, k, size, price, ts)
                else: self.place_limit(name, side, k, size, price, key)
        self.save()

    # ------------------------------------------------------------------ orders and fills
    def ref(self, name, side, k): return f"RG{name}{side}{k}{utcnow():%d%H%M}"[:30]

    def place_limit(self, name, side, k, size, price, key):
        st = self.st[name]; mk = self.mkt[name]; o = st["orders"].get(key)
        if o and abs(o["price"] - price) < 1.0: return
        if o: self.cancel_orders(name, side, k)
        if self.dry: log(f"{name} dry: would place {'BUY' if side=='L' else 'SELL'} LIMIT rung {k} {size}/pt at {price}"); st["orders"][key] = {"deal_id": None, "ref": "dry", "price": price, "size": size}; return
        try:
            r = self.ig.create_working_order(currency_code=self.ccy, direction="BUY" if side == "L" else "SELL", epic=mk["epic"], expiry=mk["expiry"], guaranteed_stop=False,
                                             level=price, size=size, time_in_force="GOOD_TILL_CANCELLED", order_type="LIMIT", deal_reference=self.ref(name, side, k), force_open=True)
            if r.get("dealStatus") != "ACCEPTED": log(name, "working order rejected:", r.get("reason")); return
            st["orders"][key] = {"deal_id": r.get("dealId"), "ref": r.get("dealReference"), "price": price, "size": size}
            log(f"{name} LIMIT {'BUY' if side=='L' else 'SELL'} rung {k} {size}/pt at {price} placed ({r.get('dealId')})")
        except Exception as ex: log(name, "working order:", ex)

    def cancel_orders(self, name, side, k=None):
        st = self.st[name]
        for key in [x for x in list(st["orders"]) if x[0] == side and (k is None or x == f"{side}{k}")]:
            o = st["orders"].pop(key)
            if self.dry or not o.get("deal_id"): continue
            try: self.ig.delete_working_order(o["deal_id"])
            except Exception as ex: log(name, "cancel", key, ex)

    def fill_market(self, name, side, k, size, price, ts):
        mk = self.mkt[name]; st = self.st[name]
        if self.dry: log(f"{name} dry: would MARKET {'BUY' if side=='L' else 'SELL'} rung {k} {size}/pt (close beyond {price})"); self.add_lot(name, side, k, price, size, "dry", ts); return
        try:
            r = self.ig.create_open_position(currency_code=self.ccy, direction="BUY" if side == "L" else "SELL", epic=mk["epic"], expiry=mk["expiry"], force_open=True, guaranteed_stop=False,
                                             level=None, limit_distance=None, limit_level=None, order_type="MARKET", quote_id=None, size=size, stop_distance=None, stop_level=None,
                                             trailing_stop=False, trailing_stop_increment=None)
            if r.get("dealStatus") != "ACCEPTED": log(name, "market order rejected:", r.get("reason")); return
            self.add_lot(name, side, k, float(r["level"]), size, r["dealId"], ts); log(f"{name} FILLED MARKET {'BUY' if side=='L' else 'SELL'} rung {k} {size}/pt at {r['level']}")
        except Exception as ex: log(name, "market order:", ex)

    def add_lot(self, name, side, k, px, size, deal_id, ts):
        st = self.st[name]; p = st["pos"].get(side)
        if p is None:
            p = {"open": str(ts), "lots": [], "tried": [], "closed": []}; st["pos"][side] = p; self.gov["ntr"] += 1
        p["tried"].append(k); p["lots"].append({"deal_id": deal_id, "px": float(px), "sz": float(size), "k": k, "tgt": 0, "brk": 0})

    def sync(self, name):
        """Working orders that filled become lots; lots IG closed (limit at the mid, stop at the break) are booked."""
        if self.dry: return
        st = self.st[name]; mk = self.mkt[name]
        try:
            opn = [x for x in self.ig.fetch_open_positions()["positions"] if x["market"]["epic"] == mk["epic"]]
            wo = {x["workingOrderData"]["dealId"] for x in self.ig.fetch_working_orders().get("workingOrders", [])}
        except Exception as ex: log(name, "sync:", ex); return
        byref = {x["position"].get("dealReference"): x["position"] for x in opn}; ids = {x["position"]["dealId"] for x in opn}
        for key, o in list(st["orders"].items()):
            if o.get("deal_id") in wo: continue
            pos = byref.get(o.get("ref"))
            st["orders"].pop(key)
            if pos:
                side, k = key[0], int(key[1:]); ts = self.bars15[name].index[-1]
                self.add_lot(name, side, k, float(pos["level"]), float(pos["size"]), pos["dealId"], ts); log(f"{name} LIMIT rung {k} filled at {pos['level']}")
        now = utcnow()
        for side in ("L", "S"):
            p = st["pos"].get(side)
            if not p: continue
            gone = [l for l in p["lots"] if l["deal_id"] not in ids]
            if gone:
                lv = self.exit_levels(name, [l["deal_id"] for l in gone])
                for l in gone:
                    px = lv.get(l["deal_id"], np.nan); s = 1 if side == "L" else -1
                    pts = s*(px - l["px"]) if np.isfinite(px) else np.nan
                    p["closed"].append({"k": l["k"], "px": l["px"], "exit": px, "sz": l["sz"], "pts": pts, "how": "ig_limit_or_stop"})
                p["lots"] = [l for l in p["lots"] if l["deal_id"] in ids]
                if not p["lots"]: self.book(name, side, "sold_or_stop")

    def exit_levels(self, name, deal_ids):
        out = {}
        try:
            now = utcnow(); tx = self.ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=100)
            for t in (tx.get("transactions", tx) if isinstance(tx, dict) else tx):
                if str(t.get("transactionType", "")).upper() != "DEAL": continue
                ref = str(t.get("reference", ""))
                for d in deal_ids:
                    if d and d in ref:
                        try: out[d] = float(t.get("closeLevel"))
                        except Exception: pass
        except Exception as ex: log(name, "exit levels:", ex)
        return out

    def close_side(self, name, side, how):
        st = self.st[name]; mk = self.mkt[name]; p = st["pos"].get(side)
        self.cancel_orders(name, side)
        for l in list(p["lots"]):
            px = np.nan
            if self.dry: px = float(self.bars15[name].close.iloc[-1])
            else:
                try:
                    r = self.ig.close_open_position(deal_id=l["deal_id"], direction="SELL" if side == "L" else "BUY", epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=l["sz"])
                    px = float(r.get("level") or np.nan)
                except Exception as ex: log(name, "close lot:", ex); continue
            s = 1 if side == "L" else -1
            p["closed"].append({"k": l["k"], "px": l["px"], "exit": px, "sz": l["sz"], "pts": s*(px - l["px"]) if np.isfinite(px) else np.nan, "how": how}); p["lots"].remove(l)
        if not p["lots"]: self.book(name, side, how)

    def book(self, name, side, how):
        st = self.st[name]; p = st["pos"][side]; ts = self.bars15[name].index[-1]
        gbp = float(np.nansum([c["pts"]*c["sz"] for c in p["closed"]])); n = len(p["closed"])
        hdr = not os.path.exists(TRADES)
        with open(TRADES, "a") as f:
            if hdr: f.write("instr,side,opened,closed,lots,gbp,how,detail\n")
            f.write(f"{name},{side},{p['open']},{ts.isoformat()},{n},{gbp:.2f},{how},\"{json.dumps(p['closed'])}\"\n")
        self.gov["dpl"] += gbp; st["pos"][side] = None; st["cool"][side] = str(ts)
        log(f"{name} EPISODE {side} closed ({how}): {n} lots, {gbp:+.2f} {self.ccy} (day {self.gov['dpl']:+.1f})")

    def end_of_job(self):
        for name in self.mkt:
            for side in ("L", "S"): self.cancel_orders(name, side)
        self.save(); log("working orders cancelled; positions left to IG's limit (mid) and stop (break) until the next job")

    def save(self): json.dump(self.st, open(STATE, "w"), indent=1)
