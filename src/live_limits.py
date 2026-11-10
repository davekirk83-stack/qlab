"""Doc 212 — the live money rules in ONE place (config/live_pot.json), shared by every live runner on DK's IG account.
Scales with the pot and the number of books: all limits are fractions of the pot; with compound=true the pot used for sizing and caps
is pot_gbp + the whole account's change since live trading started (all books together), so wins grow the stakes and losses shrink them.
DK's deposits/withdrawals (IG DEPOSIT/WITHDRAWAL transactions) are never counted as profit or loss; with deposits_raise_pot=true a deposit
raises the pot (and every limit with it) automatically (DK 10 Nov 07:53: "I may add funding where possible").
- risk_per_trade: max loss at the stop on any one trade, as a share of the (sized) pot; a book's 'share' scales its sizing pot.
- exposure_x: total open stake x price over EVERY position on the account <= exposure_x * pot.
- day_stop / floor: no new entries once the whole account is down day_stop * pot today, or floor * pot_gbp from the start (back to paper).
- index_risk_cap: total risk on the five equity indices at once (they move together)."""
import os, json, datetime as dt
CFG = os.path.join(os.environ.get("QLAB_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "live_pot.json")
C = json.load(open(CFG))
POT, RISK, EXPO, DAY_STOP, FLOOR, IDX_CAP = (float(C[k]) for k in ("pot_gbp", "risk_per_trade", "exposure_x", "day_stop", "floor", "index_risk_cap"))
def _now(): return dt.datetime.now(dt.timezone.utc)   # replaceable in replays
def share(book): return float(C["books"].get(book, {}).get("share", 1.0))
def engines(book): return list(C["books"].get(book, {}).get("engines", []))

def account_equity(ig):
    """IG spread-bet account balance + open P&L (only ever used as a CHANGE from a baseline; never printed on live)."""
    a = [a for a in ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"][0]["balance"]
    return float(a["balance"]) + float(a.get("profitLoss") or 0.0)
def account_notional(ig):
    return float(sum(float(x["position"]["size"]) * float(x["position"]["level"]) for x in ig.fetch_open_positions()["positions"]))

def _amt(x):
    try: return float(str(x).replace("£", "").replace("$", "").replace("€", "").replace(",", "").replace("E", "").strip() or 0)
    except Exception: return 0.0
def transfers(ig, since):
    """Net cash DK paid in (+) or took out (-) since `since` (ISO date): IG DEPOSIT / WITHDRAWAL transactions. Never trading P&L."""
    now = _now(); tot = 0.0
    for kind, sign in (("DEPOSIT", 1.0), ("WITHDRAWAL", -1.0)):
        tx = ig.fetch_transaction_history(trans_type=kind, from_date=f"{since}T00:00:00", to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=500)
        rows = tx.get("transactions", tx) if isinstance(tx, dict) else tx
        tot += sign * sum(abs(_amt(t.get("profitAndLoss") or t.get("amount"))) for t in (rows or []))
    return tot

def tier(pot):
    """The risk_tiers row for this pot size (aggressive early, less risk as the pot grows)."""
    rows = sorted(C.get("risk_tiers", {}).get("rows", [{"from_pot": 0}]), key=lambda r: r["from_pot"]); row = rows[0]
    for r in rows:
        if pot >= r["from_pot"]: row = r
    return row
def tps_stop(pot):
    r = tier(pot); return float(r["tps_stop_gbp"]) if "tps_stop_gbp" in r else float(r.get("tps_stop_frac", 0.05)) * pot
def tps_pnl(state=None):
    """TPS book P&L (realised + last open) and today's change, from the daily runner's state — kept OUT of the other books' day stop/floor."""
    try:
        st = state if state is not None else json.load(open(os.path.join(os.path.dirname(os.path.dirname(CFG)), "runs", "ig_daily_live", "state.json")))
        t = st.get("tps", {}); tot = float(t.get("realised", 0)) + float(t.get("open", 0))
        return tot, tot - float(t.get("day_start", tot)) if t.get("day") == _now().date().isoformat() else 0.0
    except FileNotFoundError: return 0.0, 0.0

class Pot:
    """Account-wide state for one runner (baselines kept in that runner's own state dict, so runners never write each other's files)."""
    def __init__(self, ig, state, daily_state=None):
        self.ig, self.s, self.daily = ig, state.setdefault("pot", {}), daily_state
    def refresh(self):
        acc = account_equity(self.ig); today = _now().date().isoformat()
        self.s.setdefault("acc_start", acc); self.s.setdefault("start_date", today)
        cash = transfers(self.ig, self.s["start_date"])                 # DK's deposits/withdrawals are NOT trading results
        if self.s.get("day") != today: self.s["day"], self.s["acc_day"], self.s["cash_day"] = today, acc, cash
        self.s["acc"], self.s["cash"] = acc, cash; return self
    @property
    def change(self): return self.s["acc"] - self.s["acc_start"] - self.s["cash"]          # trading P&L of all books since the start
    @property
    def today(self): return self.s["acc"] - self.s["acc_day"] - (self.s["cash"] - self.s["cash_day"])   # trading P&L today
    @property
    def base(self): return POT + (self.s["cash"] if C.get("deposits_raise_pot", True) else 0.0)  # pot_gbp + DK's net deposits
    @property
    def pot(self): return self.base + (self.change if C.get("compound", True) else 0.0)
    def entries_ok(self):
        """Day stop / floor for every book EXCEPT TPS, which has its own stop (tps_stop): TPS P&L is taken out first."""
        tt, td = tps_pnl(self.daily) if not C.get("risk_tiers", {}).get("tps_in_floor", False) else (0.0, 0.0)
        ch, today = self.change - tt, self.today - td
        if ch < -FLOOR * self.base: return False, f"books (ex TPS) down £{-ch:.2f} since start (-{FLOOR:.0%} of £{self.base:.0f}): back to paper"
        if today < -DAY_STOP * (self.pot - self.today): return False, f"books (ex TPS) down £{-today:.2f} today (-{DAY_STOP:.0%}): no new entries today"
        return True, ""
    def _old_entries_ok(self):
        if self.change < -FLOOR * self.base: return False, f"books down £{-self.change:.2f} since start (-{FLOOR:.0%} of £{self.base:.0f}): back to paper"
        if self.today < -DAY_STOP * (self.pot - self.today): return False, f"books down £{-self.today:.2f} today (-{DAY_STOP:.0%}): no new entries today"
        return True, ""
    def room(self): return EXPO * self.pot - account_notional(self.ig)
