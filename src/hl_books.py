"""
WHAT DO PROFITABLE HYPERLIQUID ACCOUNTS ACTUALLY DO? — read their books.

DK: "Can we take any more useful trading tips and techniques from hyperliquid,
     or other sources which show trader's books?"

Hyperliquid publishes every account's fills and the full leaderboard with no
key. So instead of reading what traders SAY, measure what they DO: holding
times, maker vs taker share, how many coins, how often they add to a loser,
whether they scale out, win rate per round trip, and whether the P&L comes
from a few big trades or many small ones.

TWO POPULATIONS
  consistent   $5k-$500k account value, positive P&L on day, week, month AND
               all-time, ranked by month ROI. The population closest to a
               small stack scaled up. Not market makers (vlm/value capped).
  whales       top all-time P&L above $1m, for contrast.

And a CONTROL: random accounts of the same size band regardless of P&L, so we
know which habits are merely common and which separate winners from the rest.

Read-only public data. CAP-021: no account, no credential, no order. Addresses
are public on-chain identifiers; no attempt is made to identify anyone.
"""
import warnings; warnings.filterwarnings("ignore")
import json, time, os, sys, urllib.request
import numpy as np, pandas as pd

RUNS = "/home/claude/qlab/runs"
OUT = f"{RUNS}/hl_fills"; os.makedirs(OUT, exist_ok=True)


