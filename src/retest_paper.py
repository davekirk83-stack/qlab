"""
RETEST BOOK — forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance. This file reads local archives and writes JSON.

Third forward-tracked strategy, alongside the cascade bounce (cascade_paper.py)
and the confluence pattern book (pattern_paper.py). It gets its own registration
rather than being bolted onto the pattern book, because that spec was registered
earlier the same day and is unamendable mid-run. Improving a running strategy
mid-flight is how a backtest becomes fiction.

THE SPEC, FIXED AT REGISTRATION (2026-10-14) — doc 42, narrowed by doc 43

    DIAGONAL TREND LINES ONLY, plus ETF horizontals.

    The first initialisation of this tracker scanned all history and exposed
    something doc 42's paired comparison hid: beating the break is not the same
    as making money. The retest beats the break in every slice, but only two
    slices are actually PROFITABLE:
        diagonal retests   +0.385R   (paired break -0.032R)
        ETF daily          +0.235R   (paired break -0.036R)
        crypto hourly horizontal  -0.115R  — beats the break, still loses
    A trade that loses less than a worse trade is not a strategy. The spec is
    therefore narrowed BEFORE registration, which is permitted; narrowing it
    after would not be.

    universe    crypto perps hourly + survivorship-clean ETFs daily
    level       an established descending TREND LINE with >=3 touches (both
                universes), OR a pivot-high horizontal (ETFs only)
    break       a close above the level by more than 0.4 x ATR
    ENTRY       NOT the break. Price must return to within 0.4 x ATR of the
                level within 20 bars and close back above it. Buy that close.
    stop        just below the level at the retest bar (0.4 x ATR), which for a
                diagonal means the line's price AT THAT BAR, not at the break
    EXIT        NO TARGET. Hold 40 bars, then exit at that close. Stop only.
                (doc 44 — replaces the measured move, which was costing
                 -0.471R of edge. Tight targets degrade this trade
                 MONOTONICALLY: a 1R target wins 51.8% of the time and returns
                 +0.037R; holding wins 18.8% and returns +0.841R. The measured
                 move was cutting winners. Against random entries with the same
                 stop distance: hold-40 edge +0.833R, measured-move edge
                 +0.362R. Hold-80 scores higher in absolute terms but its
                 control also rises to +0.189R, i.e. it is partly harvesting
                 drift; hold-40's control is +0.008R, so its edge is clean.)
    void        a close below the level by more than 0.4 x ATR before the
                retest completes
    costs       assumed in R terms per universe at resolution time

WHY THIS SHOULD WORK — the mechanism is the stop, not prediction
Hit rates barely improve (ETF diagonal 17.4% -> 21.5%). Reward:risk improves a
lot (5.11 -> 7.14). Entering beside the level with the stop just under it buys
the same target for less risk. This is an edge from trade CONSTRUCTION, which
is more robust than one from a claimed market mechanism — and it is the first
of its kind in the programme.

BACKTEST FOR REFERENCE (not a promise) — paired, same setups both ways
    universe              break      retest     edge
    crypto hourly        -0.210R    -0.137R   +0.073R
    crypto daily         +0.191R    +0.305R   +0.115R
    ETF                  -0.018R    +0.217R   +0.235R
    crypto hourly diag   +0.122R    +0.429R   +0.307R
    crypto daily diag    -0.106R    +0.083R   +0.189R
    ETF diag             -0.152R    +0.350R   +0.502R
    6 of 6 favour the retest.

NOT EVIDENCE, and recorded so it is never mistaken for any
    The "broke and never retested" group shows +1.5R to +2.8R. It is CIRCULAR:
    the group is defined by price action AFTER entry, so it selects winners by
    construction. It is not a strategy and must never be traded or quoted.

PRE-REGISTERED KILL CRITERION — not amendable mid-run
    minimum evidence   120 resolved trades or 6 months, whichever first
    PASS               retest mean > 0 net of costs AND retest beats the PAIRED
                       break entry on the same setups
    FAIL               retest mean <= 0 at n=120, or paired break >= retest
    early kill         any 25-trade block worse than -0.50R mean
    not evidence       a good week; the first 40 trades; one large winner;
                       anything from the no-retest group
    amendment          ANY change to universe, level definition, break or
                       retest tolerance, stop, target or costs voids the run

THE PAIRED CONTROL IS PART OF THE SPEC
Every taken retest also records what the break entry on the SAME setup would
have returned. The comparison that decided this strategy is the comparison that
must keep deciding it. An unpaired number proves nothing here — the first
analysis of this idea reached the opposite conclusion precisely because it
compared different trades.
"""
import os, glob, json, datetime as dt
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
import retest as RT

