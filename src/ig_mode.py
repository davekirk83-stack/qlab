"""Which IG account the runner trades: the DEMO (default) or, since 4 Nov 2026, DK's LIVE spread-bet account (doc 185).
CAP-021 as amended 4 Nov 2026 (DK "Yes"): a £500 live book on DK's IG spread-bet account, run by an automation DK owns and controls
(GitHub Actions, live key only in DK's GitHub secrets; DK switches it on/off with the repo variable IG_LIVE_ENABLED). Live scope:
Ignition v1.1 + the Range ladder on the US Tech 100 only, IG minimum stakes, rule 186 limits, 5x exposure cap, -4% day stop,
and back to paper at -15% from the start. Live mode needs IG_MODE=live AND the exact confirmation string below, or it refuses."""
import os
MODE = os.environ.get("IG_MODE", "demo").strip().lower()
CONFIRM = "CAP021-AMENDED-2026-11-04-IG-SPREADBET-500"
if MODE == "live" and os.environ.get("IG_LIVE_CONFIRMED", "") != CONFIRM:
    raise SystemExit("IG_MODE=live refused: IG_LIVE_CONFIRMED does not match the CAP-021 amendment of 4 Nov 2026")
if MODE not in ("demo", "live"): raise SystemExit(f"IG_MODE must be demo or live, not {MODE!r}")
LIVE = MODE == "live"
ACC_TYPE = "live" if LIVE else "demo"
OUT = os.environ.get("IG_OUT", "runs/ig_live" if LIVE else "runs/ig_demo")
MIN_ONLY = os.environ.get("IG_MIN_ONLY", "1" if LIVE else "0") == "1"   # live starts at IG's minimum stake on every order (doc 185)
FLOOR = float(os.environ.get("IG_BOOK_FLOOR", "0.85"))                 # live book at -15% from its start -> no new entries; back to paper
