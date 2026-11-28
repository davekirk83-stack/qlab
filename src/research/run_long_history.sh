#!/usr/bin/env bash
# Doc 277/283: re-run the NQ day-trading engines on the long Dukascopy history (2020-25 halves + the 2025-26 cache) instead of ~13 months.
# Builds a scratch copy of the repo whose data_nq_cache/nq_5m.csv is the joined long history; nothing in the real repo's data is replaced.
set -euo pipefail
REPO=/home/claude/qlab-git; W=${W:-/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/longnq}
rm -rf "$W"; mkdir -p "$W"; cp -r "$REPO/src" "$REPO/config" "$W/" 2>/dev/null || true; mkdir -p "$W/data_nq_cache" "$W/runs/research"
cp -r "$REPO/data_ig_cache" "$W/" 2>/dev/null || true
python - "$REPO" "$W" <<'EOF'
import sys, glob, pandas as pd
repo, w = sys.argv[1], sys.argv[2]
parts = [pd.read_csv(f, index_col=0) for f in sorted(glob.glob(f"{repo}/data_nq_cache/nq_5m_20*_h*.csv.gz") + glob.glob(f"{repo}/data_nq_cache/nq_5m_20[0-9][0-9]_[01][0-9].csv.gz"))]
cur = pd.read_csv(f"{repo}/data_nq_cache/nq_5m.csv", index_col=0)
d = pd.concat(parts + [cur]); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated(keep="last")].sort_index()
d.to_csv(f"{w}/data_nq_cache/nq_5m.csv"); print("long NQ 5m:", len(d), d.index[0], d.index[-1], "parts", len(parts))
EOF
cd "$W"; export QLAB_ROOT="$W"
for s in us_plain_integrated ign_exit_fixes ad_exit_fixes wvb_exit_fixes froth_fade_stops ad_div_redo; do
  [ -f "src/research/$s.py" ] || continue
  echo "=== $s"; timeout 5400 python "src/research/$s.py" > "runs/research/LONG_$s.txt" 2>&1 || echo "($s exit $?)"; tail -25 "runs/research/LONG_$s.txt"
done
cp runs/research/LONG_*.txt "$REPO/runs/research/" 2>/dev/null || true