HOLD = 40          # bars held; there is no target (doc 44)


def score_hold(df, bar, entry, stop, hold=HOLD):
    """Stop-only exit, held `hold` bars. Returns R, or resolved=0 if the trade
    is still younger than `hold` bars — it is then re-scored on a later run."""
    H, L, C = df.high.values, df.low.values, df.close.values
    n = len(df)
    risk = entry - stop
    if risk <= 0 or not np.isfinite(risk):
        return None
    last = bar + hold
    end = min(last, n - 1)
    for j in range(bar + 1, end + 1):
        if L[j] <= stop:
            return dict(R=-1.0, rr=float(hold), win=0.0, resolved=1,
                        bars=j - bar)
    if last > n - 1:
        return dict(R=float((C[n - 1] - entry) / risk), rr=float(hold),
                    win=np.nan, resolved=0, bars=n - 1 - bar)
    r = float((C[last] - entry) / risk)
    return dict(R=r, rr=float(hold), win=float(r > 0), resolved=1, bars=hold)

STATE = "/home/claude/qlab/runs/paper/retest.json"
H1 = "/home/claude/qlab/data_1h_33"
ETF = "/home/claude/qlab/data_wide"
CLEAN_ETF = set("""SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV ACWI
XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK
TLT IEF SHY LQD HYG AGG TIP BND EMB MUB
GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA
VNQ IYR VXX""".split())

COST_R = {"crypto_hourly": 0.017, "etf_daily": 0.005}

REGISTERED = {
    "registered_on": "2026-10-14",
    "spec_doc": "42-break-retest-and-the-chart-report",
    "universe": "crypto perps hourly + survivorship-clean ETFs daily",
    "entry": "the retest close, NOT the break close",
    "exit": "no target; hold 40 bars then exit at the close; stop only (doc 44)",
    "exit_evidence": {"hold40_vs_random": 0.833, "measured_vs_random": 0.362,
                      "hold80_vs_random": 0.721,
                      "note": "hold80 is partly drift (control +0.189R); "
                              "hold40 control is +0.008R"},
    "levels": ["descending trend line >=3 touches (both universes)",
               "pivot_high horizontal (ETFs only)"],
    "narrowed_before_registration": "crypto hourly horizontals excluded: "
        "retest -0.115R beats the break -0.197R but still loses money",
    "forward_only": "a setup is recorded only if its retest completes within "
        "the last 60 bars; the first build logged 12,271 historical setups",
    "minimum_evidence": "120 resolved trades or 6 months, whichever first",
    "pass": "retest mean > 0 net of costs AND retest beats the PAIRED break entry",
    "fail": "retest mean <= 0 at n=120, or paired break >= retest",
    "early_kill": "any 25-trade block worse than -0.50R mean",
    "not_evidence": ["a good week", "the first 40 trades", "one large winner",
                     "the no-retest group, which is circular"],
    "amendment": "any spec change voids the run and restarts the clock",
    "backtest_reference": {
        "paired_edge_R": {"crypto_hourly": 0.073, "crypto_daily": 0.115,
                          "etf": 0.235, "crypto_hourly_diag": 0.307,
                          "crypto_daily_diag": 0.189, "etf_diag": 0.502},
        "mechanism": "reward:risk, not hit rate — the stop sits under the level",
        "caveat": "measured-move targets are over-ambitious (hit rates 13-24%); "
                  "the retest edge holds because both arms share the target"},
}


def charts():
    out = []
    for p in sorted(glob.glob(f"{H1}/*.csv")):
        out.append(("crypto_hourly", os.path.basename(p)[:-4], p))
    for s in sorted(CLEAN_ETF):
        p = f"{ETF}/{s}.csv"
        if os.path.exists(p):
            out.append(("etf_daily", s, p))
    return out


