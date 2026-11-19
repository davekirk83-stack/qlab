"""IG DEMO options book: weekly US 500 short put spread (volatility risk premium), doc 245.
DK 19 Nov 2026: "But we technically can afford it" -> Claude proposed 3-4 weeks on the IG demo at the live size first; DK: "Yes".
DEMO ONLY: refuses to run unless IG_MODE is demo.

Rules (from src/vrp_spread_test.py, adapted to IG's quoted strikes):
  - Friday, about 1 hour before the US cash close: sell the weekly US 500 put whose strike is nearest S * (1 - VIX/100 * sqrt(5/252))
    (~16 delta), and buy the put WIDTH points lower (default 50). Expiry: the following Friday's weekly option.
  - Size: IG's minimum bet on both legs. Held to expiry (IG settles), no stop.
  - Every fill is logged with IG's actual bid/offer next to the Black-Scholes model credit, to measure how much IG's spread eats.

Modes:
  scan    list the option markets IG returns for US 500 searches (epics, names, expiries, bid/offer, min bet) -> runs/ig_options/scan.json
  open    place this week's spread (Friday job)
  status  log open option positions and their running P&L
"""
import os, sys, json, re, math, datetime as dt
MODE = os.environ.get("IG_MODE", "demo").strip().lower()
if MODE != "demo": raise SystemExit("ig_options_vrp is DEMO ONLY (IG_MODE must be demo)")
OUT = "runs/ig_options"; os.makedirs(OUT, exist_ok=True)
WIDTH = float(os.environ.get("VRP_WIDTH", "50"))
UNDERLYING = "IX.D.SPTRD.DAILY.IP"   # US 500 cash (spread bet)
def utcnow(): return dt.datetime.now(dt.timezone.utc)
def log(*a):
    line = f"{utcnow():%Y-%m-%d %H:%M:%S}Z " + " ".join(str(x) for x in a); print(line, flush=True)
    open(f"{OUT}/log.txt", "a").write(line + "\n")
