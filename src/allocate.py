"""
MONTHLY PROFIT ALLOCATION — four buckets, weighted by stack size.

DK, 2026-10-16: "siphon 25% off per month as pure profit, 25% paid into a gold
fund, 25% set aside for correction buying on long term holds, and 25% to grow
the actual trading stack" - then agreed to tier the weights by stack size after
seeing what a flat split costs at $2,000.

THE TIERS, and why they exist. At $2,000 earning 24.8% a year, monthly profit
is about $41. Split four ways that is roughly £8 a bucket, the stack then
compounds at 6.2% rather than 24.8%, and over ten years the flat split produces
less than half the total wealth of simply reinvesting - because every bucket is
paid for by starving the engine that fills all four. So:

    stack below $10,000      100% reinvested. Nothing is withdrawn.
    $10,000 to $25,000       50% to the stack, 50% split equally across
                             profit / gold / correction reserve
    above $25,000            DK's original 25 / 25 / 25 / 25

The engine compounds while it is small; withdrawals begin once a quarter of a
month's profit is actually worth banking.

WHAT THE BUCKETS ARE FOR
  profit     taken out and gone. The point is that the system pays its owner;
             a strategy that never does is hard to stay disciplined about.
  gold       DK's stated crash positioning (Dalio, Rickards). Not tested here -
             it is an allocation decision, not a strategy claim.
  reserve    the correction-buying pot validated in doc 129: it ADDS to
             long-term holds on dips and withdraws on recovery, leaving the
             profit in the core. It must never fund itself by trimming the
             core, because two independent grids showed that loses to simply
             holding.
  stack      compounds inside the trading books.

A LOSING MONTH ALLOCATES NOTHING. Buckets are filled from profit, never from
capital, and a drawdown is not recovered by withdrawing less later - it simply
means no allocation until the stack is above its previous high. That high-water
rule is what stops the four buckets quietly eating the stack in a bad year.

CAP-021: this moves no actual money. It is a policy being tested on the paper
ledger so it is already decided, and already measured, before it could ever
apply to anything real.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, sys
import pandas as pd

RUNS = "/home/claude/qlab/runs"
STATE = f"{RUNS}/buckets.json"


def tier(stack):
    """Returns (label, to_stack, each_other_bucket)."""
    if stack < 10_000:  return "under $10k — reinvest all", 1.00, 0.0
    if stack < 25_000:  return "$10-25k — half reinvested", 0.50, 0.50/3
    return "over $25k — DK's 25/25/25/25", 0.25, 0.25


def allocate(book, equity, state):
    """Apply the policy for one book. Mutates state; returns a row or None."""
    s = state.setdefault(book, {"high": None, "last_month": None,
                                "profit": 0.0, "gold": 0.0, "reserve": 0.0})
    month = pd.Timestamp.utcnow().strftime("%Y-%m")
    if s["last_month"] == month:
        return None                       # already allocated this month
    if s["high"] is None:
        s["high"] = equity; s["last_month"] = month
        return None                       # first month establishes the mark
    # HIGH-WATER: profit is measured against the previous high, not the
    # previous month, so a drawdown must be fully recovered before anything
    # is withdrawn again.
    profit = equity - s["high"]
    s["last_month"] = month
    if profit <= 0:
        return {"month": month, "book": book, "stack_before": equity,
                "profit": 0.0, "tier": "below high-water — no allocation",
                "to_stack": 0.0, "to_profit": 0.0, "to_gold": 0.0,
                "to_reserve": 0.0, "stack_after": equity,
                "cum_profit": s["profit"], "cum_gold": s["gold"],
                "cum_reserve": s["reserve"]}
    lbl, f_stack, f_other = tier(equity)
    to_stack = profit*f_stack
    to_each = profit*f_other
    s["profit"] += to_each; s["gold"] += to_each; s["reserve"] += to_each
    after = equity - (profit - to_stack)
    s["high"] = after
    return {"month": month, "book": book, "stack_before": equity,
            "profit": profit, "tier": lbl, "to_stack": to_stack,
            "to_profit": to_each, "to_gold": to_each, "to_reserve": to_each,
            "stack_after": after, "cum_profit": s["profit"],
            "cum_gold": s["gold"], "cum_reserve": s["reserve"]}


def esc(x): return str(x).replace("'", "''")


if __name__ == "__main__":
    # equities are passed in as book=value pairs by the scheduled task, which
    # reads them from pb_equity / pb2_equity
    args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    if not args:
        print(__doc__); raise SystemExit(0)
    state = {}
    if os.path.exists(STATE):
        try: state = json.load(open(STATE))
        except Exception: pass
    lines = []
    for book, v in args.items():
        try: eq = float(v)
        except ValueError: continue
        row = allocate(book, eq, state)
        if row is None:
            print(f"  {book}: nothing to do (first month, or already run)")
            continue
        print(f"  {book}: equity ${eq:,.2f}  profit ${row['profit']:,.2f}  "
              f"[{row['tier']}]")
        if row["profit"] > 0:
            print(f"      stack +${row['to_stack']:,.2f}   "
                  f"profit +${row['to_profit']:,.2f}   "
                  f"gold +${row['to_gold']:,.2f}   "
                  f"reserve +${row['to_reserve']:,.2f}")
        lines.append(
            "INSERT INTO pb_buckets (month, book, stack_before, profit, tier, "
            "to_stack, to_profit, to_gold, to_reserve, stack_after, "
            "cum_profit, cum_gold, cum_reserve, run_at) VALUES "
            f"('{row['month']}', '{esc(book)}', {row['stack_before']:.4f}, "
            f"{row['profit']:.4f}, '{esc(row['tier'])}', {row['to_stack']:.4f}, "
            f"{row['to_profit']:.4f}, {row['to_gold']:.4f}, "
            f"{row['to_reserve']:.4f}, {row['stack_after']:.4f}, "
            f"{row['cum_profit']:.4f}, {row['cum_gold']:.4f}, "
            f"{row['cum_reserve']:.4f}, "
            f"'{pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M')}');")
    os.makedirs(RUNS, exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=1)
    if lines:
        out = f"{RUNS}/buckets_{pd.Timestamp.utcnow().strftime('%Y-%m')}.sql"
        open(out, "w").write("\n".join(lines))
        print(f"\n  SQL -> {out}")
