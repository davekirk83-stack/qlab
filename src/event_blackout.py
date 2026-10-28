"""Event blackout (DK, 28 Oct 2026: "it's best not to trade these days" / "Yes"; doc 154).
No NEW entries from 30 minutes before to 60 minutes after an FOMC statement (2pm New York). Open positions are managed normally;
resting entry orders are cancelled for the window. Dates live in runs/event_blackouts.json (add next year's FOMC calendar from
federalreserve.gov when it is published)."""
import os, json, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab")
BEFORE, AFTER = pd.Timedelta(minutes=30), pd.Timedelta(minutes=60)
def _events():
    try: return json.load(open(f"{ROOT}/runs/event_blackouts.json"))["fomc"]
    except Exception: return []
def windows():
    out = []
    for d in _events():
        t = pd.Timestamp(d + " 14:00", tz="America/New_York").tz_convert("UTC")
        out.append((t - BEFORE, t + AFTER))
    return out
def in_blackout(ts, lead=pd.Timedelta(0)):
    """True if ts (or ts + lead, for orders that could fill later) falls inside a blackout window."""
    t = pd.Timestamp(ts); t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return any(a <= t <= b or a <= t + lead <= b for a, b in windows())
