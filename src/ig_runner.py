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
v1.1 (doc 108, from Mon 26 Oct 2026): no entries 16:00-18:59 UTC; stop = max(45, 1.5 x ATR20).
Second engine (doc 116, from Mon 26 Oct 2026): Range v3-IDX in src/ig_range_engine.py on US Tech 100 / Wall Street / Germany 40 — set IG_RANGE=0 to disable.
"""
import os, sys, json, time, math, datetime as dt, traceback
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import paperbook7 as P7
from ig_range_engine import RangeEngine
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab")
from trading_ig import IGService, IGStreamService
from lightstreamer.client import Subscription, SubscriptionListener, LightstreamerClient, ClientListener

EPIC = os.environ.get("IG_EPIC", "IX.D.NASDAQ.CASH.IP")   # US Tech 100, daily funded SPREAD BET (GBP per point); IX.D.NASDAQ.IFD.IP is the CFD
SIZE = float(os.environ.get("IG_SIZE", "1.0"))               # £ per point on the demo (doc 99 sizing)
V11 = os.environ.get("IG_V11", "1") == "1"                   # Ignition v1.1 (doc 108)
RANGE = os.environ.get("IG_RANGE", "1") == "1"               # Range v3-IDX engine (doc 116)
OUT = "runs/ig_demo"; os.makedirs(OUT, exist_ok=True)


def calibrate_dshare():
    """IG's tick feed carries ~1.7x the ticks of the Dukascopy feed the book was fitted on, so delta SHARE runs smaller in
    the tails (doc 119). Map the registered 0.05 (the top ~9% of Dukascopy bars over the year) to the same percentile of
    IG's own bars, once enough IG bars exist; until then use the tail ratio measured on the first three days (0.878)."""
    import glob
    try:
        full = pd.read_csv(f"{ROOT}/data_nq_cache/nq_5m.csv", index_col=0)
        p = float(((full.delta/full.vol.replace(0, np.nan)).abs().dropna() >= P7.DSHARE).mean())
        fs = sorted(glob.glob(f"{OUT}/bars_*.csv"))
        ig = pd.concat([pd.read_csv(f, header=None, names="ts,open,high,low,close,vol,delta,spread".split(",")) for f in fs]) if fs else pd.DataFrame()
        ig = ig[ig.ts.astype(str).str.startswith("20")] if len(ig) else ig
        if len(ig) >= 500:
            ds = (ig.delta.astype(float)/ig.vol.astype(float).replace(0, np.nan)).abs().dropna()
            thr = float(ds.quantile(1 - p)); src = f"percentile-matched on {len(ig)} IG bars"
        else:
            thr = P7.DSHARE*0.878; src = f"tail-ratio default ({len(ig)} IG bars, <500)"
        thr = min(max(thr, 0.035), P7.DSHARE)
    except Exception as e:
        thr, src = P7.DSHARE, f"calibration failed ({e}); registered threshold"
    return thr, src
STATE = f"{OUT}/state.json"; TRADES = f"{OUT}/trades.csv"
US_OPEN, US_CLOSE = P7.US_OPEN, P7.US_CLOSE   # New York local minutes (DST-proof, 27 Oct 2026)
BAR = 5


def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), *a, flush=True)


