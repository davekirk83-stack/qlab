# 93 — Go-live criteria: what "four weeks of reliable profit on paper" has to mean (19 Oct 2026)

DK, 16 Oct: *"I think 4 weeks reliable profit making on paper is sufficient to start at a modest level."* This doc turns that sentence into a test that can be passed or failed, so the decision, when it comes, is made against a record and not a feeling. **It changes nothing now.** CAP-021 (research and paper only; no live order, account, credential or capital of any size on any signal) stands until DK makes a separate, deliberate decision with this record in front of him. Nothing here is advice to trade; it is the bar the paper record has to clear before that conversation can even start.

## 1. What "reliable" means — the four tests, all required
**T1 — Four consecutive calendar weeks, each positive, net of costs, for the candidate book.** Not four weeks that net positive; four weeks that are *each* positive. A book that has 3 up weeks and one −6% week has not shown reliability, it has shown variance. Measured Monday to Sunday on the committed state files (the repo is the ledger; D1 is the mirror).

**T2 — The book beats its control over the same four weeks.** For the shadow books (Death-cross, Golden-cross, Ignition) real minus shadow > 0; for Range v3, v3 minus v2.2 > 0; for the range books, the live-window overlay (doc 91) within 3% of the backtest over the same days — i.e. the fills are real. A book that makes money because the market went up has passed T1 and failed T2, and does not go.

**T3 — Sample.** At least 100 closed trips in the four weeks for a 15-minute book, 30 for a 4-hour book, 60 for Ignition. Below that the four weeks are weather, not climate, and the clock keeps running until the count is met.

**T4 — Shape, from the fill log (his step 15).** Median trip positive; top 5% of trips carrying less than 100% of P&L (rule 166); no single day worse than −5% of the book; the kill switch and crash-alert hand-off exercised at least once in a dry run during the window.

## 2. What "modest" means — sizing rules for the first live period, if it ever comes
- Starting stack per book: the smaller of £1,000 and 10% of what DK has said he would lose without it changing anything. One book at a time, the one that passed first; a second book only after the first has run live for four weeks and matched its paper within 5%.
- Leverage as the mandate: 2–3× normal, never above 5× in the first period; risk per trip as the paper book, not more.
- Limit orders only (doc 35, doc 64); the range books do not take market fills.
- The paper book keeps running beside the live one at the same settings. The live ledger is judged against the paper ledger daily; a gap of more than 5% over two weeks stops the live book and the question is the fills, not the strategy.
- Stop conditions pre-written: live book −15% from start, or two consecutive negative weeks, or the crash alert at RED → back to paper, no discussion.

## 3. What the criteria do NOT settle — decisions that need their own doc before any button exists
1. **Who presses the button.** CAP-021 means Claude never holds a key or places an order. A live book means DK, or an automation DK owns and controls, executes from a signal file. That design — what the signal file is, how he confirms it, what happens when he is asleep — has to exist and be rehearsed on paper first.
2. **Venue and account.** Which exchange or broker, in whose name (David J Kirk Ltd was named as the vehicle for ventures; a trading account is a different question for his accountant), and the costs it actually charges versus the 4.5bp / 2bp assumed everywhere in this lab.
3. **Tax and record-keeping** — outside this section's remit; flagged, not answered.

## 4. Where each book stands against the tests today (19 Oct)
| book | started | weeks | T1 | T2 | T3 | T4 | note |
|---|---|---|---|---|---|---|---|
| Keltner v1 | 15 Oct | 0.6 | — | no control | 2 trips | — | daily book, slow |
| Range v2.2 | 16 Oct | 0.5 | week 1 negative | overlay ok (−1.7%) | 172 | — | first week flat for the strategy |
| ETF v3 | 16 Oct | 0.5 | — | no backtest at this timeframe | 4 | — | |
| Death-cross short v1 | 18 Oct | 0.1 | — | shadow | 0 | — | |
| Golden-cross long v1 | 19 Oct | 0 | — | shadow | 0 | — | |
| Range v3 mid-target | 19 Oct | 0 | — | vs v2.2 | 0 | — | the first candidate on the backtest |
| Ignition v1 (NQ) | 19 Oct | 0 | — | shadow | 0 | — | 2 trades/day expected |

Earliest any book can clear T1–T3: the week of 16 November, and only if its next four weeks are each positive. The honest expectation from the backtests is that Range v3 (89–100% of months positive over five years) is the likeliest to clear first, and that a book clearing all four tests in its first four weeks is itself a 1-in-3 event even for a sound strategy — so a miss is not a failure of the strategy, it is the clock restarting.

## 5. Standing instruction
This doc is the bar. The 07:23 report will state, once a week on Mondays, which books have cleared which tests. When a book clears all four, the report says so in one line and stops; the next step is DK's conversation, with section 3 answered first. Rule 169: no book is proposed for live money without this doc's four tests passed on the committed ledger, and section 3 answered in writing.