N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs_put(S, K, T, v):
    if v <= 0 or T <= 0: return max(0.0, K - S)
    d1 = (math.log(S / K) + 0.5 * v * v * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return K * N(-d2) - S * N(-d1)

def connect():
    from trading_ig import IGService
    u, p, key = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
    ig = IGService(u, p, key, acc_type="demo", return_dataframe=False); ig.create_session()
    sb = [a for a in ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"]
    if not sb: raise RuntimeError("no SPREADBET account on the demo login")
    try: ig.switch_account(sb[0]["accountId"], True)
    except Exception as e:
        if "same" not in str(e).lower(): log("switch_account:", e)
    return ig

def search(ig, terms):
    seen = {}
    for t in terms:
        try: res = ig.search_markets(t)
        except Exception as e: log("search", t, e); continue
        for m in (res.get("markets", res) if isinstance(res, dict) else res) or []:
            seen[m["epic"]] = m
    return list(seen.values())

def option_markets(ig):
    ms = search(ig, ["US 500 put", "US 500 weekly", "Weekly US 500", "US 500 option", "US 500 PUT", "SPX weekly put"])
    return [m for m in ms if "OPT" in str(m.get("instrumentType", "")).upper() or "PUT" in m.get("instrumentName", "").upper()]

def scan(ig):
    ms = option_markets(ig)
    log(f"scan: {len(ms)} option-like markets")
    out = []
    for m in ms[:200]:
        out.append({k: m.get(k) for k in ("epic", "instrumentName", "instrumentType", "expiry", "bid", "offer", "marketStatus")})
    # dealing rules for a few
    for m in out[:6]:
        try:
            d = ig.fetch_market_by_epic(m["epic"])
            m["minDealSize"] = d["dealingRules"]["minDealSize"]; m["lotSize"] = d["instrument"].get("lotSize")
            m["valueOfOnePip"] = d["instrument"].get("valueOfOnePip"); m["currencies"] = [c["code"] for c in d["instrument"]["currencies"]]
        except Exception as e: m["detail_error"] = str(e)
    json.dump(out, open(f"{OUT}/scan.json", "w"), indent=1, default=str)
    for m in out[:60]: log(m.get("epic"), "|", m.get("instrumentName"), "|", m.get("expiry"), "|", m.get("bid"), "/", m.get("offer"), "|", m.get("minDealSize", ""))

def nav(ig):
    """Walk IG's market navigation to the US 500 option nodes (search only returns a few strikes)."""
    import time
    top = ig.fetch_top_level_navigation_nodes()
    nodes = top.get("nodes", []) if isinstance(top, dict) else top
    log("top nodes:", [n["name"] for n in nodes])
    found = []
    def walk(node_id, path, depth):
        if depth > 4: return
        time.sleep(1.2)
        try: r = ig.fetch_sub_nodes_by_node(node_id)
        except Exception as e: log("node", path, e); return
        subs = r.get("nodes", []) or []; mkts = r.get("markets", []) or []
        if mkts and ("500" in path or "S&P" in path or "SPX" in path):
            log("NODE", path, f"{len(mkts)} markets; e.g.", [(m["epic"], m["instrumentName"], m.get("expiry")) for m in mkts[:4]])
            found.append({"path": path, "id": node_id, "markets": [{k: m.get(k) for k in ("epic", "instrumentName", "expiry", "bid", "offer")} for m in mkts]})
        for n in subs:
            nm = n["name"]
            if depth == 0 and "option" not in nm.lower(): continue
            if depth >= 1 and not any(k in nm.upper() for k in ("US 500", "S&P", "SPX", "WEEKLY", "DAILY", "INDICES", "INDEX", "500")): continue
            walk(n["id"], path + " > " + nm, depth + 1)
    for n in nodes:
        if "option" in n["name"].lower(): walk(n["id"], n["name"], 1)
    json.dump(found, open(f"{OUT}/nav.json", "w"), indent=1, default=str)
    log(f"nav: {len(found)} US 500 option nodes saved to {OUT}/nav.json")

def strike_of(name):
    m = re.search(r"(\d{3,5}(?:\.\d+)?)\s*(?:PUT|P\b)", name.upper()) or re.search(r"(\d{4,5}(?:\.\d+)?)", name)
    return float(m.group(1)) if m else None

def vix_now():
    try:
        import yfinance as yf
        return float(yf.Ticker("^VIX").history(period="5d").Close.dropna().iloc[-1])
    except Exception as e:
        log("VIX fetch failed:", e); return None

def place(ig, epic, direction, size):
    d = ig.fetch_market_by_epic(epic); cc = [c["code"] for c in d["instrument"]["currencies"]]
    return ig.create_open_position(currency_code="GBP" if "GBP" in cc else cc[0], direction=direction, epic=epic, expiry=d["instrument"]["expiry"],
                                   force_open=True, guaranteed_stop=False, level=None, limit_distance=None, limit_level=None, order_type="MARKET",
                                   quote_id=None, size=size, stop_distance=None, stop_level=None, trailing_stop=False, trailing_stop_increment=None), d

def open_week(ig, dry):
    tag = f"{OUT}/opened_{utcnow():%G-W%V}.json"
    if os.path.exists(tag): log("already opened this week:", tag); return
    u = ig.fetch_market_by_epic(UNDERLYING)["snapshot"]; S = (float(u["bid"]) + float(u["offer"])) / 2
    V = vix_now()
    if not V: log("no VIX -> no trade"); return
    T = 5 / 252; target = S * (1 - V / 100 * math.sqrt(T))
    puts = [m for m in option_markets(ig) if "PUT" in m.get("instrumentName", "").upper()]
    # choose the expiry about a week out: the latest expiry within 9 days
    def exp_days(m):
        e = str(m.get("expiry") or "")
        for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d"):
            try: return (dt.datetime.strptime(e, fmt).date() - utcnow().date()).days
            except ValueError: pass
        return None
    cands = [(exp_days(m), m) for m in puts]; cands = [(d, m) for d, m in cands if d is not None and 3 <= d <= 9]
    if not cands: log("no weekly put with 3-9 days to expiry found; run 'scan' and check names/expiries"); return
    dmax = max(d for d, _ in cands); week = [m for d, m in cands if d == dmax]
    strikes = sorted((strike_of(m["instrumentName"]), m) for m in week if strike_of(m["instrumentName"]))
    if not strikes: log("could not parse strikes from names, e.g.", week[0]["instrumentName"]); return
    short = min(strikes, key=lambda x: abs(x[0] - target))
    long_ = min(strikes, key=lambda x: abs(x[0] - (short[0] - WIDTH)))
    if long_[0] >= short[0]: log("no lower strike for the long wing"); return
    Ts = dmax / 365; model = bs_put(S, short[0], Ts, V / 100 + .02) - bs_put(S, long_[0], Ts, V / 100 + .04)
    sm = ig.fetch_market_by_epic(short[1]["epic"]); lm = ig.fetch_market_by_epic(long_[1]["epic"])
    size = max(float(sm["dealingRules"]["minDealSize"]["value"]), float(lm["dealingRules"]["minDealSize"]["value"]))
    sb, so = float(sm["snapshot"]["bid"]), float(sm["snapshot"]["offer"]); lb, lo = float(lm["snapshot"]["bid"]), float(lm["snapshot"]["offer"])
    ig_credit = sb - lo; width = short[0] - long_[0]
    rec = dict(time=str(utcnow()), S=S, VIX=V, target=round(target, 1), short=short[1]["epic"], short_strike=short[0], long=long_[1]["epic"], long_strike=long_[0],
               days=dmax, size=size, short_bid_offer=[sb, so], long_bid_offer=[lb, lo], ig_credit=ig_credit, model_credit=round(model, 2),
               width=width, max_loss_pts=round(width - ig_credit, 2), max_loss_gbp=round((width - ig_credit) * size, 2), dry=dry)
    log("PLAN", json.dumps(rec))
    if ig_credit <= 0: log("IG credit <= 0 -> skip"); json.dump(rec, open(tag, "w"), indent=1); return
    if dry: log("dry run: no orders"); return
    r1, _ = place(ig, short[1]["epic"], "SELL", size); log("SELL short put:", r1.get("dealStatus"), r1.get("reason"), r1.get("level"))
    if r1.get("dealStatus") != "ACCEPTED": log("short leg rejected -> no long leg"); return
    r2, _ = place(ig, long_[1]["epic"], "BUY", size); log("BUY long put:", r2.get("dealStatus"), r2.get("reason"), r2.get("level"))
    rec.update(short_fill=r1.get("level"), long_fill=r2.get("level"), short_deal=r1.get("dealId"), long_deal=r2.get("dealId"))
    json.dump(rec, open(tag, "w"), indent=1)
    with open(f"{OUT}/trades.jsonl", "a") as f: f.write(json.dumps(rec) + "\n")

def status(ig):
    ps = ig.fetch_open_positions()["positions"]
    opt = [p for p in ps if "PUT" in p["market"]["instrumentName"].upper() or "OPT" in str(p["market"].get("instrumentType", "")).upper()]
    tot = 0.0
    for p in opt:
        pos, mk = p["position"], p["market"]; bid, off = float(mk["bid"] or 0), float(mk["offer"] or 0)
        pl = (bid - float(pos["level"])) * float(pos["size"]) if pos["direction"] == "BUY" else (float(pos["level"]) - off) * float(pos["size"])
        tot += pl; log("open", mk["instrumentName"], mk.get("expiry"), pos["direction"], pos["size"], "@", pos["level"], "now", bid, "/", off, f"P&L £{pl:+.2f}")
    log(f"options open: {len(opt)} legs, running P&L £{tot:+.2f}")

if __name__ == "__main__":
    job = sys.argv[1] if len(sys.argv) > 1 else "scan"; dry = "--dry" in sys.argv
    ig = connect()
    {"scan": lambda: scan(ig), "nav": lambda: nav(ig), "open": lambda: open_week(ig, dry), "status": lambda: status(ig)}[job]()
