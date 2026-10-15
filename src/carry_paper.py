"""
FUNDING CARRY — forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance. This file reads a public API and writes JSON.

WHAT IT DOES
------------
Each month it records, IN ADVANCE, the coins the rule selects, then measures the
funding those coins actually paid over the following month. Selection uses only
the previous 30 days, so there is no lookahead — and because the pick is written
down before the month starts, it cannot be revised afterwards.

THE RULE (fixed at registration, 2026-10-14)
    universe   top 40 perps by open-interest notional on Hyperliquid
    exclude    any coin without a liquid spot market to hedge against
               (checked against Binance and Coinbase; XMR currently excluded)
    rank       mean funding over the previous 30 days
    select     top 12 with positive trailing funding
    hold       one month, delta-neutral (short perp, long spot)
    cost       20bp per rebalance (two legs, 10bp round trip each)

WHY 12 AND NOT 5
    N=5 showed a higher backtested CAGR (+11.4% vs +8.5%) but the backtest covers
    13 months with no crisis, so the apparent precision of the top of the ranking
    is not trustworthy. 12 is the more diversified choice and costs ~3pp of a
    number I do not believe anyway.

KILL CRITERION (pre-registered, not amendable mid-run)
    minimum evidence   12 completed months
    fail               mean monthly funding <= 0 net of costs
    early kill         any month worse than -5%, or two consecutive negative
                       months, or the hedge becoming unavailable for >3 of the 12
    not evidence       a good month; the first six months; the absence of a crisis
"""
import os, json, time, datetime as dt
import numpy as np, pandas as pd
import requests

API = "https://api.hyperliquid.xyz/info"
STATE = "/home/claude/qlab/runs/paper/carry.json"
H = 3600 * 1000
N_SELECT = 12
UNIVERSE_SIZE = 40
COST_PER_REBALANCE = 0.0020

REGISTERED = {
    "registered_on": "2026-10-14",
    "rule": "top 12 hedgeable perps by previous-30-day mean funding, held one month, "
            "delta-neutral, 20bp rebalance cost",
    "minimum_evidence_months": 12,
    "fail": "mean monthly funding <= 0 net of costs over 12 months",
    "early_kill": ["any month worse than -5%",
                   "two consecutive negative months",
                   "hedge unavailable for more than 3 of the 12 selections"],
    "not_evidence": ["a good month", "the first six months",
                     "the absence of a crisis in the sample"],
    "backtest_for_reference": {
        "months": 13, "cagr": 0.0854, "maxdd": 0.0, "sharpe": 5.09,
        "caveat": "Sharpe 5 and zero drawdown is what carry looks like before its "
                  "tail risk appears. Treat as a warning, not an expectation.",
    },
}


def post(body, tries=4):
    for _ in range(tries):
        try:
            r = requests.post(API, json=body, timeout=45)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1)
    return None


def universe():
    meta = post({"type": "metaAndAssetCtxs"})
    if not meta:
        return []
    out = []
    for u, c in zip(meta[0]["universe"], meta[1]):
        try:
            out.append((float(c.get("openInterest", 0)) * float(c.get("markPx", 0)),
                        u["name"]))
        except Exception:
            pass
    out.sort(reverse=True)
    return [n for _, n in out[:UNIVERSE_SIZE]]


def hedgeable():
    spot = set()
    try:
        d = requests.get("https://data-api.binance.vision/api/v3/exchangeInfo",
                         timeout=40).json()
        spot |= {s["baseAsset"] for s in d["symbols"]
                 if s["status"] == "TRADING" and s["quoteAsset"] in ("USDT", "USDC")}
    except Exception:
        pass
    try:
        d = requests.get("https://api.exchange.coinbase.com/products", timeout=40).json()
        spot |= {p["base_currency"] for p in d if p.get("status") == "online"}
    except Exception:
        pass
    return spot


def funding_window(coin, start_ms, end_ms):
    out, cur = [], start_ms
    for _ in range(40):
        d = post({"type": "fundingHistory", "coin": coin,
                  "startTime": cur, "endTime": end_ms})
        if not d:
            break
        out += d
        nt = d[-1]["time"] + 1
        if nt <= cur or len(d) < 500:
            break
        cur = nt
    return [float(x["fundingRate"]) for x in out]


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    return dict(registered=REGISTERED, started=str(dt.date.today()), months=[])


def step():
    s = load()
    now = int(time.time() * 1000)
    this_month = dt.date.today().strftime("%Y-%m")

    # 1. settle any month that has now completed
    for m in s["months"]:
        if m.get("realised") is not None or m["month"] >= this_month:
            continue
        rates = []
        for c in m["picks"]:
            f = funding_window(c, m["start_ms"], m["end_ms"])
            if f:
                rates.append(float(np.prod([1 + x for x in f]) - 1))
        if rates:
            m["realised"] = float(np.mean(rates) - COST_PER_REBALANCE)
            m["coins_settled"] = len(rates)

    # 2. make this month's selection if not already made
    if not any(m["month"] == this_month for m in s["months"]):
        uni = universe()
        spot = hedgeable()
        look_start = now - 30 * 24 * H
        scores = {}
        for c in uni:
            base = c[1:] if c.startswith("k") else c
            if base not in spot:
                continue
            f = funding_window(c, look_start, now)
            if len(f) > 400:
                scores[c] = float(np.mean(f)) * 24 * 365 * 100
        picks = [c for c, v in sorted(scores.items(), key=lambda x: -x[1])
                 if v > 0][:N_SELECT]
        first = dt.date.today().replace(day=1)
        nxt = (first + dt.timedelta(days=32)).replace(day=1)
        s["months"].append(dict(
            month=this_month, decided_on=str(dt.date.today()),
            picks=picks,
            trailing_ann_pct={c: round(scores[c], 1) for c in picks},
            start_ms=int(time.mktime(dt.date.today().timetuple()) * 1000),
            end_ms=int(time.mktime(nxt.timetuple()) * 1000),
            realised=None))

    json.dump(s, open(STATE, "w"), indent=1)
    return s


def report(s):
    print("=" * 80)
    print("  FUNDING CARRY — forward paper tracker")
    print("=" * 80)
    print("  Research only. No order, no account, no capital.\n")
    done = [m for m in s["months"] if m.get("realised") is not None]
    print(f"  {'month':9s} {'decided':11s} {'realised':>10}  selections")
    for m in s["months"]:
        r = f"{m['realised']*100:+9.2f}%" if m.get("realised") is not None else "   pending"
        print(f"  {m['month']:9s} {m['decided_on']:11s} {r}  "
              f"{', '.join(m['picks'][:8])}{'...' if len(m['picks'])>8 else ''}")
    print(f"\n  completed months: {len(done)}/12 "
          f"({len(done)/12*100:.0f}% of the pre-registered minimum)")
    if done:
        r = np.array([m["realised"] for m in done])
        print(f"  mean monthly {r.mean()*100:+.2f}%  "
              f"(~{((1+r.mean())**12-1)*100:+.1f}% annualised)  "
              f"worst {r.min()*100:+.2f}%  positive {float((r>0).mean())*100:.0f}%")
    if len(done) < 12:
        print("  -> NO VERDICT. Below the minimum evidence threshold.")


if __name__ == "__main__":
    s = step()
    report(s)