class Runner:
    def __init__(self, end_utc, dry):
        thr, src = calibrate_dshare(); P7.DSHARE = thr; log(f"delta-share threshold {thr:.4f} ({src}); registered 0.05")
        self.end = end_utc; self.dry = dry
        u, p, k = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
        # ONE session. Step 1: on the CFD demo account, open the price stream and confirm the subscription.
        self.ig = IGService(u, p, k, acc_type="demo", return_dataframe=False)
        sess = self.ig.create_session(); self.ls_endpoint = sess.get("lightstreamerEndpoint"); cur = sess.get("currentAccountId")
        accs = self.ig.fetch_accounts()["accounts"]
        sb = [a for a in accs if a["accountType"] == "SPREADBET"]; cfd = [a for a in accs if a["accountType"] == "CFD"]
        if not sb: raise RuntimeError("no SPREADBET demo account")
        self.acc = sb[0]["accountId"]
        want_px = cfd[0]["accountId"] if (cfd and os.environ.get("IG_STREAM_VIA_CFD", "0") == "1") else self.acc
        if cur != want_px: self.ig.switch_account(want_px, False); cur = want_px
        self.stream_acc = cur; self.stream_pw = f"CST-{self.ig.session.headers['CST']}|XST-{self.ig.session.headers['X-SECURITY-TOKEN']}"
        self.ig_px = self.ig
        self.feed = None; self.ticks = 0; self.cur = {}; self.last_sign = {}; self.bars = pd.DataFrame(); self.engine = None; self.epics = [EPIC]
        self.ig_px = self.ig; self.bars = self.history(); log(f"history {len(self.bars)} bars to {self.bars.index[-1]}")
        self.open_stream()
        for _ in range(20):
            if self.feed: break
            time.sleep(0.5)
        log("stream", "subscribed on " + self.feed if self.feed else "NOT subscribed", "via", self.stream_acc)
        # Step 2: switch the REST session to the spread-bet account for orders
        if cur != self.acc:
            self.ig.switch_account(self.acc, True)
        self.session_acc = self.acc; log("trading session on", self.session_acc)
        mkt = self.ig.fetch_market_by_epic(EPIC)
        self.size = max(SIZE, float(mkt["dealingRules"]["minDealSize"]["value"])); self.expiry = mkt["instrument"]["expiry"]; cc = [c["code"] for c in mkt["instrument"]["currencies"]]; self.ccy = "GBP" if "GBP" in cc else cc[0]
        log(f"demo account {self.acc}, {EPIC} {mkt['instrument']['name']} min size {self.size} {self.ccy}/pt, status {mkt['snapshot']['marketStatus']}")
        self.state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        today = utcnow().strftime("%Y-%m-%d")
        if self.state.get("day") != today: self.state = {"day": today, "ntr": 0, "dpl": 0.0, "last_exit_bar": None}
        self.pos = None; self.recover_position()
        if RANGE:
            try:
                self.engine = RangeEngine(self.ig, self.ccy, dry, self.state, self.rest_history, primary=(EPIC, self.bars))
                extra = [e for e in self.engine.epic2name if e not in self.epics]; self.epics += extra
                if extra: self.subscribe(extra)
            except Exception: log("range engine failed to start:", traceback.format_exc()); self.engine = None


    # ---------------------------------------------------------------- data
    def history(self): return self.rest_history(EPIC, "5Min", 300)

    def rest_history(self, epic, res, n):
        h = self.ig_px.fetch_historical_prices_by_epic(epic, resolution=res, numpoints=n)["prices"]
        rows = []
        for x in h:
            ts = pd.Timestamp(x["snapshotTimeUTC"] if "snapshotTimeUTC" in x else x["snapshotTime"]).tz_localize("UTC") if pd.Timestamp(x.get("snapshotTimeUTC", x["snapshotTime"])).tz is None else pd.Timestamp(x["snapshotTimeUTC"])
            mid = lambda k: (x[k]["bid"] + x[k]["ask"])/2 if x[k]["bid"] is not None else np.nan
            rows.append(dict(ts=ts, open=mid("openPrice"), high=mid("highPrice"), low=mid("lowPrice"), close=mid("closePrice"),
                             vol=x.get("lastTradedVolume") or 0, delta=0.0, spread=(x["closePrice"]["ask"] - x["closePrice"]["bid"]) if x["closePrice"]["bid"] is not None else np.nan))
        d = pd.DataFrame(rows).dropna(subset=["close"]).set_index("ts").sort_index()
        d = d[~d.index.duplicated(keep="last")]
        return d

    def on_tick(self, item, epic=EPIC):
        v = item.get("values", item) if isinstance(item, dict) else item
        try:
            bid, ofr = float(v["BID"]), float(v["OFR"])
        except (KeyError, TypeError, ValueError): return
        t = utcnow(); mid = (bid + ofr)/2; spread = ofr - bid
        bucket = t.replace(second=0, microsecond=0, minute=(t.minute//BAR)*BAR)
        cur = self.cur.get(epic)
        if cur is None or bucket != cur["ts"]:
            if cur is not None: self.close_bar(epic)
            self.cur[epic] = {"ts": bucket, "open": mid, "high": mid, "low": mid, "close": mid, "vol": 0, "delta": 0, "spread_sum": 0.0, "last_mid": mid}
        c = self.cur[epic]; s = np.sign(mid - c["last_mid"])
        if s == 0: s = self.last_sign.get(epic, 0)
        self.last_sign[epic] = s; c["delta"] += s; c["vol"] += 1; c["spread_sum"] += spread; c["last_mid"] = mid
        c["high"] = max(c["high"], mid); c["low"] = min(c["low"], mid); c["close"] = mid

    def close_bar(self, epic=EPIC):
        c = self.cur.get(epic); self.cur[epic] = None
        if c is None: return
        if self.engine:
            try: self.engine.on_bar5(epic, c)
            except Exception: log("range engine error:", traceback.format_exc())
        if epic != EPIC: return
        log(f"bar {c['ts']:%H:%M} o {c['open']:.1f} h {c['high']:.1f} l {c['low']:.1f} c {c['close']:.1f} ticks {c['vol']} delta {c['delta']:+.0f}")
        row = pd.DataFrame([dict(open=c["open"], high=c["high"], low=c["low"], close=c["close"], vol=c["vol"], delta=c["delta"], spread=c["spread_sum"]/max(c["vol"], 1))], index=[pd.Timestamp(c["ts"])])
        self.bars = pd.concat([self.bars, row]); self.bars = self.bars[~self.bars.index.duplicated(keep="last")].tail(600)
        with open(f"{OUT}/bars_{c['ts'].strftime('%Y-%m-%d')}.csv", "a") as f:
            f.write(f"{c['ts'].isoformat()},{c['open']:.2f},{c['high']:.2f},{c['low']:.2f},{c['close']:.2f},{c['vol']},{c['delta']},{row.spread.iloc[0]:.2f}\n")
        try: self.decide()
        except Exception: log("decide error:", traceback.format_exc())

    # ---------------------------------------------------------------- strategy
    def decide(self):
        if not self.dry: self.resolve_pending()
        d = P7.features(self.bars); i = len(d) - 1; row = d.iloc[i]; ts = d.index[i]
        nyt = P7.ny(ts); mins = nyt.hour*60 + nyt.minute
        if self.pos:
            self.manage(d, i); return
        s = int(row.sig)
        if s == 0 or np.isnan(row.atr): return
        if not (US_OPEN <= mins < US_CLOSE): log(f"bar {ts:%H:%M} sig {s} outside US hours — skipped"); return
        if V11 and nyt.hour in P7.V11_SKIP_HOURS: log(f"bar {ts:%H:%M} sig {s} in the US lunch window (12-15 New York) — skipped (v1.1)"); return
        st = self.state
        if st["ntr"] >= P7.MAXT or st["dpl"] <= -P7.LOSSCAP: log("governor: daily cap reached"); return
        if st.get("last_exit_bar") is not None and (i - st["last_exit_bar"]) < P7.COOL: return
        self.open(s, row, ts)

    def open(self, s, row, ts):
        direction = "BUY" if s == 1 else "SELL"; tgt = round(P7.TGT_ATR*row.atr, 1)
        stop_pts = round(max(P7.STOP, P7.V11_STOP_ATR*row.atr), 1) if V11 else P7.STOP
        log(f"SIGNAL {direction} at bar {ts:%H:%M} close {row.close:.1f} atr {row.atr:.1f} ign {row.ign:.2f} dshare {row.dshare:+.3f}")
        if self.dry: log(f"dry run — no order (stop would be {stop_pts} pts)"); return
        r = self.ig.create_open_position(currency_code=self.ccy, direction=direction, epic=EPIC, expiry=self.expiry, force_open=True, guaranteed_stop=False,
                                         level=None, limit_distance=tgt, limit_level=None, order_type="MARKET", quote_id=None, size=self.size,
                                         stop_distance=stop_pts, stop_level=None, trailing_stop=False, trailing_stop_increment=None)
        if r.get("dealStatus") != "ACCEPTED": log("order rejected:", r.get("reason"), r); return
        self.pos = {"deal_id": r["dealId"], "side": s, "entry": float(r["level"]), "paper_entry": float(row.close), "atr": float(row.atr), "opened": str(ts),
                    "bar_i": len(self.bars) - 1, "best": float(r["level"]), "be": False, "stop": float(r["level"]) - s*stop_pts, "bars": 0}
        self.state["ntr"] += 1; self.save()
        log(f"FILLED {direction} {self.size}/pt at {self.pos['entry']} (paper would assume next open) stop {self.pos['stop']:.1f} ({stop_pts} pts) limit +{tgt}")

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
        """Exit level of the position IG just closed (stop/limit). Transactions first (openLevel/closeLevel), activity as fallback."""
        p = self.pos
        try:
            now = utcnow(); tx = self.ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=50)
            rows = tx.get("transactions", tx) if isinstance(tx, dict) else tx
            for t in rows:
                if str(t.get("transactionType", "")).upper() != "DEAL": continue
                try: ol, cl = float(t.get("openLevel")), float(t.get("closeLevel"))
                except Exception: continue
                if abs(ol - p["entry"]) <= 2.0:
                    log("tx:", t.get("instrumentName"), "open", ol, "close", cl, "P&L", t.get("profitAndLoss"))
                    return cl, "ig_stop" if (p["side"]*(cl - ol) < 0) else "ig_limit"
        except Exception as e: log("transactions:", e)
        try:
            act = self.ig.fetch_account_activity_by_period(1_800_000)["activities"]   # last 30 min
            for a in act:
                if a.get("epic") == EPIC and ("clos" in str(a.get("activity", "")).lower() or a.get("status") in ("CLOSED", "DELETED")):
                    return float(a.get("level") or a.get("details", {}).get("level") or np.nan), "ig_stop_or_limit"
        except Exception as e: log("activity:", e)
        return np.nan, "ig_closed"

    def close(self, how):
        p = self.pos
        if self.dry: log("dry run — would close", how); self.pos = None; return
        r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] == 1 else "BUY", epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=self.size)
        lvl = float(r.get("level") or np.nan)
        self.book(lvl, how)

    def resolve_pending(self):
        """A stop/limit exit whose level was unknown when booked (IG posts the transaction a few seconds late): re-query and patch the row."""
        pend = self.state.get("pending_exit")
        if not pend: return
        try:
            now = utcnow(); tx = self.ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=50)
            rows = tx.get("transactions", tx) if isinstance(tx, dict) else tx
            for t in rows:
                if str(t.get("transactionType", "")).upper() != "DEAL": continue
                try: ol, cl = float(t.get("openLevel")), float(t.get("closeLevel"))
                except Exception: continue
                if abs(ol - pend["entry"]) <= 2.0:
                    pts = pend["side"]*(cl - ol); how = "ig_stop" if pts < 0 else "ig_limit"
                    lines = open(TRADES).read().splitlines()
                    for k, ln in enumerate(lines):
                        if ln.startswith(pend["opened"]) and ",nan,nan," in ln:
                            f = ln.split(","); f[5] = f"{cl:.2f}"; f[6] = f"{pts:.2f}"; f[7] = how; lines[k] = ",".join(f)
                    open(TRADES, "w").write("\n".join(lines) + "\n")
                    self.state["dpl"] += pts; self.state["pending_exit"] = None; self.save(); log(f"pending exit resolved: {how} at {cl} -> {pts:+.1f} pts"); return
            pend["tries"] = pend.get("tries", 0) + 1
            if pend["tries"] >= 6: self.state["pending_exit"] = None; log("pending exit: not found after 6 tries")
            self.save()
        except Exception as e: log("resolve_pending:", e)

    def book(self, lvl, how):
        p = self.pos; s = p["side"]; pts = s*(lvl - p["entry"]) if not np.isnan(lvl) else np.nan
        if np.isnan(lvl): self.state["pending_exit"] = {"opened": p["opened"], "entry": p["entry"], "side": s, "tries": 0}
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
    def open_stream(self):
        runner = self
        ls = LightstreamerClient(self.ls_endpoint, None); ls.connectionDetails.setUser(self.stream_acc); ls.connectionDetails.setPassword(self.stream_pw)
        class CL(ClientListener):
            def onStatusChange(self, status): log("ls status:", status)
            def onServerError(self, code, message): log("ls server error:", code, message)
        ls.addListener(CL()); ls.connect(); log("stream user", self.stream_acc, "endpoint", self.ls_endpoint)
        self.ls = ls; self.subscribe([EPIC])

    def subscribe(self, epics):
        runner = self
        class L(SubscriptionListener):
            def __init__(self, name, bidf, ofrf, epic): self.name, self.bidf, self.ofrf, self.epic = name, bidf, ofrf, epic
            def onItemUpdate(self, u):
                try:
                    runner.ticks += 1
                    if runner.ticks <= 3: log(self.name, self.epic, "update:", {f: u.getValue(f) for f in (self.bidf, self.ofrf)})
                    if self.name == runner.feed: runner.on_tick({"BID": u.getValue(self.bidf), "OFR": u.getValue(self.ofrf)}, self.epic)
                except Exception: log("on_tick error:", traceback.format_exc())
            def onSubscriptionError(self, code, message): log(self.name, self.epic, "subscription error", code, message)
            def onSubscription(self): log(self.name, self.epic, "subscribed"); runner.feed = runner.feed or self.name
        for e in epics:
            sub = Subscription(mode="DISTINCT", items=[f"CHART:{e}:TICK"], fields=["BID", "OFR", "UTM"]); sub.addListener(L("CHART", "BID", "OFR", e))
            sub2 = Subscription(mode="MERGE", items=[f"MARKET:{e}"], fields=["BID", "OFFER", "UPDATE_TIME", "MARKET_STATE"]); sub2.addListener(L("MARKET", "BID", "OFFER", e))
            self.ls.subscribe(sub); self.ls.subscribe(sub2); log("streaming", e)

    def run(self):
        last_check = time.time()
        while utcnow() < self.end:
            time.sleep(1)
            if time.time() - last_check > 60:
                last_check = time.time()
                if self.pos and not self.dry: self.check_closed_by_ig()
                for e, c in list(self.cur.items()):
                    if c and (utcnow() - c["ts"]).total_seconds() > BAR*60 + 20: self.close_bar(e)
        if self.pos: self.close("session_end")
        if self.engine:
            try: self.engine.end_of_job()
            except Exception: log("range engine end:", traceback.format_exc())
        self.save(); self.ls.disconnect(); log("done; ticks", self.ticks, "bars", len(self.bars))


