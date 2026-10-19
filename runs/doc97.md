# 97 — Two outside sources on autonomous trading loops, checked against ours (19 Oct 2026)

DK sent (18:59) a thread summarising the DXRG paper "What LLM Trading Agents Actually Do in Production" (arXiv 2609.05663, Sep 2026; 3,505 user-funded LLM agents on Base memecoins + a 500–599-agent Hyperliquid fleet, six months) and proAlishke's "The 3 A.M. Problem" thread (8 Sep) on engineering an unattended loop.

## DXRG — what it says and what it confirms
Findings: no fleet showed a directional edge (the Hyperliquid fleet trailed a matched retail benchmark); the operating layer (sliders, constraints, candidate lists, order mechanics) explained behaviour far more than strategy text; sizing was volatility-blind (median 5× leverage in every volatility sextile; one posture cell held 62% of liquidations); agents captured none of the upside they reached (43% saw ≥ +300bp favourable excursion, 49% closed negative; a mechanical bracket recovered +39bp per position); frontier models indistinguishable on 416 replayed scenarios. Every headline survives day-clustered inference and permutation nulls.
For us: confirmation of the two choices the lab made early — **no LLM in the trade loop** (the books are mechanical; the Head of Capital sits before and after them, never inside), and **exits are code** (doc 70, rule 167). Their "mechanical bracket beats the agent's own exit" is our golden-cross and range-book exit findings from a different direction. Nothing to adopt; one thing to keep saying: a trading loop with a model deciding exits, leverage or universe is the failure mode, not the product.

## proAlishke — the checklist, item by item
| his control | ours | status |
|---|---|---|
| append-only ledger first | qlab repo (state + SQL per day) + D1 mirror; findings/rules/books tables | have |
| kill switch + deadman | HALT.json flatten 0/1/2; crash-alert hand-off; a book with a missing state file stops (rule 159) | have; no deadman (not needed while paper) |
| paper loop end to end before capital | seven paper books, replayed daily from the repo | have |
| signal lifecycle with gates, no skipping | implicit (REJECTED / PROMISING / registered / running / PASS); no named states, no PILOT | **gap 1** |
| maker ≠ checker; falsification gauntlet | matched random controls, split-half, exit-free race, planted-edge calibration (= shuffled-label control), 5-year holdouts; but the same session makes and checks | **gap 4** |
| idempotent execution; reconcile against the broker | Ignition replays from its start date each run; range books carry watermarks; no broker (paper) | fine for paper; a live design item for doc 93 §3 |
| lessons as constraints with tests, not prose | rules 151–172 are sentences; SPEC.departure() and the state-file check are the only executable ones | **gap 2** |
| data quality gates (freshness, completeness, sanity; halt, don't pass) | Ignition: "bars older than two days → say so"; Coinbase/Yahoo pulls: none | **gap 3** |
| drift monitoring of inputs vs validation; automatic demotion | live-window overlay (doc 91) done once by hand; doc 93 T2 requires it | **gap 5** |
| capital walked up a ladder (pilot before live) | doc 93 "modest" = one step | **gap 1** |

## Adopted (queue, ahead of the Bulkowski detectors)
1. **Lifecycle states** on the books table — CANDIDATE, VALIDATED, PAPER, PILOT, LIVE, RETIRED — with the gate for each transition written down; PILOT ("deliberately insulting size, enough to feel slippage, not enough to matter") inserted into doc 93 between paper and modest. No transition without its gate; every transition in the ledger.
2. **Rules as tests**: a `tests/` file in qlab that replays each incident and asserts the refusal — missing state file, HALT not honoured, universe drift, entry without ladder, unshifted HTF bar, a book amended in place. A rule without a test is a diary entry.
3. **Data gates** in every paper book: assert bar freshness, completeness and sanity on each pull; halt the book and say so rather than trade stale data.
4. **Checker separation**: no registration without a fresh-session checker that re-derives the result from the doc alone (the high-stakes verification made mandatory). Rule 173.
5. **Weekly drift check**: the live-overlay as a standing Monday line per book, with automatic demotion (PAPER → watch) when live separates from validation beyond doc 93's 3%.
