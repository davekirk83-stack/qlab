"""Doc 189 (DK 5 Nov "1 and 3 yes"): daily check that the IG runner and paper book 7 (Ignition v1.1) agree.
For one New York trading day: Ignition signals on the paper feed (Dukascopy NQ cache) vs on IG's own bars (runs/<book>/signals.csv,
or for days before signals.csv existed, the SIGNAL lines in the committed last_run.log history), matched within 10 minutes; then each
IG fill vs the paper entry (next bar open) — the slippage. Prints a short report; exit code 0 always (a report, not a gate).
Usage: python src/ig_vs_paper.py [YYYY-MM-DD] [ig_demo|ig_live]
"""
import os, sys, re, subprocess, pandas as pd, numpy as np
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{REPO}/src")
os.environ.setdefault("QLAB_ROOT", REPO)
import paperbook7 as P7
day = sys.argv[1] if len(sys.argv) > 1 else (pd.Timestamp.now("America/New_York").normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
book = sys.argv[2] if len(sys.argv) > 2 else "ig_demo"
NY = "America/New_York"; d0 = pd.Timestamp(day, tz=NY); d1 = d0 + pd.Timedelta(days=1)

# paper signals (v1.1 gates: US hours, no 12-15 NY)
bars = pd.read_csv(f"{REPO}/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
f = P7.features(bars); t = f.index.tz_convert(NY); m = t.hour * 60 + t.minute
ok = (t >= d0) & (t < d1) & (m >= P7.US_OPEN) & (m < P7.US_CLOSE) & ~np.isin(t.hour, P7.V11_SKIP_HOURS) & (f.sig.values != 0)
paper = pd.DataFrame({"bar": f.index[ok], "side": f.sig.values[ok].astype(int), "close": f.close.values[ok]})
covered = bool(((t >= d0) & (t < d1)).any())
tr, _, _ = P7.replay(f, d0.tz_convert("UTC").strftime("%Y-%m-%d"), 0, us_hours=True, v11=True)
ptr = [x for x in tr if d0 <= pd.Timestamp(x["opened"]).tz_convert(NY) < d1]

# IG signals
igs = []
sf = f"{REPO}/runs/{book}/signals.csv"
if os.path.exists(sf):
    s = pd.read_csv(sf); s["bar"] = pd.to_datetime(s.bar, utc=True)
    s = s[(s.bar.dt.tz_convert(NY) >= d0) & (s.bar.dt.tz_convert(NY) < d1)]
    igs = [(r.bar, int(r.side), r.close, r.what) for r in s.itertuples()]
if not igs:   # older days: committed log history
    try:
        hs = subprocess.run(["git", "-C", REPO, "log", "--format=%h %cI", "--", f"runs/{book}/last_run.log"], capture_output=True, text=True).stdout.splitlines()
        seen = set()
        for line in hs:
            h, ci = line.split()
            run_day = pd.Timestamp(ci).tz_convert("UTC").strftime("%Y-%m-%d")   # the log's times are UTC clock times on the commit's UTC day
            txt = subprocess.run(["git", "-C", REPO, "show", f"{h}:runs/{book}/last_run.log"], capture_output=True, text=True).stdout
            for mm in re.finditer(r"SIGNAL (BUY|SELL) at bar (\d\d:\d\d) close ([\d.]+)", txt):
                ts = pd.Timestamp(f"{run_day} {mm.group(2)}", tz="UTC")
                if d0 <= ts.tz_convert(NY) < d1 and (ts, mm.group(1)) not in seen:
                    seen.add((ts, mm.group(1))); igs.append((ts, 1 if mm.group(1) == "BUY" else -1, float(mm.group(3)), "taken(log)"))
    except Exception as e: print("log history:", e)

print(f"IGNITION v1.1 — paper feed vs IG ({book}), {day} New York")
if not covered: print("  paper feed has no bars for this day yet — run after the 07:23 paper update"); sys.exit(0)
used = set(); rows = []
for b, sd, c in paper.itertuples(index=False):
    hit = [k for k, x in enumerate(igs) if k not in used and x[1] == sd and abs((x[0] - b).total_seconds()) <= 600]
    if hit: used.add(hit[0]); rows.append(("both", b, sd, c, igs[hit[0]][2], igs[hit[0]][3]))
    else:
        bf = f"{REPO}/runs/{book}/bars_{pd.Timestamp(b):%Y-%m-%d}.csv"; up = False
        if os.path.exists(bf):
            try: bt = pd.to_datetime(pd.read_csv(bf, header=None, usecols=[0])[0], utc=True, format="mixed"); up = bool(((bt >= b - pd.Timedelta(minutes=10)) & (bt <= b + pd.Timedelta(minutes=10))).any())
            except Exception: pass
        rows.append(("paper only", b, sd, c, np.nan, "IG runner was live, its feed gave no signal" if up else "IG runner not running then (coverage, not a feed difference)"))
for k, x in enumerate(igs):
    if k not in used: rows.append(("IG only", x[0], x[1], np.nan, x[2], x[3]))
if not rows: print("  no Ignition signal on either feed — agree")
for w, b, sd, pc, ic, what in sorted(rows, key=lambda r: r[1]):
    print(f"  {pd.Timestamp(b).tz_convert(NY):%H:%M} NY {'BUY ' if sd == 1 else 'SELL'} {w:10} paper close {pc:9.1f}  IG close {ic:9.1f}  {what}")
n_both = sum(r[0] == "both" for r in rows); n = len(rows)
n_cov = sum(r[0] == "paper only" and r[5].startswith("IG runner not") for r in rows)
print(f"  agreement: {n_both}/{n - n_cov} signals on both feeds while the IG runner was live ({n_cov} paper signals fell outside its sessions)" if n else "")
# fills vs paper entries
tf = f"{REPO}/runs/{book}/trades.csv"
if os.path.exists(tf):
    T = pd.read_csv(tf); T["o"] = pd.to_datetime(T.opened, utc=True, format="mixed")
    T = T[(T.o.dt.tz_convert(NY) >= d0) & (T.o.dt.tz_convert(NY) < d1)]
    for r in T.itertuples():
        slip = r.side * (r.ig_entry - r.paper_entry)   # vs the IG signal bar's close (same feed; the two feeds differ in level)
        print(f"  IG fill {r.o.tz_convert(NY):%H:%M} NY side {r.side:+d}: filled {r.ig_entry:.1f} vs IG signal close {r.paper_entry:.1f} -> {slip:+.1f} pts against us; result {r.pts:+.1f} pts ({r.how})")
for x in ptr: print(f"  paper trade {pd.Timestamp(x['opened']).tz_convert(NY):%H:%M} NY side {x['side']:+d}: {x['pts']:+.1f} pts ({x['how']})")
