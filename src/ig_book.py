"""Book 13 rehearsal on the IG DEMO (doc 169/171, DK 1 Nov "Yes"): the demo account trades as if it held only the £500 combined book.
BookEquity keeps that virtual equity in runs/ig_demo/book_eq.json, independent of the demo account's real (large) balance:
  - every closed Ignition trade, range episode and news-fade trade adds its £ P&L;
  - rule 186: size from CURRENT book equity; risk halved while equity is >10% below its high, restored at a new high;
  - a day whose realised loss reaches -4% of the day's opening equity takes no further entries (doc 169 pool rule);
  - total open exposure (stake x price over all positions) never above 5 x book equity (DK 1 Nov: 5x maximum).
DEMO ONLY (CAP-021 as amended 20 Oct). Nothing here can reach a live account."""
import os, json, datetime as dt
OUT = "runs/ig_demo"; F = f"{OUT}/book_eq.json"
START_EQ = float(os.environ.get("IG_BOOK_START_EQ", "500"))
R_IGN, RNG_MARGIN, R_NEWS, MARGIN = 0.02, 0.15, 0.01, 0.05
MAX_LEV = 5.0   # DK 1 Nov 16:02: "happy with 2x but if you are confident in using 5x sensibly then that's fine (but no more)"

class BookEquity:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.s = json.load(open(F)) if os.path.exists(F) else {"start": dt.date.today().isoformat(), "eq": START_EQ, "hi": START_EQ, "day": None, "day_open": START_EQ, "log": []}
    @property
    def eq(self): return float(self.s["eq"])
    @property
    def k(self): return 0.5 if self.s["eq"] < 0.9 * self.s["hi"] else 1.0
    def _roll(self):
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        if self.s.get("day") != today: self.s["day"] = today; self.s["day_open"] = self.s["eq"]; self.save()
    def day_ok(self):
        self._roll(); return self.s["eq"] > self.s["day_open"] * 0.96
    def add(self, gbp, src):
        if gbp is None or gbp != gbp: return
        self._roll(); self.s["eq"] = round(self.s["eq"] + float(gbp), 4); self.s["hi"] = max(self.s["hi"], self.s["eq"])
        self.s["log"] = (self.s.get("log", []) + [[dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), src, round(float(gbp), 2), self.s["eq"]]])[-500:]
        self.save()
    def ign_size(self, stop_pts, min_size):
        return max(min_size, round(self.eq * R_IGN * self.k / max(stop_pts, 1.0), 2))
    def news_size(self, risk_pts, min_size):
        return max(min_size, round(self.eq * R_NEWS * self.k / max(risk_pts, 1.0), 2))
    def range_full(self, price):
        """full-ladder £/pt so that the whole ladder's notional is 15% of equity as margin at 5%"""
        return self.eq * RNG_MARGIN * self.k / MARGIN / max(price, 1.0)
    def cap(self, size, price, open_notional, min_size):
        """Scale a new position so total open exposure stays <= 5 x book equity; 0 if what is left is under a quarter of the size or the minimum."""
        room = MAX_LEV * self.eq - open_notional
        if room <= 0 or price <= 0: return 0.0
        s = min(size, round(room / price, 2))
        return s if (s >= min_size and s >= 0.25 * size) else 0.0
    def save(self): json.dump(self.s, open(F, "w"), indent=1)
