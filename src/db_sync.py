"""
DATABASE SYNC — emit SQL for everything the trackers have produced.

The paper trackers write JSON to runs/paper/. That directory lives in an
ephemeral container: when it recycles, the forward record goes with it, and a
forward record that cannot survive a restart is not evidence of anything.

The container has no Cloudflare credentials and should not have any, so this
does not write to D1 itself. It emits idempotent SQL which is executed through
the Cloudflare MCP tool in-session. INSERT OR IGNORE on a UNIQUE(book, sym,
entry_time) key means running it twice is harmless — no duplicate trades, no
need to track what has already been synced.

Run at the end of any session that stepped a tracker.
"""
import json, glob, os, sys

PAPER = "/home/claude/qlab/runs/paper"


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return repr(v)


def main():
    rows = []
    for f in sorted(glob.glob(f"{PAPER}/*.json")):
        book = os.path.basename(f)[:-5]
        if book == "state":
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for t in d.get("trades", []):
            if not isinstance(t, dict):
                continue
            rows.append("(NULL," + ",".join(q(x) for x in (
                book, t.get("sym"), t.get("day"), t.get("entry_time"),
                t.get("entry"), t.get("stop"), t.get("ret"), t.get("exit"),
                t.get("risk_pct"), t.get("ret_fixed"), t.get("exit_fixed"))) + ")")
    if not rows:
        print("-- no trades to sync")
        return
    print(f"-- {len(rows)} trades across the paper books")
    print("INSERT OR IGNORE INTO trades VALUES")
    print(",\n".join(rows) + ";")


if __name__ == "__main__":
    main()
