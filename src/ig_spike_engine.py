"""
SPIKE CONTINUATION ENGINE for the IG runner (demo; live from 9 Nov 2026 under the widened CAP-021 scope, doc 194) (doc 191, DK 8 Nov 2026: "Yes also run the demos if they are worthy of further investigation").
On live: only with the 9 Nov confirmation string, IG minimum stakes, and never more than 2% of the book at risk.

Rule (chosen on US Tech 100 2020-21, holdout 2025-26 +0.19R n40; US 500 2025-26 +0.27R n34 untuned):
  - cash session only (09:30-16:00 New York); 15-minute bars (the range engine's IG-aligned 15-min bars are reused — no extra history calls);
  - SPIKE: a 15-min bar whose range >= 3x the mean 15-min cash-session range of the previous 5 sessions;
  - CONFIRM: the NEXT 15-min bar extends the spike's extreme by > 0.25 x the spike range AND closes beyond the spike's close;
  - enter at market at that close, WITH the spike; stop at the confirming bar's opposite extreme; limit at entry +/- 1 x spike range;
  - exit at market after 8 bars (2 hours), at the cash close, or at the end of the job (whichever first).
Sizing: 2% of book equity at risk (ig_book.BookEquity, the same £500 book as the other engines), 5x exposure cap, -4% day stop.
Its own 8 trades a day per market (gov key ntr_spike_<market>). State: <OUT>/spike_state.json; trades: <OUT>/spike_trades.csv.
"""
import os, json, csv, datetime as dt, traceback
import numpy as np, pandas as pd
from ig_mode import OUT, LIVE, MIN_ONLY, WIDE

STATE = f"{OUT}/spike_state.json"; TRADES = f"{OUT}/spike_trades.csv"
SESS = {"NQ": ("America/New_York", 9.5, 16.0), "US500": ("America/New_York", 9.5, 16.0)}
K_SPIKE, X_EXT, TGT_R, HOLD_BARS, MAXT, RISK = 3.0, 0.25, 1.0, 8, 8, 0.02


def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a): print(utcnow().strftime("%H:%M:%S"), "[spike]", *a, flush=True)


def spike_signal(d, tz, h0, h1):
    """d: 15-min OHLC (UTC index), last row = the bar that just closed. Returns None or dict(side, entry, stop, target, spike_range, ref)."""
    if len(d) < 200: return None
    lt = d.index.tz_convert(tz); hh = lt.hour + lt.minute / 60; day = np.array(lt.date)
    sess = (hh >= h0) & (hh < h1)
    i = len(d) - 1; j = i - 1
    if not (sess[i] and sess[j] and day[i] == day[j]): return None
    rng = (d.high - d.low).values
    dm = pd.Series(np.where(sess, rng, np.nan)).groupby(day).mean().dropna()
    prior = dm[dm.index < day[i]].tail(5)
    if len(prior) < 5: return None
    ref = float(prior.mean()); r = float(rng[j])
    if not (ref > 0 and r >= K_SPIKE * ref): return None
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values
    s = 1 if C[j] > O[j] else -1 if C[j] < O[j] else 0
    if s == 0: return None
    ext = (H[i] - H[j]) / r if s == 1 else (L[j] - L[i]) / r
    if not (ext > X_EXT and s * (C[i] - C[j]) > 0): return None
    stop = float(L[i]) if s == 1 else float(H[i])
    if s * (C[i] - stop) <= 0: return None
    return dict(side=s, entry=float(C[i]), stop=stop, target=float(C[i] + s * TGT_R * r), spike_range=r, ref=ref, bar=str(d.index[i]))


