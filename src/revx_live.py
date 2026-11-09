"""
REVOLUT X LIVE RUNNER v2 — Range long book with RESTING orders (doc 194; CAP-021 as amended 5 Nov 2026).
v1 (bought after each bar closed, mirroring the paper engine) lost 3.5% on the 1-9 Nov replay while the paper book made +6.9%: it chased the
bounce and paid taker fees both ways. v2 trades the way the edge actually works — orders already resting when the dip arrives:

Every 15 minutes, using only bars that have CLOSED (no look-ahead):
  1. fills: check the orders that rested through the bar that just closed (live: ask Revolut X; dry: the bar's low/high touched them);
  2. exits (paperbook6 Range v3 rules, long side): stop 5% under average cost; break (close beyond the band +/-1.5 ATR); cap 48 bars;
     regime off -> sell at market (IOC through the price, 0.09% taker);
  3. orders for the NEXT bar from this bar's indicators: a sell at the mid (EMA20) for everything held (post-only, 0% maker);
     buy rungs at lower band + (0.30, 0.05, -0.25, -0.55) x ATR sized (15/25/30/30%) of the episode budget, when the regime allows and
     the 6h cool-down is over. New episodes: budget 10% of book equity, at most 10 coins open; cash reserved nearest-rung first.
  4. book down 15% from its start -> no new episodes; HALT recorded for DK (CAP-021 5 Nov).
Modes: dry  = no orders; fills simulated on the next bar (strictly through the price), state in runs/revx_dry/
       live = DK's Revolut X account; only through the workflow when DK has set REVX_LIVE_ENABLED=true; state in runs/revx_live/.
Universe: the 26 registered coins on Revolut X, USD pairs (ZEC not listed). Keys: DK's GitHub secrets only (src/revx_client.py).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, time, math, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); os.environ.setdefault("QLAB_ROOT", ROOT)
import paperbook14 as B, paperbook6 as P

MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
assert MODE in ("dry", "live")
OUT = f"{ROOT}/runs/revx_{MODE}"; os.makedirs(OUT, exist_ok=True)
STATE, TRADES = f"{OUT}/state.json", f"{OUT}/trades.csv"
FRAC, MAXOPEN, STOP_BOOK = 0.10, 10, -0.15
TK, SL = 0.0009, 0.0010
STOP = P.MARGIN_STOP / P.LEV   # 5% under average cost


def now(): return pd.Timestamp.now(tz="UTC")
def log(*a): print(dt.datetime.utcnow().strftime("%H:%M:%S"), *a, flush=True)


def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"start": str(now().floor("15min")), "cash0": None, "cash": None, "pos": {}, "orders": [], "cool": {}, "halt": None}


def save(st): json.dump(st, open(STATE, "w"), indent=1, default=str)


def trade_row(t, coin, side, qty, px, why, fee):
    hdr = not os.path.exists(TRADES)
    with open(TRADES, "a") as f:
        if hdr: f.write("time,coin,side,qty,price,usd,fee,why\n")
        f.write(f"{t},{coin},{side},{qty:.8f},{px:.8g},{qty*px:.2f},{fee:.4f},{why}\n")


class Exec:
    """dry: simulated cash and fills. live: Revolut X."""
    def __init__(self, st):
        self.st = st
        if MODE == "live":
            from revx_client import RevX
            self.rx = RevX()
            f = f"{ROOT}/runs/revx_live/pairs.json"
            self.cfg = json.load(open(f)) if os.path.exists(f) else self.rx.pairs()

    def cash(self):
        if MODE == "dry": return self.st["cash"]
        bal = self.rx.balances(); rows = bal if isinstance(bal, list) else bal.get("data", [])
        return sum(float(b.get("total") or b.get("available") or 0) for b in rows if b.get("currency") == "USD")

    def _fmt(self, x, step):
        dp = max(0, -int(math.floor(math.log10(step)))); v = math.floor(x / step + 1e-9) * step
        return f"{v:.{dp}f}", v

    def _px(self, p):
        dp = min(8, max(2, 5 - int(math.floor(math.log10(p)))))
        return f"{p:.{dp}f}"

    def place_limit(self, coin, side, qty, price):
        """returns an order record (dict) or None"""
        if MODE == "dry": return {"id": f"dry-{coin}-{side}-{price:.8g}", "coin": coin, "side": side, "qty": qty, "price": price}
        c = self.cfg.get(f"{coin}/USD", {}); bs = float(c.get("base_step", "0.000001"))
        q, qv = self._fmt(qty, bs)
        if qv <= 0 or qv * price < float(c.get("min_order_size_quote", "0.1")) * 1.5: return None
        try:
            r = self.rx.place(f"{coin}-USD", side, base_size=q, price=self._px(price), tif="gtc", post_only=True)
        except Exception as e:
            log(f"  {coin} {side} limit refused: {str(e)[:160]}"); return None
        d = r.get("data", r); return {"id": d.get("venue_order_id") or d.get("id"), "coin": coin, "side": side, "qty": qv, "price": price}

    def market(self, coin, side, qty, ref):
        """IOC through the price. returns (filled qty, avg price, fee usd)"""
        if MODE == "dry":
            fpx = ref * (1 - SL) if side == "sell" else ref * (1 + SL)
            fee = qty * fpx * TK
            self.st["cash"] += (qty * fpx - fee) if side == "sell" else -(qty * fpx + fee)
            return qty, fpx, fee
        c = self.cfg.get(f"{coin}/USD", {}); bs = float(c.get("base_step", "0.000001")); q, qv = self._fmt(qty, bs)
        if qv * ref < 0.5: return 0.0, 0.0, 0.0
        lim = ref * (0.99 if side == "sell" else 1.01)
        try: r = self.rx.place(f"{coin}-USD", side, base_size=q, price=self._px(lim), tif="ioc")
        except Exception as e: log(f"  {coin} {side} IOC refused: {str(e)[:160]}"); return 0.0, 0.0, 0.0
        d = r.get("data", r); fq, fp = self.status(d.get("venue_order_id") or d.get("id"), wait=True)
        return fq, fp, fq * fp * TK

    def status(self, oid, wait=False):
        for k in range(6 if wait else 1):
            if wait: time.sleep(1.5)
            o = self.rx.order(oid); o = o.get("data", o)
            if not wait or o.get("status") in ("filled", "cancelled", "rejected", "partially_filled", "replaced"):
                return float(o.get("filled_quantity") or 0), float(o.get("average_fill_price") or 0)
        return 0.0, 0.0

    def settle(self, o, bar):
        """how much of a resting order filled during `bar` (dry) / so far (live); cancels the rest (live). returns (qty, px)"""
        if MODE == "dry":
            hit = (bar.low < o["price"]) if o["side"] == "buy" else (bar.high > o["price"])
            if not hit: return 0.0, 0.0
            v = o["qty"] * o["price"]; self.st["cash"] += v if o["side"] == "sell" else -v
            return o["qty"], o["price"]
        fq, fp = self.status(o["id"])
        if fq < o["qty"] - 1e-12:
            try: self.rx.cancel(o["id"])
            except Exception: pass
            fq, fp = self.status(o["id"])   # a fill may land between the read and the cancel
        return fq, fp


def main():
    st = load(); ex = Exec(st); t = now()
    if MODE == "dry" and st["cash"] is None: st["cash"] = 500.0 * 1.27   # dry: £500 at ~1.27 $/£
    U = [s for s in json.load(open(f"{ROOT}/runs/range_universe.json"))["registered_universe"] if s != "ZECUSD"]
    bars = {}
    for s in U:
        b = B.refresh(s)
        if MODE == "live": time.sleep(1.0)
        if len(b) < 300 or b.index.max() < t - pd.Timedelta(minutes=45): log(f"{s}: no fresh candles — skipped"); continue
        bars[s[:-3]] = b[["open", "high", "low", "close"]].astype(float)

    # 1. fills from the orders that rested through the last bar
    for o in st["orders"]:
        c = o["coin"]
        if c not in bars: continue
        b = bars[c]; placed = pd.Timestamp(o["placed"]); nb = b[b.index >= placed]
        if MODE == "dry" and not len(nb): continue
        q, px = ex.settle(o, nb.iloc[0] if len(nb) else None)
        if q <= 0: continue
        p = st["pos"].setdefault(c, None)
        if o["side"] == "buy":
            if p is None: p = st["pos"][c] = {"open": str(placed), "qty": 0.0, "cost": 0.0, "tried": [], "budget": o["budget"]}
            p["qty"] += q; p["cost"] += q * px; p["tried"] = sorted(set(p["tried"]) | {o["rung"]})
            trade_row(t, c, "buy", q, px, f"rung{o['rung']}", 0.0); log(f"{c}: rung {o['rung']} filled — bought ${q*px:.2f} at {px:.6g}")
        elif p:
            avg = p["cost"] / p["qty"] if p["qty"] else px
            p["cost"] -= avg * min(q, p["qty"]); p["qty"] = max(0.0, p["qty"] - q)
            trade_row(t, c, "sell", q, px, "mid", 0.0); log(f"{c}: sold ${q*px:.2f} at the mid {px:.6g}")
    st["orders"] = []
    if MODE == "live" and st["cash0"] is None:
        c0 = ex.cash()
        if c0 < 50: log(f"live: only ${c0:.2f} on Revolut X — nothing to trade with yet"); save(st); return
        st["cash0"] = c0; st["start"] = str(t); log(f"live book starts with ${c0:.2f}")
    if st["cash0"] is None: st["cash0"] = st["cash"]

    # 2. exits on the bar that just closed
    ind = {c: P.indicators(b, c + "USD") for c, b in bars.items()}
    for c, p in list(st["pos"].items()):
        if p is None or c not in bars: st["pos"].pop(c, None); continue
        b = bars[c]; ema, lo_b, hi_b, a, allow = ind[c]; i = len(b) - 1; C, L = b.close.values, b.low.values
        if p["qty"] * C[i] < 0.5:
            st["pos"].pop(c); st["cool"][c] = str(b.index[i]); log(f"{c}: episode closed at the mid"); continue
        avg = p["cost"] / p["qty"]
        why = ("stop" if L[i] <= avg * (1 - STOP) else "break" if (C[i] < lo_b[i] - 1.5 * a[i] or C[i] > hi_b[i] + 1.5 * a[i])
               else "cap" if (b.index[i] - pd.Timestamp(p["open"])) >= pd.Timedelta(minutes=15 * P.CAP_BARS) else "regime" if not allow[i] else None)
        if why:
            ref = avg * (1 - STOP) if why == "stop" and MODE == "dry" else C[i]
            q, px, fee = ex.market(c, "sell", p["qty"], ref)
            if q > 0:
                trade_row(t, c, "sell", q, px, why, fee); log(f"{c}: {why} — sold ${q*px:.2f} ({100*(px/avg-1):+.2f}% on cost)")
                p["qty"] -= q; p["cost"] -= avg * q
            if p["qty"] * C[i] < 0.5: st["pos"].pop(c); st["cool"][c] = str(b.index[i])

    # equity and the book stop
    px_now = {c: float(b.close.iloc[-1]) for c, b in bars.items()}
    cash = ex.cash(); held = sum(p["qty"] * px_now.get(c, 0) for c, p in st["pos"].items()); eq = cash + held
    if eq / st["cash0"] - 1 <= STOP_BOOK and not st["halt"]:
        st["halt"] = f"{t}: book {100*(eq/st['cash0']-1):.1f}% from start — no new episodes; DK to review (CAP-021)"; log("HALT:", st["halt"])

    # 3. orders for the next bar
    want = []
    for c, b in bars.items():
        ema, lo_b, hi_b, a, allow = ind[c]; i = len(b) - 1
        if not (np.isfinite(a[i]) and a[i] > 0): continue
        p = st["pos"].get(c)
        if p and p["qty"] > 0: want.append((-1, c, "sell", p["qty"], float(ema[i]), None, None))
        if not allow[i]: continue
        ct = st["cool"].get(c)
        if ct and b.index[i] < pd.Timestamp(ct) + pd.Timedelta(hours=P.COOLDOWN_H): continue
        if p is None and (st["halt"] or len(st["pos"]) >= MAXOPEN): continue
        budget = p["budget"] if p else FRAC * eq
        for k, (frac, off) in enumerate(P.BID):
            if p and k in p["tried"]: continue
            price = float(lo_b[i] + off * a[i])
            if price <= 0: continue
            want.append(((b.close.values[i] - price) / a[i], c, "buy", budget * frac / price, price, k, budget))
    want.sort(key=lambda x: x[0])
    free = cash; newc = set()
    for dist, c, side, qty, price, k, budget in want:
        if side == "buy":
            if qty * price > free: continue
            if c not in st["pos"] and c not in newc and len(st["pos"]) + len(newc) >= MAXOPEN: continue
        o = ex.place_limit(c, side, qty, price)
        if not o: continue
        o.update(placed=str(t.floor("15min")), rung=k, budget=budget); st["orders"].append(o)
        if side == "buy": free -= qty * price; newc.add(c) if c not in st["pos"] else None

    st["last"] = {"time": str(t), "cash": round(cash, 2), "coins": round(held, 2), "equity": round(eq, 2), "open": len(st["pos"]),
                  "orders": len(st["orders"])}
    save(st)
    log(f"[{MODE}] equity ${eq:.2f} (cash ${cash:.2f} + coins ${held:.2f}) {100*(eq/st['cash0']-1):+.2f}% | open: {', '.join(st['pos']) or '-'} | "
        f"{sum(o['side']=='buy' for o in st['orders'])} bids, {sum(o['side']=='sell' for o in st['orders'])} sells resting")


if __name__ == "__main__": main()
