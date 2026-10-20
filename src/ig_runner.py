"""
IG DEMO RUNNER — Ignition v1 (US-hours variant, doc 101) on IG's US Tech 100 daily-funded spread bet, DEMO ACCOUNT ONLY.
CAP-021 as amended 20 Oct 2026: demo-account credentials only; demo orders and price data permitted; no live account, key or money.
Refuses to start unless the account type returned by IG is a demo (acc_type 'demo' endpoint) — there is no code path to the live API.

What it does (one GitHub Actions job per half-session, see .github/workflows/ig-demo.yml):
  1. logs in to demo-api.ig.com, picks the SPREADBET demo account, loads 300 x 5-min bars of history (REST) for the indicators
  2. subscribes to the tick stream (CHART:<epic>:TICK) and builds 5-minute bars of the MID with tick-rule delta and mean spread —
     the same bar definition as data_nq_cache (paperbook7)
  3. at each bar close runs paperbook7.features on the bar history; entries only 13:30-20:00 UTC (US cash hours);
     opens a MARKET position of MIN size with an attached stop (45 pts) and limit (9 x ATR20)
  4. manages it per paperbook7.manage: breakeven at +15, then a 1-ATR trail — by moving the IG stop; cap 36 bars; flat at session end
  5. governors: max 8 trades/day, 3-bar cooloff, daily loss cap 200 pts
  6. logs every bar (runs/ig_demo/bars_<date>.csv) and every fill (runs/ig_demo/trades.csv) with the price the paper book would
     have assumed (next bar open) beside the price IG actually gave — that is the doc 93 fill-shape evidence
State between jobs: runs/ig_demo/state.json (committed by the job). An open position is recovered from IG at start.
"""
import os, sys, json, time, math, datetime as dt, traceback
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import paperbook7 as P7
from trading_ig import IGService, IGStreamService
from lightstreamer.client import Subscription, SubscriptionListener, LightstreamerClient

EPIC = os.environ.get("IG_EPIC", "IX.D.NASDAQ.IFD.IP")
OUT = "runs/ig_demo"; os.makedirs(OUT, exist_ok=True)
STATE = f"{OUT}/state.json"; TRADES = f"{OUT}/trades.csv"
US_OPEN, US_CLOSE = 13*60+30, 20*60
BAR = 5


def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), *a, flush=True)


