"""
WHAT A PROFITABLE TRADE ACTUALLY LOOKS LIKE.

DK: "I don't care about the evidence. I want you to see exactly what a
     successful and profitable trade looks like as technique and execution."

A fair instruction. Everything in this programme so far has tested RULES. None
of it has looked at how money is actually made, fill by fill, by people who
demonstrably make it.

WHY HYPERLIQUID
It is a fully on-chain perpetuals exchange, so every fill of every account is
public and verifiable: price, size, side, timestamp, whether the order was
passive or aggressive, the fee paid and the realised PnL. No self-reporting, no
survivorship in the record itself, no screenshots. The leaderboard carries
47,016 accounts with audited PnL. That is a better evidence base for EXECUTION
than any book or course, because it is what they did rather than what they say.

SELECTION
From the 47,016: equity over $200k, profitable over all-time AND the last month
AND the last week, and all-time ROI over 100%. 379 accounts survive. Then
ranked by PnL PER DOLLAR OF VOLUME TRADED — edge per unit of turnover, which
rewards skill rather than size and cannot be bought with leverage.

WHAT IS MEASURED, and why each one matters to us
  maker share     passive or aggressive? Doc 61 measured that our own cost
                  assumption was 3-4x too pessimistic at retail size. If the
                  best accounts are overwhelmingly passive, execution style is
                  a larger part of their edge than signal.
  fills per trade do they take a position in one go, or build it? Doc 65 found
                  laddering more than doubled return per unit of capital on
                  our cascade book, and DK predicted exactly that.
  build direction when they add, is price moving FOR them or AGAINST them?
                  This separates averaging down from pyramiding, and doc 53
                  voided our own ladder for being the former.
  hold time       doc 67 found our cascade is a scalp and not a swing trade.
                  What are they?
  win rate and
  payoff          the shape of the distribution: many small wins, or few large?
  fees vs PnL     how much of the gross does execution cost them?
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys
import numpy as np, pandas as pd


def load(path):
    f = json.load(open(path))
    d = pd.DataFrame(f)
    for c in ("px", "sz", "closedPnl", "fee", "startPosition"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.time, unit="ms")
    return d.sort_values("ts").reset_index(drop=True)


def round_trips(d):
    """Group fills into positions: a position runs from flat to flat."""
    out = []
    for coin, g in d.groupby("coin"):
        g = g.sort_values("ts")
        # The 2000-fill window starts mid-position, so anchor on the API's
        # startPosition (the position BEFORE the first fill) rather than
        # assuming flat. Without this every early trade is orphaned.
        pos = float(g.iloc[0].startPosition) if np.isfinite(g.iloc[0].startPosition) else 0.0
        cur = None
        if abs(pos) > 1e-9:
            cur = dict(coin=coin, start=g.iloc[0].ts, fills=0, adds=0, opens=0,
                       closes=0, maker=0, taker=0, pnl=0.0, fee=0.0,
                       first_px=float(g.iloc[0].px),
                       side=(1 if pos > 0 else -1), add_pxs=[], peak=abs(pos),
                       partial=True)
        for _, r in g.iterrows():
            signed = r.sz if r.dir in ("Open Long", "Close Short", "Buy") else -r.sz
            if cur is None:
                cur = dict(coin=coin, start=r.ts, fills=0, adds=0, opens=0,
                           closes=0, maker=0, taker=0, pnl=0.0, fee=0.0,
                           first_px=r.px, side=(1 if signed > 0 else -1),
                           add_pxs=[], peak=0.0, partial=False)
            cur["fills"] += 1
            cur["pnl"] += (r.closedPnl if np.isfinite(r.closedPnl) else 0.0)
            cur["fee"] += (r.fee if np.isfinite(r.fee) else 0.0)
            if r.crossed: cur["taker"] += 1
            else: cur["maker"] += 1
            if "Open" in str(r.dir) or (cur["side"] > 0 and signed > 0) or \
               (cur["side"] < 0 and signed < 0):
                cur["opens"] += 1
                cur["add_pxs"].append(r.px)
            else:
                cur["closes"] += 1
            pos += signed
            cur["peak"] = max(cur["peak"], abs(pos))
            if abs(pos) < 1e-9:
                cur["end"] = r.ts
                cur["last_px"] = r.px
                cur["hold_min"] = (cur["end"] - cur["start"]).total_seconds() / 60
                out.append(cur); cur = None; pos = 0.0
    return pd.DataFrame(out)


def report(path, label):
    d = load(path)
    T = round_trips(d)
    if not len(T):
        print(f"  {label}: no completed round trips in the window"); return
    T = T[T.fills >= 2]
    T = T[~T.get("partial", False)] if "partial" in T.columns else T
    print("=" * 84)
    print(f"  {label}")
    print(f"  {len(d)} fills  {d.ts.min().date()} -> {d.ts.max().date()}  "
          f"{d.coin.nunique()} instruments   {len(T)} completed round trips")
    print("=" * 84)
    mk = (~d.crossed).mean() * 100
    print(f"\n  EXECUTION STYLE")
    print(f"    passive (resting limit) fills   {mk:5.1f}%")
    print(f"    aggressive (crossed spread)     {100-mk:5.1f}%")
    notional = (d.px * d.sz).sum()
    print(f"    total fees ${d.fee.sum():,.0f} on ${notional:,.0f} traded"
          f"   = {d.fee.sum()/notional*10000:.2f}bp")
    gross = d.closedPnl.sum()
    print(f"    realised PnL ${gross:,.0f}   fees are "
          f"{d.fee.sum()/abs(gross)*100:.1f}% of it")
    if not len(T):
        print("  no completed round trips\n"); return
    print(f"\n  POSITION BUILDING")
    print(f"    fills per position      median {T.fills.median():.0f}   "
          f"mean {T.fills.mean():.1f}   max {T.fills.max():.0f}")
    print(f"    ENTRY fills per position median {T.opens.median():.0f}   "
          f"mean {T.opens.mean():.1f}")
    print(f"    EXIT fills per position  median {T.closes.median():.0f}   "
          f"mean {T.closes.mean():.1f}")
    single = (T.opens == 1).mean() * 100
    print(f"    entered in ONE fill      {single:5.1f}% of positions")
    print(f"    scaled in (2+ fills)     {100-single:5.1f}%")
    # when they add, is price moving for or against them?
    agg = []
    for _, r in T.iterrows():
        p = r.add_pxs
        if len(p) < 2: continue
        # for a long, adding lower = averaging down; adding higher = pyramiding
        d_ = np.diff(p)
        agg.append(np.mean(d_ > 0) if r.side > 0 else np.mean(d_ < 0))
    if agg:
        print(f"    when scaling in, share of adds made INTO the move "
              f"(pyramiding): {np.mean(agg)*100:.1f}%")
        print(f"    share made AGAINST the move (averaging down):      "
              f"{(1-np.mean(agg))*100:.1f}%")
    print(f"\n  HOLDING TIME")
    for q, lab in ((0.25, "25th pct"), (0.5, "median  "), (0.75, "75th pct")):
        v = T.hold_min.quantile(q)
        print(f"    {lab}  {v:9.1f} min  ({v/60:7.1f} h)")
    print(f"\n  OUTCOME SHAPE")
    w = T[T.pnl > 0]; l = T[T.pnl <= 0]
    print(f"    win rate                {len(w)/len(T)*100:5.1f}%")
    if len(w) and len(l):
        print(f"    average win   ${w.pnl.mean():>12,.0f}")
        print(f"    average loss  ${l.pnl.mean():>12,.0f}")
        print(f"    payoff ratio            {abs(w.pnl.mean()/l.pnl.mean()):5.2f}")
        print(f"    largest win   ${T.pnl.max():>12,.0f}")
        print(f"    largest loss  ${T.pnl.min():>12,.0f}")
        top = T.nlargest(max(1, len(T)//20), "pnl").pnl.sum()
        print(f"    top 5% of trades supplied {top/T.pnl.sum()*100:5.1f}% of total PnL")
    print()


if __name__ == "__main__":
    report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