def order_test(r):
    """DEMO ONLY: open the minimum position with stop/limit attached, move the stop, close at market. Proves the order path."""
    d = P7.features(r.bars); row = d.iloc[-1]; atr = float(row.atr) if not np.isnan(row.atr) else 30.0
    for a in r.ig.fetch_accounts()["accounts"]:
        log("account", a["accountId"], a["accountType"], a.get("currency"), "balance", a.get("balance"), "preferred", a.get("preferred"), "status", a.get("status"))
    mkt = r.ig.fetch_market_by_epic(EPIC); curs = [c["code"] for c in mkt["instrument"]["currencies"]]; rules = mkt["dealingRules"]
    log("market currencies", curs, "min size", rules["minDealSize"], "min stop", rules.get("minNormalStopOrLimitDistance"), "status", mkt["snapshot"]["marketStatus"])
    log(f"ORDER TEST on demo {r.acc}: BUY {r.size}/pt {EPIC} in {r.ccy}, stop {P7.STOP}, limit +{P7.TGT_ATR*atr:.0f}")
    res = r.ig.create_open_position(currency_code=r.ccy, direction="BUY", epic=EPIC, expiry=r.expiry, force_open=True, guaranteed_stop=False, level=None,
                                    limit_distance=round(P7.TGT_ATR*atr, 1), limit_level=None, order_type="MARKET", quote_id=None, size=r.size,
                                    stop_distance=P7.STOP, stop_level=None, trailing_stop=False, trailing_stop_increment=None)
    log("open ->", {k: res.get(k) for k in ("dealStatus", "reason", "level", "dealId", "stopLevel", "limitLevel", "dealReference")})
    if res.get("dealStatus") != "ACCEPTED": return

    time.sleep(3); lvl = float(res["level"])
    up = r.ig.update_open_position(limit_level=None, stop_level=round(lvl - P7.STOP + 5, 1), deal_id=res["dealId"])
    log("move stop ->", {k: up.get(k) for k in ("dealStatus", "reason", "stopLevel")})
    time.sleep(3)
    cl = r.ig.close_open_position(deal_id=res["dealId"], direction="SELL", epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=r.size)
    log("close ->", {k: cl.get(k) for k in ("dealStatus", "reason", "level", "profit", "profitCurrency")})
    try:
        pts = float(cl["level"]) - lvl; log(f"round trip: in {lvl} out {cl['level']} = {pts:+.1f} pts (spread cost) in {time.time():.0f}")
    except Exception: pass


