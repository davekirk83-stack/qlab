"""
THE KILL SWITCH — one place that stops every book at once.

DK: "Will we have an 'exit all positions' kill order option, if suddenly a war
     breaks out, there is a market crash etc? This could pause all trading for
     an agreed period."

Yes, and it should exist before the number of books grows any further. Six are
running now - cascade v3, patterns, retest, VWAP, Keltner daily, and the
15-minute range book - across two scheduled tasks, each with its own state
file and its own idea of what it holds. Without a single switch, "stop
everything" means remembering six places under exactly the conditions where
something gets forgotten.

WHAT IT IS, STATED HONESTLY. Under CAP-021 there are no live positions
anywhere, so this halts PAPER books. It opens nothing and closes nothing in
any market. The reason to build it now is that the paper record is only
worth keeping if a halt is recorded as a decision taken at a moment in time,
with a reason, rather than applied quietly afterwards when the outcome is
already known. A kill switch that leaves no trace is how a backtest gets
laundered into a track record.

THE SWITCH is a single row in D1 (pb_halt). Every book reads it before it
does anything:

  active = 0    normal operation
  active = 1    FLATTEN every open position at the current mark, record each
                exit with reason 'halt', and open nothing new
  resume_after  a date. The books stay halted until it passes, then resume
                on their own. DK asked for an agreed period rather than an
                indefinite stop, so the switch expires by default instead of
                being left on by accident.
  flatten       1 closes positions, 0 holds them but stops new entries -
                the softer option for "I want to stop adding risk" rather
                than "get me out".

HOW IT IS SET. Through this script, which writes the SQL, or by DK simply
saying so in chat. Both record who set it and why. Nothing automatic sets it:
an automatic circuit breaker is a separate and harder question, because a
rule that halts on a crash would have halted through several of the periods
the five-year test shows were profitable.

  python killswitch.py on  "Israel-Iran escalation" --days 5
  python killswitch.py on  "flash crash" --no-flatten
  python killswitch.py on  "squeaky bum time" --shorts-only --days 30
  python killswitch.py off
  python killswitch.py status
"""
import sys, json, os
import pandas as pd

RUNS = "/home/claude/qlab/runs"
OUT = f"{RUNS}/halt.sql"


def esc(s): return str(s).replace("'", "''")


def write(sql):
    os.makedirs(RUNS, exist_ok=True)
    open(OUT, "w").write(sql)
    print(sql)
    print(f"\nSQL written to {OUT} — apply it to dk-capital to take effect.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("on", "off", "status"):
        print(__doc__); raise SystemExit(1)
    cmd = sys.argv[1]
    now = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M")
    if cmd == "status":
        print("SELECT active, reason, set_at, set_by, resume_after, flatten "
              "FROM pb_halt WHERE id = 1;")
        raise SystemExit(0)
    if cmd == "off":
        write("UPDATE pb_halt SET active = 0, reason = NULL, "
              f"resume_after = NULL, set_at = '{now}', set_by = 'DK' "
              "WHERE id = 1;")
        raise SystemExit(0)
    reason = sys.argv[2] if len(sys.argv) > 2 else "unspecified"
    days = 7
    flatten = 1
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days")+1])
    if "--no-flatten" in sys.argv:
        flatten = 0
    if "--shorts-only" in sys.argv:
        flatten = 2      # close longs, block new longs, shorts keep running
    until = (pd.Timestamp.utcnow() + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    write(f"UPDATE pb_halt SET active = 1, reason = '{esc(reason)}', "
          f"set_at = '{now}', set_by = 'DK', resume_after = '{until}', "
          f"flatten = {flatten} WHERE id = 1;")
    print(f"\nHALT: {reason}")
    print("  " + {0: 'hold positions, no new entries', 1: 'flatten all positions',
                   2: 'SHORTS ONLY - longs closed and blocked, shorts keep running'}[flatten])
    print(f"  resumes automatically after {until} ({days} days)")
