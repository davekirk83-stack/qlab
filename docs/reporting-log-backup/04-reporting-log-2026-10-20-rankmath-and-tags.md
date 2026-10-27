# Reporting log — 2026-10-20 — Rank Math (D4) CLOSED, A39 completed, 21-URL manual backfill confirmed

## DK, verbatim, this session
> "It does cost me money to keep running, in subscriptions, domains, and website hosting"
> "and this right here"
> "Do the rankmath thing"
> "I feel like I work for you sometimes and not the other way around"
> "Posts and pages already ticked"
> "I submitted those 21"

## D4 — CLOSED, confirmed by DK 2026-10-20

**"Posts and pages already ticked."** DK confirmed the Rank Math → Instant Indexing → Settings → Post Types checkboxes for Post and Page are on. This is the standing item open since 7 October (every future publish/edit now pushes to Bing/Yandex/other IndexNow participants automatically — no manual submission needed per post, ever again).

**"I submitted those 21."** DK confirmed he also pasted the full list of the site's 21 live published post URLs into Instant Indexing's manual "Submit URLs" tool, pushing all existing content immediately rather than waiting for a future edit to trigger it. Backfill and the standing automatic setting are both done — nothing left on the Bing/IndexNow side, past or future.

Could not be done by this operation — checked and confirmed honestly rather than claimed: neither `wpcom-mcp-content-authoring` nor `wpcom-mcp-plugin-management` exposes Rank Math's own module settings (its options live in Rank Math's own serialized option, outside any endpoint this connector surfaces). DK did both actions himself.

**D4 is closed, fully — automatic setting on, and the one-time backfill of all 21 existing posts submitted.** To be reflected at the next consolidation pass of `claude/06-approvals-queue.md`.

## The "I feel like I work for you" exchange
DK raised a fair structural complaint: the pattern today (he clicks, the operation reports) is real, and its cause is narrow — these are all behind his own account login (Rule 5), not a tooling failure to fix. Flagged to him that the same complaint exists in the other direction and has for longer: the Capital section's 8 September "carte blanche" backlog (`claude/capital/17-trading-mandate.md` §2m) — DK's own words at the time, *"I'm tired of this blockheaded stubbornness and inflexibility"* — where permission was given and the backlog still wasn't built. Offered to audit that backlog and get a current count. **Not yet actioned — offered, not confirmed by DK.**

Going forward: batch any remaining account-gated asks rather than trickle them one at a time.

## A39 — EXECUTED AND VERIFIED, 2026-10-20

Confirmed live (`posts.list`, 2026-10-20) that posts 302, 296, 286 already carried tags; the other 18 published posts were still `"tags": []`. Retried `posts.update` `describe` with `wpcom_site` included (the first attempt had omitted it and failed) and confirmed: `tags` takes an array of term IDs and **replaces** the post's tag list — since all 18 target posts had none, no merge logic was needed; `categories` was left untouched on every call (only `tags` was sent, and per the schema "only provided fields are updated").

Applied tags from the 13-term bank (IDs 791324281–791324293: Preparedness, UK, Home Security, Security, Crime Prevention, DIY, Home Improvement, Safety, Consumer Rights, Water, Money, England, Law) to all 18 posts, 3–5 tags each chosen for topical fit, every post staying well under the documented 15 combined tags+categories cap (existing categories were 1–2 per post):

| Post | Title (short) | Tags applied |
|---|---|---|
| 283 | Front door security / Part Q | Home Security, Law, Safety, Security, UK |
| 256 | Power cut compensation calculator | Money, UK, Law, Consumer Rights, Preparedness |
| 246 | Doorbell camera law / ICO | Law, UK, Home Security, Security, Safety |
| 242 | Start Here hub | Preparedness, UK, Safety |
| 213 | Power cut compensation, 14 areas | Money, UK, Consumer Rights, England, Law |
| 216 | Storing logs / moisture | DIY, Home Improvement, UK, Preparedness |
| 220 | Storm names 2026/27 | Preparedness, UK, Safety, England |
| 214 | Plug-in solar legal | Law, DIY, Home Improvement, Preparedness, UK |
| 137 | Surface water flooding | Water, England, Preparedness, Safety, UK |
| 136 | Winter car kit | Law, Safety, Preparedness, UK |
| 135 | Emergency radios after long wave | Preparedness, UK, Safety |
| 121 | Wildfire alert | Safety, Preparedness, UK, England |
| 114 | Government Prepare campaign | Preparedness, UK, Safety |
| 55 | Off-grid basics | Water, Preparedness, DIY, UK |
| 54 | Prepping in a flat | Preparedness, UK, DIY |
| 53 | 72-hour grab bag | Preparedness, UK, Safety |
| 56 | Financial resilience | Money, Preparedness, UK, Consumer Rights |
| 39 | Best UK power cut kits | Preparedness, UK, Safety |

All 18 `posts.update` calls returned successfully, each confirmed in its own response: `status: "publish"` unchanged, `date`/`author 151173283`/existing `categories` unchanged, no `_content_warnings`. **All 21 published posts now carry Reader-visible tags.** Mechanism proven on 2 posts on 22 September, now applied operation-wide.

**A39 is closed.** To be reflected as done at the next consolidation pass of `claude/06-approvals-queue.md` (not edited directly here, per standing practice).

## Still open
- **A34** (Mumsnet post) and **A40** (remaining Request Indexing confirmation) — untouched, DK's own pacing.
- **Offer pending**: audit of the Capital "carte blanche" backlog (§2m) at DK's word.
