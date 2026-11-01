"""News-day fade engine for the IG DEMO (doc 156 rules, doc 169 book 13). US Tech 100 after CPI (8:30 New York) and FOMC (2pm New York).
P = last close before the release; wait 15 minutes; spike = the larger excursion from P in those 15 minutes; X = spike extreme (tracked);
trigger = the first 5-minute bar after the wait that CLOSES beyond the previous bar's low (spike up; mirror for down) while still on the
spike side of P -> trade AGAINST the spike at market; stop X (+0.02%), limit P; flat 4 hours after the release. No trade if price closes
back through P first, or if the trigger already passed before this runner saw it. Risk 1% of book equity (ig_book). DEMO ONLY."""
import os, json, datetime as dt, numpy as np, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); OUT = "runs/ig_demo"; TRADES = f"{OUT}/news_trades.csv"
W, HOLD = pd.Timedelta(minutes=15), pd.Timedelta(hours=4)

def events():
    try: j = json.load(open(f"{ROOT}/runs/event_blackouts.json"))
    except Exception: return []
    ev = [pd.Timestamp(d + " 14:00", tz="America/New_York").tz_convert("UTC") for d in j.get("fomc", [])]
    ev += [pd.Timestamp(d + " 08:30", tz="America/New_York").tz_convert("UTC") for d in j.get("cpi", [])]
    return sorted(ev)

def live_signal(bars, T, now_ts):
    """bars: 5-min OHLC with UTC index (bar start). Returns ('trade', side, entry, stop, target) when the LAST completed bar is the
    trigger; ('wait',) before it; ('void', why) when the event can no longer trade."""
    b = bars.copy(); b.index = pd.DatetimeIndex(b.index); b.index = b.index.tz_localize("UTC") if b.index.tz is None else b.index.tz_convert("UTC")
    pre = b[b.index < T]
    if len(pre) < 3: return ("void", "no bars before the release")
    P = float(pre.close.iloc[-1]); w = b[(b.index >= T) & (b.index < T + W)]
    if now_ts < T + W or len(w) < 2: return ("wait",)
    s = 1 if (w.high.max() - P) >= (P - w.low.min()) else -1; X = float(w.high.max() if s == 1 else w.low.min())
    a = b[(b.index >= T + W) & (b.index < T + HOLD)]
    H, L, C = a.high.values, a.low.values, a.close.values
    for k in range(1, len(C)):
        X = max(X, H[k]) if s == 1 else min(X, L[k])
        if (C[k] - P) * s <= 0: return ("void", "back through the pre-news level before a trigger")
        if (s == 1 and C[k] < L[k - 1]) or (s == -1 and C[k] > H[k - 1]):
            if k == len(C) - 1: return ("trade", -s, float(C[k]), float(X * (1 + 0.0002 * s)), P)
            return ("void", "trigger already passed")
    return ("wait",)

class NewsFade:
    def __init__(self, ig, epic, expiry, ccy, dry, state, book, min_size, log):
        self.ig, self.epic, self.expiry, self.ccy, self.dry, self.book, self.min, self.log = ig, epic, expiry, ccy, dry, book, min_size, log
        self.st = state.setdefault("news", {}); self.ev = events()
    def active(self, now):
        return [T for T in self.ev if T - pd.Timedelta(minutes=5) <= now < T + HOLD]
    def deal_ids(self): return {v["pos"]["deal_id"] for v in self.st.values() if v.get("pos")}
    def on_bar(self, bars, now):
        for T in self.active(now):
            key = T.isoformat(); e = self.st.setdefault(key, {"done": False, "pos": None})
            if e.get("pos"): self.manage(e, T, now); continue
            if e["done"]: continue
            sig = live_signal(bars, T, now)
            if sig[0] == "void": e["done"] = True; self.log(f"news fade {key}: no trade — {sig[1]}"); continue
            if sig[0] == "trade": self.open(e, key, *sig[1:])
        for key, e in self.st.items():                         # an event whose window ended with a position still open
            if e.get("pos") and now >= pd.Timestamp(key) + HOLD: self.close(e, "time")
    def open(self, e, key, side, entry, stop, target):
        risk = abs(entry - stop)
        if risk <= 0 or (target - entry) * side <= 0: e["done"] = True; self.log(f"news fade {key}: degenerate levels, no trade"); return
        if not self.book.day_ok(): e["done"] = True; self.log(f"news fade {key}: book daily stop reached, no trade"); return
        size = self.book.news_size(risk, self.min); d = "BUY" if side == 1 else "SELL"
        self.log(f"news fade {key}: SIGNAL {d} at {entry:.1f} stop {stop:.1f} target {target:.1f} ({risk:.1f} pts risk) {size}/pt")
        e["done"] = True
        if self.dry: return
        r = self.ig.create_open_position(currency_code=self.ccy, direction=d, epic=self.epic, expiry=self.expiry, force_open=True, guaranteed_stop=False,
                                         level=None, limit_distance=None, limit_level=round(target, 1), order_type="MARKET", quote_id=None, size=size,
                                         stop_distance=None, stop_level=round(stop, 1), trailing_stop=False, trailing_stop_increment=None)
        if r.get("dealStatus") != "ACCEPTED": self.log("news fade order rejected:", r.get("reason")); return
        e["pos"] = {"deal_id": r["dealId"], "side": side, "entry": float(r["level"]), "paper_entry": entry, "size": size, "opened": dt.datetime.now(dt.timezone.utc).isoformat()}
        self.log(f"news fade FILLED {d} {size}/pt at {r['level']}")
    def manage(self, e, T, now):
        if now >= T + HOLD: self.close(e, "time"); return
        if self.dry: return
        try:
            if e["pos"]["deal_id"] not in {x["position"]["dealId"] for x in self.ig.fetch_open_positions()["positions"]}: self.record(e, np.nan, "ig_stop_or_limit")
        except Exception as ex: self.log("news fade check:", ex)
    def close(self, e, how):
        p = e["pos"]; lvl = np.nan
        if not self.dry:
            try:
                r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] == 1 else "BUY", epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=p["size"])
                lvl = float(r.get("level") or np.nan)
            except Exception as ex: self.log("news fade close:", ex); return
        self.record(e, lvl, how)
    def record(self, e, lvl, how):
        p = e["pos"]
        if lvl != lvl:                                         # level unknown (IG closed it): read it from the transaction history
            try:
                now = dt.datetime.now(dt.timezone.utc); tx = self.ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=50)
                for t in (tx.get("transactions", tx) if isinstance(tx, dict) else tx):
                    try: ol, cl = float(t.get("openLevel")), float(t.get("closeLevel"))
                    except Exception: continue
                    if abs(ol - p["entry"]) <= 2.0: lvl = cl; break
            except Exception as ex: self.log("news fade tx:", ex)
        pts = p["side"] * (lvl - p["entry"]) if lvl == lvl else np.nan; gbp = pts * p["size"] if pts == pts else np.nan
        self.book.add(gbp, "news"); hdr = not os.path.exists(TRADES)
        with open(TRADES, "a") as f:
            if hdr: f.write("opened,closed,side,paper_entry,ig_entry,ig_exit,pts,size,gbp,how\n")
            f.write(f"{p['opened']},{dt.datetime.now(dt.timezone.utc).isoformat()},{p['side']},{p['paper_entry']:.2f},{p['entry']:.2f},{lvl:.2f},{pts:.2f},{p['size']},{gbp:.2f},{how}\n")
        self.log(f"news fade CLOSED {how} at {lvl} -> {pts:+.1f} pts, £{gbp:+.2f}; book £{self.book.eq:,.2f}"); e["pos"] = None