if __name__ == "__main__":
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    dry = "--dry" in sys.argv
    end = utcnow() + dt.timedelta(minutes=minutes)
    try:
        if "--tx" in sys.argv:
            u, p_, k = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
            ig = IGService(u, p_, k, acc_type="demo", return_dataframe=False); sess = ig.create_session()
            sb = [a for a in ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"]
            if sb and sess.get("currentAccountId") != sb[0]["accountId"]: ig.switch_account(sb[0]["accountId"], True)
            now = utcnow(); tx = ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=100)
            rows = tx.get("transactions", tx) if isinstance(tx, dict) else tx
            with open(f"{OUT}/tx.txt", "w") as f:
                for t in rows:
                    line = " | ".join(f"{k}={t.get(k)}" for k in ("dateUtc", "instrumentName", "transactionType", "size", "openLevel", "closeLevel", "profitAndLoss", "reference"))
                    log(line); f.write(line + "\n")
            sys.exit(0)
        if "--markets" in sys.argv:
            u, p_, k = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
            ig = IGService(u, p_, k, acc_type="demo", return_dataframe=False); sess = ig.create_session()
            sb = [a for a in ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"]
            if sb and sess.get("currentAccountId") != sb[0]["accountId"]: ig.switch_account(sb[0]["accountId"], True)
            for a in ig.fetch_accounts()["accounts"]: log("account", a["accountType"], "balance", a.get("balance"))
            epics = ["IX.D.NASDAQ.CASH.IP", "IX.D.DOW.DAILY.IP", "IX.D.DAX.DAILY.IP", "IX.D.FTSE.DAILY.IP", "IX.D.SPTRD.DAILY.IP", "CS.D.EURUSD.TODAY.IP", "CS.D.GBPUSD.TODAY.IP", "CS.D.USCGC.TODAY.IP", "CC.D.LCO.USS.IP"]
            with open(f"{OUT}/markets.txt", "w") as f:
                for e in epics:
                    try:
                        m = ig.fetch_market_by_epic(e); ins, r, sn = m["instrument"], m["dealingRules"], m["snapshot"]
                        bands = [(b.get("min"), b.get("max"), b.get("margin")) for b in (ins.get("marginDepositBands") or [])][:3]
                        line = (f"{e} | {ins.get('name')} | expiry {ins.get('expiry')} | minSize {r['minDealSize']} | minStop {r.get('minNormalStopOrLimitDistance')} | "
                                f"marginFactor {ins.get('marginFactor')} {ins.get('marginFactorUnit')} | bands {bands} | bid {sn.get('bid')} offer {sn.get('offer')} | "
                                f"valueOfOnePip {ins.get('valueOfOnePip')} onePipMeans {ins.get('onePipMeans')} | status {sn.get('marketStatus')} | ccy {[c['code'] for c in ins.get('currencies', [])]}")
                    except Exception as ex: line = f"{e} | ERROR {ex}"
                    log(line); f.write(line + "\n"); time.sleep(2)
            sys.exit(0)
        if "--order-test" in sys.argv:
            r = Runner(end, True); order_test(r); r.ls.disconnect(); sys.exit(0)
        Runner(end, dry).run()
    except SystemExit: pass
    except Exception:
        log("FATAL", traceback.format_exc())
        open(f"{OUT}/last_error.txt", "w").write(traceback.format_exc())
    sys.stdout.flush(); os._exit(0)   # daemon stream threads otherwise trip a lock at interpreter shutdown