class SpikeEngine:
    def __init__(self, ig, ccy, dry, gov, range_engine, book, notional_fn, markets):
        if LIVE and not WIDE: raise SystemExit("spike engine on live needs the CAP-021 amendment of 9 Nov 2026 (wider scope)")
        self.ig, self.ccy, self.dry, self.gov, self.eng, self.beq, self.notional_fn = ig, ccy, dry, gov, range_engine, book, notional_fn
        self.markets = [m for m in markets if m in SESS and m in range_engine.mkt and m not in range_engine.disabled]
        self.st = json.load(open(STATE)) if os.path.exists(STATE) else {}
        self.st.setdefault("pos", {})
        log("markets:", self.markets or "none (needs the range engine's bars for NQ / US500)")

    def key(self, name): return f"ntr_spike_{name}"

    def on_bar5(self, epic, c):
        name = self.eng.epic2name.get(epic)
        if name not in self.markets or c["ts"].minute % 15 != 10: return
        try: self.step(name)
        except Exception: log(name, "step error:", traceback.format_exc())

    def step(self, name):
        d = self.eng.bars15[name]; tz, h0, h1 = SESS[name]; ts = d.index[-1]
        p = self.st["pos"].get(name)
        if p:
            self.sync(name)
            p = self.st["pos"].get(name)
            if p:
                age = int((ts - pd.Timestamp(p["bar"])) / pd.Timedelta(minutes=15))
                lt = ts.tz_convert(tz); hh = lt.hour + lt.minute / 60 + 0.25   # end of the bar that just closed
                if age >= HOLD_BARS or hh >= h1: self.close(name, "time" if age >= HOLD_BARS else "cash_close")
            return
        sig = spike_signal(d, tz, h0, h1)
        if not sig: return
        what = f"{'BUY' if sig['side']==1 else 'SELL'} spike {sig['spike_range']:.1f} (ref {sig['ref']:.1f}) entry~{sig['entry']:.1f} stop {sig['stop']:.1f} tgt {sig['target']:.1f}"
        if self.gov.get(self.key(name), 0) >= MAXT: log(name, "SIGNAL", what, "— skipped, 8 spike trades today"); return
        if self.beq and not self.beq.day_ok(): log(name, "SIGNAL", what, "— skipped, book day stop"); return
        mk = self.eng.mkt[name]; risk = abs(sig["entry"] - sig["stop"])
        if risk < mk.get("minstop", 0): sig["stop"] = sig["entry"] - sig["side"] * mk["minstop"]; risk = mk["minstop"]
        rk = RISK
        if LIVE:
            import live_limits as L; rk = L.intraday_risk(self.beq.pot.pot if self.beq and getattr(self.beq, "pot", None) is not None and "acc" in self.beq.pot.s else (self.beq.eq if self.beq else 500))
        size = max(mk["min"], int(self.beq.eq * rk * self.beq.k / risk * 100) / 100) if self.beq else mk["min"]
        if MIN_ONLY: size = mk["min"]   # live: IG minimum stake on every order (doc 185)
        if self.beq: size = self.beq.cap(size, sig["entry"], self.notional_fn() if self.notional_fn else 0.0, mk["min"])
        if LIVE and self.beq and size * risk > rk * self.beq.eq * self.beq.k + 1e-9:   # rule 186 on real money: never more than the tier's intraday risk (DK 11 Nov: 3%)
            log(name, "SIGNAL", what, f"— skipped, {size}/pt x {risk:.0f} pts is more than {rk:.0%} of the book"); return
        if size <= 0: log(name, "SIGNAL", what, "— skipped, 5x exposure cap"); return
        log(name, "SIGNAL", what, f"size {size}/pt")
        if self.dry:
            self.st["pos"][name] = dict(deal_id="dry", side=sig["side"], px=sig["entry"], sz=size, bar=str(ts), stop=sig["stop"], tgt=sig["target"])
        else:
            r = self.ig.create_open_position(currency_code=self.ccy, direction="BUY" if sig["side"] == 1 else "SELL", epic=mk["epic"], expiry=mk["expiry"],
                                             force_open=True, guaranteed_stop=False, level=None, limit_distance=None, limit_level=round(sig["target"], 1),
                                             order_type="MARKET", quote_id=None, size=size, stop_distance=None, stop_level=round(sig["stop"], 1),
                                             trailing_stop=False, trailing_stop_increment=None)
            if r.get("dealStatus") != "ACCEPTED": log(name, "order rejected:", r.get("reason")); return
            self.st["pos"][name] = dict(deal_id=r["dealId"], side=sig["side"], px=float(r["level"]), sz=size, bar=str(ts), stop=sig["stop"], tgt=sig["target"])
            log(name, f"FILLED {'BUY' if sig['side']==1 else 'SELL'} {size}/pt at {r['level']} stop {sig['stop']:.1f} limit {sig['target']:.1f}")
        self.gov[self.key(name)] = self.gov.get(self.key(name), 0) + 1; self.save()

    def sync(self, name):
        """position closed by IG (stop or limit) -> book it"""
        p = self.st["pos"][name]
        if self.dry or p["deal_id"] == "dry":   # dry runs: play IG's stop and limit against the bar that just closed
            b = self.eng.bars15[name].iloc[-1]; s = p["side"]
            if (s == 1 and b.low <= p["stop"]) or (s == -1 and b.high >= p["stop"]): self.book(name, p["stop"], "stop(dry)")
            elif (s == 1 and b.high >= p["tgt"]) or (s == -1 and b.low <= p["tgt"]): self.book(name, p["tgt"], "limit(dry)")
            return
        try: ids = {x["position"]["dealId"] for x in self.ig.fetch_open_positions()["positions"]}
        except Exception as ex: log(name, "sync:", ex); return
        if p["deal_id"] in ids: return
        lv = self.eng.exit_levels(name, [dict(deal_id=p["deal_id"], px=p["px"], sz=p["sz"])])
        self.book(name, lv.get(p["deal_id"], np.nan), "ig_stop_or_limit")

    def close(self, name, how):
        p = self.st["pos"][name]; px = np.nan
        if self.dry or p["deal_id"] == "dry": px = float(self.eng.bars15[name].close.iloc[-1])
        else:
            try:
                r = self.ig.close_open_position(deal_id=p["deal_id"], direction="SELL" if p["side"] == 1 else "BUY", epic=None, expiry=None, level=None,
                                                order_type="MARKET", quote_id=None, size=p["sz"])
                px = float(r.get("level") or np.nan)
            except Exception as ex:
                log(name, "close:", ex); self.sync(name); return
        self.book(name, px, how)

    def book(self, name, px, how):
        p = self.st["pos"].pop(name); pts = p["side"] * (px - p["px"]) if np.isfinite(px) else np.nan
        gbp = pts * p["sz"] if np.isfinite(pts) else np.nan
        hdr = not os.path.exists(TRADES)
        with open(TRADES, "a", newline="") as f:
            w = csv.writer(f)
            if hdr: w.writerow(["market", "side", "opened_bar", "closed", "entry", "exit", "size", "pts", "gbp", "how"])
            w.writerow([name, p["side"], p["bar"], utcnow().isoformat(timespec="seconds"), p["px"], px, p["sz"], f"{pts:.1f}", f"{gbp:.2f}", how])
        if self.beq and np.isfinite(gbp): self.beq.add(gbp, "spike")
        log(name, f"CLOSED ({how}) {pts:+.1f} pts, {gbp:+.2f} {self.ccy}"); self.save()

    def end_of_job(self):
        for name in list(self.st["pos"]):
            log(name, "job ending — closing the spike position (intraday engine)"); self.close(name, "job_end")
        self.save()

    def save(self): json.dump(self.st, open(STATE, "w"), indent=1)