def post(body, tries=3):
    for k in range(tries):
        try:
            r = urllib.request.Request("https://api.hyperliquid.xyz/info",
                                       data=json.dumps(body).encode(),
                                       headers={"Content-Type": "application/json",
                                                "User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(r, timeout=30))
        except Exception:
            time.sleep(1.5*(k+1))
    return None


def leaderboard():
    j = json.load(open(f"{RUNS}/hl_leaderboard.json"))
    rows = []
    for r in j["leaderboardRows"]:
        w = dict(r["windowPerformances"])
        rows.append(dict(addr=r["ethAddress"], value=float(r["accountValue"]),
                         **{f"pnl_{k}": float(v["pnl"]) for k, v in w.items()},
                         **{f"roi_{k}": float(v["roi"]) for k, v in w.items()},
                         vlm_month=float(w["month"]["vlm"])))
    return pd.DataFrame(rows)


def fills(addr):
    p = f"{OUT}/{addr}.json"
    if os.path.exists(p): return json.load(open(p))
    f = post({"type": "userFills", "user": addr, "aggregateByTime": True})
    time.sleep(0.25)
    if f is None: return None
    json.dump(f, open(p, "w"))
    return f


def characterise(F):
    """Round trips from a fill list. Returns a dict of habits."""
    if not F or len(F) < 30: return None
    d = pd.DataFrame(F)
    d["t"] = pd.to_datetime(d.time, unit="ms", utc=True)
    d["px"] = d.px.astype(float); d["sz"] = d.sz.astype(float)
    d["pnl"] = d.closedPnl.astype(float); d["fee"] = d.fee.astype(float)
    d["maker"] = ~d.crossed
    d = d.sort_values("t")
    span_d = max((d.t.iloc[-1]-d.t.iloc[0]).total_seconds()/86400, 1/24)
    # round trips: per coin, track position; a trip closes when position returns to 0
    trips = []
    for coin, g in d.groupby("coin"):
        pos = 0.0; t0 = None; pnl = 0.0; fee = 0.0; adds = 0; n = 0; first_side = None
        for _, r in g.iterrows():
            sgn = 1 if r.side == "B" else -1
            if pos == 0: t0 = r.t; pnl = 0; fee = 0; adds = 0; n = 0; first_side = sgn
            elif np.sign(pos) == sgn: adds += 1
            pos += sgn*r.sz; pnl += r.pnl; fee += r.fee; n += 1
            if abs(pos) < 1e-9 and t0 is not None:
                trips.append(dict(coin=coin, open=t0, close=r.t, pnl=pnl-fee,
                                  hold_h=(r.t-t0).total_seconds()/3600, fills=n,
                                  adds=adds, side="L" if first_side > 0 else "S"))
                pos = 0.0; t0 = None
    T = pd.DataFrame(trips)
    if len(T) < 10: return None
    gross = T.pnl.sum()
    top = T.pnl.sort_values(ascending=False)
    conc = top.head(max(1, len(T)//20)).sum()/gross if gross > 0 else np.nan
    return dict(n_fills=len(d), n_trips=len(T), trips_per_day=len(T)/span_d,
                maker_share=d.maker.mean(), coins=d.coin.nunique(),
                median_hold_h=T.hold_h.median(), p25_hold_h=T.hold_h.quantile(.25),
                p75_hold_h=T.hold_h.quantile(.75),
                win_rate=(T.pnl > 0).mean(), avg_win=T.pnl[T.pnl > 0].mean(),
                avg_loss=T.pnl[T.pnl <= 0].mean(), short_share=(T.side == "S").mean(),
                adds_per_trip=T.adds.mean(), fills_per_trip=T.fills.mean(),
                top5pct_share=conc, net_pnl=gross, fee_share=d.fee.sum()/max(abs(gross), 1),
                span_days=span_d)


if __name__ == "__main__":
    L = leaderboard()
    print(f"{len(L):,} accounts on the leaderboard.")
    band = L[(L.value >= 5_000) & (L.value <= 500_000)]
    cons = band[(band.pnl_day > 0) & (band.pnl_week > 0) & (band.pnl_month > 0) & (band.pnl_allTime > 0)
                & (band.vlm_month/band.value < 2000)].sort_values("roi_month", ascending=False)
    whales = L[(L.pnl_allTime > 1_000_000)].sort_values("pnl_allTime", ascending=False)
    rng = np.random.default_rng(3)
    ctrl = band.sample(60, random_state=3)
    print(f"  consistent small/mid: {len(cons):,} qualify; whales: {len(whales):,}; control band {len(band):,}\n")

    groups = {"consistent (top 60 by month ROI)": cons.head(60),
              "whales (top 30 all-time P&L)": whales.head(30),
              "control (random same-size accounts)": ctrl}
    res = {}
    for lbl, G in groups.items():
        rows = []
        for a in G.addr:
            F = fills(a)
            c = characterise(F)
            if c: c["addr"] = a; rows.append(c)
        R = pd.DataFrame(rows); res[lbl] = R
        print(f"  {lbl}: {len(R)} accounts with readable books")
    pd.concat([r.assign(group=k) for k, r in res.items()]).to_csv(f"{RUNS}/hl_books.csv", index=False)

    KEYS = [("trips_per_day", "round trips / day", "{:.1f}"),
            ("median_hold_h", "median hold (hours)", "{:.1f}"),
            ("p25_hold_h", "  25th pct hold (h)", "{:.2f}"),
            ("p75_hold_h", "  75th pct hold (h)", "{:.1f}"),
            ("maker_share", "maker (limit) share", "{:.0%}"),
            ("coins", "coins traded", "{:.0f}"),
            ("short_share", "short share of trips", "{:.0%}"),
            ("win_rate", "win rate per trip", "{:.0%}"),
            ("adds_per_trip", "adds per trip", "{:.2f}"),
            ("fills_per_trip", "fills per trip", "{:.1f}"),
            ("top5pct_share", "share of P&L from top 5% of trips", "{:.0%}"),
            ("fee_share", "fees / |net P&L|", "{:.2f}")]
    print(f"\n  {'MEDIAN ACROSS ACCOUNTS':<38}" + "".join(f"{k.split(' (')[0][:22]:>24}" for k in res))
    for key, lbl, fmt in KEYS:
        print(f"  {lbl:<38}" + "".join(f"{fmt.format(R[key].median()):>24}" for R in res.values()))
    # win/loss ratio
    print(f"  {'avg win / avg loss':<38}" + "".join(
        f"{(R.avg_win/-R.avg_loss).median():>24.2f}" for R in res.values()))