def load(path):
    df = pd.read_csv(path)
    dc = "date" if "date" in df.columns else df.columns[0]
    df[dc] = pd.to_datetime(df[dc], errors="coerce")
    df = df.dropna(subset=[dc]).set_index(dc).sort_index()
    return df[~df.index.duplicated()]


def scan(universe, sym, path, watermark=None):
    """Only setups whose RETEST bar is STRICTLY AFTER this symbol's watermark.

    The watermark is the last bar that existed when the tracker first saw this
    symbol. Two earlier designs failed here and both looked fine while doing so:
      - no guard at all: 12,271 historical setups logged, "minimum evidence
        reached" on day one;
      - a trailing 60-bar window: with a 40-bar hold, setups inside the window
        were ALREADY MATURE at registration, so day one opened with 85 "mature"
        trades that were really backtest data.
    A forward tracker must admit only what did not exist when it started. The
    watermark is the only version of that which cannot be undone by changing
    the hold period.
    """
    df = load(path)
    if len(df) < 500:
        return []
    try:
        lows, highs = PP.confirmed_pivots(df)
    except Exception:
        return []
    if len(lows) < 4 or len(highs) < 4:
        return []
    C = df.close.values
    out = []
    for diag, setups in ((False, RT.find_setups(df, highs, lows, tail=0)),
                         (True, RT.diagonal_setups(df, highs, lows, tail=0))):
        for sid, u in enumerate(setups):
            rb = u.get("retest_bar")
            if rb is None or u.get("failed"):
                continue
            if watermark is not None and str(df.index[rb]) <= watermark:
                continue                   # existed before we started watching
            # SPEC: diagonals anywhere; horizontals on ETFs only (doc 43)
            if not diag and universe != "etf_daily":
                continue
            stop = u.get("retest_stop") if diag else u["stop"]
            if stop is None:
                stop = u["stop"]
            # Score with whatever bars exist NOW. A setup too young to have
            # resolved is recorded OPEN and re-scored on later runs — that is
            # what makes this forward tracking rather than a backtest replay.
            r = score_hold(df, rb, C[rb], stop)
            b = score_hold(df, u["break_bar"], u["entry_break"], u["stop"])
            if not r or not b:
                continue
            bars_since = len(df) - 1 - rb
            out.append(dict(
                universe=universe, sym=sym, diagonal=bool(diag),
                sid=f"{sym}|{'d' if diag else 'h'}|{sid}",
                ts=str(df.index[rb]), level=round(float(u["level"]), 8),
                entry=round(float(C[rb]), 8), stop=round(float(stop), 8),
                target=round(float(u["target"]), 8),
                touches=int(u.get("touches", 0)),
                rr=round(float(r["rr"]), 3), resolved=int(r["resolved"]),
                R=round(float(r["R"]), 4),
                paired_break_R=round(float(b["R"]), 4),
                win=(None if r["resolved"] == 0 else bool(r["win"] == 1)),
                bars_since=int(bars_since),
                mature=bool(bars_since >= HOLD),
            ))
    return out


def refresh_open(s):
    """Re-score every still-open setup against the latest bars."""
    by_sym = {}
    for t in s["trades"]:
        # Re-score anything not yet MATURE — including stop-outs. A stopped trade is
        # resolved at once but its bars_since must keep advancing until HOLD, or it
        # never matures and the evidence pool silently drops every loser (doc 106).
        if t.get("mature"):
            continue
        by_sym.setdefault((t["universe"], t["sym"]), []).append(t)
    if not by_sym:
        return 0
    paths = {(u, sy): p for u, sy, p in charts()}
    closed = 0
    for key, items in by_sym.items():
        p = paths.get(key)
        if not p:
            continue
        try:
            df = load(p)
        except Exception:
            continue
        idx = {str(x): i for i, x in enumerate(df.index)}
        for t in items:
            i = idx.get(t["ts"])
            if i is None:
                continue
            r = score_hold(df, i, t["entry"], t["stop"])
            if not r:
                continue
            t["resolved"] = int(r["resolved"])
            t["R"] = round(float(r["R"]), 4)
            t["win"] = None if r["resolved"] == 0 else bool(r["win"] == 1)
            t["bars_since"] = int(len(df) - 1 - i)
            t["mature"] = bool(t["bars_since"] >= HOLD)
            if t["resolved"] == 1:
                closed += 1
    return closed


