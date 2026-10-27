# Search Console recheck — 2026-10-07

**Context:** DK asked to recheck G3 (Search Console indexing) nearly a month after the original 14 September check. He pulled fresh screenshots of the Page Indexing report and the Sitemaps report himself.

## 14 September (original G3 finding, for comparison)
~59 flagged pages total. Breakdown: Discovered — currently not indexed 45 · Excluded by noindex 5 · Page with redirect 5 · Not found (404) 2 · Crawled — currently not indexed 1 · Blocked by robots.txt 1.

## 7 October (this recheck, DK's screenshot 1 — "Why pages aren't indexed")
77 flagged pages total. Breakdown: Discovered — currently not indexed **62** · Page with redirect 7 · Excluded by noindex 5 · Not found (404) 2 · Blocked by robots.txt 1 · Crawled — currently not indexed 0.

Validation status on the "Discovered — currently not indexed" row: **Started**, trend line **upward**.

## 7 October (DK's screenshot 2 — "Submitted sitemaps")
Two sitemaps on file, both status **Success**:
- `sitemap.xml` — submitted 29 Aug 2026, last read **6 Oct 2026**, 93 discovered pages
- `sitemap_index.xml` — submitted 29 Aug 2026, last read **4 Oct 2026**, 39 discovered pages

These are two different sitemap systems, not one sitemap read twice — robots.txt (fetched directly, 2026-10-07) declares three separate `Sitemap:` lines: `sitemap.xml`, `news-sitemap.xml`, and `sitemap_index.xml`. `sitemap_index.xml` is Rank Math's (confirmed by direct fetch — it points to `post-sitemap.xml`, `page-sitemap.xml`, `category-sitemap.xml`, generator comment confirms Rank Math). `sitemap.xml` is a separate, larger set — almost certainly WordPress.com/Jetpack's own native sitemap running in parallel to Rank Math's. The discovered-page counts differ (93 vs 39) because they're genuinely different files with different coverage, not a stale duplicate.

## Reading

- Redirect/noindex/404/robots.txt counts essentially unchanged since 14 Sept (redirect +2, everything else flat or down 1) — the technical housekeeping side of the site hasn't shifted and isn't the issue.
- The backlog that matters — "Discovered — currently not indexed" — grew from 45 to 62 (+38%) over 23 days. Total flagged pages grew from ~59 to 77.
- Both sitemaps show Status: Success and were read within the last 1–3 days (4 and 6 Oct) — Google is actively and recently fetching them. This rules out "Google has stopped looking at the site" as an explanation; it is looking, repeatedly, and still not indexing most of what it finds.
- Running two parallel sitemap systems (Jetpack's native one + Rank Math's) isn't necessarily a fault — Google handles multiple declared sitemaps fine — but it's worth knowing it exists before anyone goes looking for "the" sitemap and only checks one. Not flagged as broken, just noted so it isn't mistaken for an error later.
- Independently corroborated the same day via live search: `site:lockedandstocked.co.uk` and a quoted domain+topic search both returned **zero results from the site** (confirmed via WebSearch, 2026-10-07, before DK's screenshots were requested).
- robots.txt fetched directly 2026-10-07: clean, nothing disallowing Googlebot, only the already-agreed AI-crawler blocks present.
- The "three weeks old, no inbound links, this is expected" explanation given for the original 14 Sept finding no longer fits cleanly — the site is now over a month old, is being actively re-crawled, and the backlog is getting worse rather than clearing. Not evidence of a technical fault — evidence that passive patience alone is not resolving it.

## Remediation — D2 (Request Indexing), D3 (Bing Webmaster Tools — DONE), D4 (IndexNow — status to confirm)

Both D2 and D3 require DK's own account access (Rule 5) and were handed to him as concrete steps on 2026-10-07, with a prioritised URL list drawn from the live `posts.list` (21 published posts confirmed).

**D2 progress:**
- 2026-10-07: first batch of 8 — homepage, start-here hub (242), the power-cut calculator (256), the 14-areas power-cut post (213), and the four most recent posts (302, 296, 286, 283).
- 2026-10-08/09: DK confirmed ("Done those now") the second batch of 9 given in the 2026-10-08 reminder — doorbell camera (246), log storage (216), storm names (220), plug-in solar (214), surface water flooding (137), winter car kit (136), emergency radios (135), wildfire alert (121), Prepare campaign (114).
- **17 of 21 posts now submitted for Request Indexing.** 5 remain: off-grid basics (55), flat prepping (54), 72-hour grab bag (53), financial resilience (56), power cut kits guide (39).
- Status of D4 (Instant Indexing toggle) not yet confirmed by DK as of this update — asked directly, answer pending.

**D3 (Bing Webmaster Tools): DONE — DK confirmed 2026-10-07**, site added/imported from Google Search Console.

**D4 (IndexNow — the distribution plan's `[UNVERIFIED]` item, now resolved as a method, action status unconfirmed):** Rank Math — already running this site, confirmed via the sitemap generator tag — ships a free, built-in "Instant Indexing" module using the IndexNow protocol (Rank Math SEO → Instant Indexing → Settings, select Posts/Pages). Auto-generates its own API key, no extra account needed; once enabled, automatically submits every post to Bing/Yandex/other IndexNow-participating engines on publish or edit — no manual action per post, going forward. Given to DK 2026-10-07/08 as the answer to "won't I have to do every post manually from here on." **Important limit: Google does not participate in IndexNow**; Google's own Indexing API is restricted by Google's terms to JobPosting/BroadcastEvent structured data only, so there is no equivalent automatic push for Google — it stays on sitemap re-crawl (active, every 1-3 days) plus occasional manual Request Indexing.

## Unresolved / still DK's to action (Rule 5, account access)
- **D2** — 5 posts remaining (listed above) — small enough for one more sitting, well under the daily cap.
- **D4** — confirm whether Rank Math's Instant Indexing module has been turned on. Asked DK directly 2026-10-09.

## Relevance to the live Grok-suggestions discussion (7 October)
This directly corroborates the risk flagged in the Grok assessment: if nothing is being surfaced by Google organically, a new tool/calculator built on the site has the same invisibility problem a new post does. Distribution that doesn't depend on search ranking is not optional while this backlog persists — it's the only way anything new reaches anyone in the near term.

**Status: G3 reopened, remediation nearly complete.** Originally marked closed 14 September; the 7 October recheck showed the underlying condition had worsened, not resolved. D3 done same day. D2 is 17 of 21 posts through as of 9 October, 5 left. D4 (IndexNow) identified as the standing fix for Bing — status of the toggle itself unconfirmed. To be folded into the approvals queue (`claude/06-approvals-queue.md`) at the next successful consolidation round — not edited directly here per the standing practice of not doing whole-file rewrites of that document outside a dedicated consolidation pass.