class Runner:
    def __init__(self, end_utc, dry):
        self.end = end_utc; self.dry = dry
        u, p, k = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
        self.ig = IGService(u, p, k, acc_type="demo", return_dataframe=False)
        sess = self.ig.create_session(); self.session_acc = sess.get("currentAccountId"); self.ls_endpoint = sess.get("lightstreamerEndpoint")
        accs = self.ig.fetch_accounts()["accounts"]
        sb = [a for a in accs if a["accountType"] == "SPREADBET"]
        if not sb: raise RuntimeError("no SPREADBET demo account")
        self.acc = sb[0]["accountId"]
        if self.session_acc != self.acc:
            try:
                self.ig.switch_account(self.acc, True); log(f"switched session from {self.session_acc} to spread-bet account {self.acc}")
                self.session_acc = self.acc
            except Exception as e: log("switch_account:", e); self.session_acc = self.session_acc or self.acc
        mkt = self.ig.fetch_market_by_epic(EPIC)
        self.size = float(mkt["dealingRules"]["minDealSize"]["value"]); self.expiry = mkt["instrument"]["expiry"]; self.ccy = mkt["instrument"]["currencies"][0]["code"]
        log(f"demo account {self.acc}, {EPIC} {mkt['instrument']['name']} min size {self.size} {self.ccy}/pt, status {mkt['snapshot']['marketStatus']}")
        self.state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        today = utcnow().strftime("%Y-%m-%d")
        if self.state.get("day") != today: self.state = {"day": today, "ntr": 0, "dpl": 0.0, "last_exit_bar": None}
        self.pos = None; self.recover_position()
        self.bars = self.history(); self.cur = None; self.ticks = 0; self.last_sign = 0
        log(f"history {len(self.bars)} bars to {self.bars.index[-1]}")

    # ---------------------------------------------------------------- data
    def history(self):
        h = self.ig.fetch_historical_prices_by_epic(EPIC, resolution="5Min", numpoints=300)["prices"]
        rows = []
        for x in h:
            ts = pd.Timestamp(x["snapshotTimeUTC"] if "snapshotTimeUTC" in x else x["snapshotTime"]).tz_localize("UTC") if pd.Timestamp(x.get("snapshotTimeUTC", x["snapshotTime"])).tz is None else pd.Timestamp(x["snapshotTimeUTC"])
            mid = lambda k: (x[k]["bid"] + x[k]["ask"])/2 if x[k]["bid"] is not None else np.nan
            rows.append(dict(ts=ts, open=mid("openPrice"), high=mid("highPrice"), low=mid("lowPrice"), close=mid("closePrice"),
                             vol=x.get("lastTradedVolume") or 0, delta=0.0, spread=(x["closePrice"]["ask"] - x["closePrice"]["bid"]) if x["closePrice"]["bid"] is not None else np.nan))
        d = pd.DataFrame(rows).dropna(subset=["close"]).set_index("ts").sort_index()
        d = d[~d.index.duplicated(keep="last")]
        return d

    def on_tick(self, item):
        v = item.get("values", item) if isinstance(item, dict) else item
        try:
            bid, ofr = float(v["BID"]), float(v["OFR"])
        except (KeyError, TypeError, ValueError): return
        t = utcnow(); mid = (bid + ofr)/2; spread = ofr - bid
        bucket = t.replace(second=0, microsecond=0, minute=(t.minute//BAR)*BAR)
        if self.cur is None or bucket != self.cur["ts"]:
            if self.cur is not None: self.close_bar()
            self.cur = {"ts": bucket, "open": mid, "high": mid, "low": mid, "close": mid, "vol": 0, "delta": 0, "spread_sum": 0.0, "last_mid": mid}
        c = self.cur; s = np.sign(mid - c["last_mid"])
        if s == 0: s = self.last_sign
        self.last_sign = s; c["delta"] += s; c["vol"] += 1; c["spread_sum"] += spread; c["last_mid"] = mid
        c["high"] = max(c["high"], mid); c["low"] = min(c["low"], mid); c["close"] = mid

    def close_bar(self):
        c = self.cur
        row = pd.DataFrame([dict(open=c["open"], high=c["high"], low=c["low"], close=c["close"], vol=c["vol"], delta=c["delta"], spread=c["spread_sum"]/max(c["vol"], 1))], index=[pd.Timestamp(c["ts"])])
        self.bars = pd.concat([self.bars, row]); self.bars = self.bars[~self.bars.index.duplicated(keep="last")].tail(600)
        with open(f"{OUT}/bars_{c['ts'].strftime('%Y-%m-%d')}.csv", "a") as f:
            f.write(f"{c['ts'].isoformat()},{c['open']:.2f},{c['high']:.2f},{c['low']:.2f},{c['close']:.2f},{c['vol']},{c['delta']},{row.spread.iloc[0]:.2f}\n")
        try: self.decide()
        except Exception: log("decide error:", traceback.format_exc())

    # ---------------------------------------------------------------- strategy
    def decide(self):
        d = P7.features(self.bars); i = len(d) - 1; row = d.iloc[i]; ts = d.index[i]
        mins = ts.hour*60 + ts.minute
        if self.pos:
            self.manage(d, i); return
        s = int(row.sig)
        if s == 0 or np.isnan(row.atr): return
        if not (US_OPEN <= mins < US_CLOSE): log(f"bar {ts:%H:%M} sig {s} outside US hours — skipped"); return
        st = self.state
        if st["ntr"] >= P7.MAXT or st["dpl"] <= -P7.LOSSCAP: log("governor: daily cap reached"); return
        if st.get("last_exit_bar") is not None and (i - st["last_exit_bar"]) < P7.COOL: return
        self.open(s, row, ts)

    def open(self, s, row, ts):
        direction = "BUY" if s == 1 else "SELL"; tgt = round(P7.TGT_ATR*row.atr, 1)
        log(f"SIGNAL {direction} at bar {ts:%H:%M} close {row.close:.1f} atr {row.atr:.1f} ign {row.ign:.2f} dshare {row.dshare:+.3f}")
        if self.dry: log("dry run — no order"); return
        r = self.ig.create_open_position(currency_code=self.ccy, direction=direction, epic=EPIC, expiry=self.expiry, force_open=True, guaranteed_stop=False,
                                         level=None, limit_distance=tgt, limit_level=None, order_type="MARKET", quote_id=None, size=self.size,
                                         stop_distance=P7.STOP, stop_level=None, trailing_stop=False, trailing_stop_increment=None)
        if r.get("dealStatus") != "ACCEPTED": log("order rejected:", r.get("reason"), r); return
        self.pos = {"deal_id": r["dealId"], "side": s, "entry": float(r["level"]), "paper_entry": float(row.close), "atr": float(row.atr), "opened": str(ts),
                    "bar_i": len(self.bars) - 1, "best": float(r["level"]), "be": False, "stop": float(r["level"]) - s*P7.STOP, "bars": 0}
        self.state["ntr"] += 1; self.save()
        log(f"FILLED {direction} {self.size}/pt at {self.pos['entry']} (paper would assume next open) stop {self.pos['stop']:.1f} limit +{tgt}")

    def manage(self, d, i):
        p = self.pos; s = p["side"]; H, L, C = d.high.values, d.low.values, d.close.values
        p["bars"] += 1
        fav = H[i] if s == 1 else L[i]; p["best"] = max(p["best"], fav) if s == 1 else min(p["best"], fav)
        new_stop = p["stop"]
        if not p["be"] and s*(p["best"] - p["entry"]) >= P7.BE: p["be"] = True; new_stop = p["entry"] + s*2*(d.spread.iloc[i]/2)
        if p["be"]:
            t = p["best"] - s*P7.TRAIL_ATR*p["atr"]
            if (s == 1 and t > new_stop) or (s == -1 and t < new_stop): new_stop = t
        if p["bars"] >= P7.CAP: self.close("cap"); return
        if abs(new_stop - p["stop"]) >= 0.5:
            try:
                r = self.ig.update_open_position(limit_level=None, stop_level=round(new_stop, 1), deal_id=p["deal_id"])
                if r.get("dealStatus", "ACCEPTED") == "ACCEPTED": p["stop"] = new_stop; log(f"stop -> {new_stop:.1f} ({'BE/trail' if p['be'] else 'init'})")
            except Exception as e: log("update stop:", e)
        self.check_closed_by_ig()

    def check_closed_by_ig(self):
        if not self.pos: return
        open_ids = {x["position"]["dealId"] for x in self.ig.fetch_open_positions()["positions"]}
        if self.pos["deal_id"] not in open_ids:
            lvl, how = self.last_close_level()
            self.book(lvl, how)

    def last_close_level(self):
        try:
            act = self.ig.fetch_account_activity_by_period(1_800_000)["activities"]   # last 30 min
            for a in act:
                if a.get("epic") == EPIC and a.get("status") in ("CLOSED", "DELETED") or "clos" in str(a.get("activity", "")).lower():
                    return float(a.get("level") or a.get("details", {}).get("level") or np.nan), "ig_stop_or_limit"
        except Exception as e: log("activity:", e)
        return np.nan, "ig_closed"

    def close(self, how):
        p = self.pos
        if self.dry: log("dry run — would close", how); self.pos = None; return
        r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] == 1 else "BUY", epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=self.size)
        lvl = float(r.get("level") or np.nan)
        self.book(lvl, how)

    def book(self, lvl, how):
        p = self.pos; s = p["side"]; pts = s*(lvl - p["entry"]) if not np.isnan(lvl) else np.nan
        hdr = not os.path.exists(TRADES)
        with open(TRADES, "a") as f:
            if hdr: f.write("opened,closed,side,paper_entry,ig_entry,ig_exit,pts,how,bars\n")
            f.write(f"{p['opened']},{utcnow().isoformat()},{s},{p['paper_entry']:.2f},{p['entry']:.2f},{lvl:.2f},{pts:.2f},{how},{p['bars']}\n")
        self.state["dpl"] += 0 if np.isnan(pts) else pts; self.state["last_exit_bar"] = len(self.bars) - 1
        log(f"CLOSED {how} at {lvl} -> {pts:+.1f} pts (day {self.state['dpl']:+.1f}, trades {self.state['ntr']})")
        self.pos = None; self.save()

    def recover_position(self):
        try:
            for x in self.ig.fetch_open_positions()["positions"]:
                if x["market"]["epic"] == EPIC:
                    p = x["position"]; s = 1 if p["direction"] == "BUY" else -1
                    self.pos = {"deal_id": p["dealId"], "side": s, "entry": float(p["level"]), "paper_entry": np.nan, "atr": float(self.state.get("last_atr", 30.0)), "opened": p.get("createdDateUTC", ""),
                                "bar_i": 0, "best": float(p["level"]), "be": False, "stop": float(p["stopLevel"] or 0), "bars": int(self.state.get("open_bars", 0))}
                    log("recovered open position", self.pos["deal_id"])
        except Exception as e: log("recover:", e)

    def save(self):
        if self.pos: self.state.update(last_atr=self.pos["atr"], open_bars=self.pos["bars"])
        json.dump(self.state, open(STATE, "w"), indent=1)

    # ---------------------------------------------------------------- loop
    def run(self):
        # stream on the EXISTING session (IGStreamService.create_session would log in again and reset the account)
        cst = self.ig.session.headers["CST"]; xst = self.ig.session.headers["X-SECURITY-TOKEN"]
        ls = LightstreamerClient(self.ls_endpoint, None); ls.connectionDetails.setUser(self.session_acc); ls.connectionDetails.setPassword(f"CST-{cst}|XST-{xst}")
        ls.connect(); log("stream user", self.session_acc, "endpoint", self.ls_endpoint)
        class _S:  # minimal shim with the two methods used below
            def subscribe(self, sub): ls.subscribe(sub)
            def disconnect(self): ls.disconnect()
        stream = _S()
        sub = Subscription(mode="DISTINCT", items=[f"CHART:{EPIC}:TICK"], fields=["BID", "OFR", "UTM"])
        runner = self
        class L(SubscriptionListener):
            def onItemUpdate(self, u):
                runner.ticks += 1; runner.on_tick({"BID": u.getValue("BID"), "OFR": u.getValue("OFR")})
            def onSubscriptionError(self, code, message): log("subscription error", code, message)
            def onSubscription(self): log("subscribed")
        sub.addListener(L())
        stream.subscribe(sub); log("streaming", EPIC)
        last_check = time.time()
        while utcnow() < self.end:
            time.sleep(1)
            if time.time() - last_check > 60:
                last_check = time.time()
                if self.pos and not self.dry: self.check_closed_by_ig()
                if self.cur and (utcnow() - self.cur["ts"]).total_seconds() > BAR*60 + 20: self.close_bar(); self.cur = None
        if self.pos and utcnow().hour >= 21: self.close("session_end")
        self.save(); stream.disconnect(); log("done; ticks", self.ticks, "bars", len(self.bars))


if __name__ == "__main__":
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    dry = "--dry" in sys.argv
    end = utcnow() + dt.timedelta(minutes=minutes)
    try:
        Runner(end, dry).run()
    except Exception:
        log("FATAL", traceback.format_exc())
        open(f"{OUT}/last_error.txt", "w").write(traceback.format_exc())