def state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    return dict(registered=REGISTERED, started=str(dt.date.today()),
                seen=[], trades=[], watermarks={})


def step():
    s = state()
    s.setdefault("watermarks", {})
    closed = refresh_open(s)
    seen = set(s["seen"])
    new = 0
    for universe, sym, path in charts():
        key = f"{universe}|{sym}"
        first_sight = key not in s["watermarks"]
        try:
            df_last = str(load(path).index[-1])
        except Exception:
            continue
        if first_sight:
            # First time we have seen this symbol: record where "now" is and
            # take NO trades from its history. Everything before this instant
            # is backtest, and backtest does not belong in a forward journal.
            s["watermarks"][key] = df_last
            continue
        try:
            found = scan(universe, sym, path, watermark=s["watermarks"][key])
        except Exception:
            continue
        s["watermarks"][key] = df_last
        for t in found:
            key = f"{t['sid']}|{t['ts']}"
            if key in seen:
                continue
            seen.add(key); s["trades"].append(t); new += 1
    s["seen"] = sorted(seen)[-40000:]
    json.dump(s, open(STATE, "w"), indent=1)
    print(f"  {new} new retest setups recorded, {closed} open setups resolved")
    return s


def block_check(T, size=25, floor=-0.50):
    """Early kill: any consecutive block of `size` worse than `floor`."""
    r = T.R.values
    for i in range(0, len(r) - size + 1):
        m = r[i:i + size].mean()
        if m < floor:
            return i, float(m)
    return None, None


def report(s):
    T = pd.DataFrame(s["trades"])
    print("=" * 88)
    print(f"  RETEST BOOK — forward paper, started {s['started']}")
    print("=" * 88)
    print("  Research only. No order, no account, no capital.\n")
    if not len(T):
        print("  no setups yet"); return
    # EVIDENCE = MATURE trades only. A young setup can essentially only resolve
    # as a LOSS (the stop is near; the gain needs time), so counting resolved-
    # only trades early samples stop-outs and nothing else — an early build
    # showed -0.647R at a 9.5% hit rate for exactly that reason. A trade joins
    # the pool once it has been held the full HOLD bars.
    T["evidence"] = T.mature.fillna(False)
    res = T[T.evidence]
    for lab, sub in (("ALL retests", T),
                     ("  horizontal", T[~T.diagonal]),
                     ("  DIAGONAL", T[T.diagonal]),
                     ("  crypto hourly", T[T.universe == "crypto_hourly"]),
                     ("  ETF daily", T[T.universe == "etf_daily"])):
        if len(sub) < 1:
            continue
        m = sub[sub.evidence]
        if not len(m):
            print(f"  {lab:18s} n={len(sub):5d} logged, 0 mature yet")
            continue
        r = m.R.values; b = m.paired_break_R.values
        se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
        mr = m[m.resolved == 1]
        hit = mr.win.mean() * 100 if len(mr) else float("nan")
        print(f"  {lab:18s} logged={len(sub):5d} mature={len(r):5d}  hit {hit:5.1f}%  "
              f"retest {r.mean():+6.3f}R  paired break {b.mean():+6.3f}R  "
              f"EDGE {r.mean()-b.mean():+6.3f}R"
              + (f"  t={r.mean()/se:+5.2f}" if se == se and se > 0 else ""))
    n = len(res)
    print(f"\n  evidence: {n}/120 MATURE trades ({len(T)} logged, "
          f"{int((~T.evidence).sum())} still too young to count) "
          f"({min(n/120*100,100):.0f}% of the pre-registered minimum)")
    if len(res) >= 25:
        i, m = block_check(res)
        if i is not None:
            print(f"  ** EARLY KILL BREACHED ** 25-trade block from #{i} "
                  f"mean {m:+.3f}R, below the -0.50R floor")
    if n < 120:
        print("  -> NO VERDICT. Below the minimum. This is not a result yet.")
    else:
        edge = res.R.mean() - res.paired_break_R.mean()
        ok = res.R.mean() > 0 and edge > 0
        print(f"  -> {'PASS' if ok else 'FAIL'}: mean {res.R.mean():+.3f}R, "
              f"paired edge {edge:+.3f}R")


if __name__ == "__main__":
    s = step()
    report(s)
