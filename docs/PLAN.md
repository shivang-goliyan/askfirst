# Five days, one pair of hands

Submission closes **18 Oct, 15:00 UTC — 20:30 IST**. Rewritten 13 Oct, when the team shape became
clear: this is a **single-builder project**. Other people contribute input and review, not commits.
The earlier version of this file assumed six parallel lanes and was wrong, so it is gone.

That changes the plan in one way that matters: **nothing is parallel, so everything needs a cut
order agreed before the week starts, not during it.** It is written below and it is binding.

The engine already works and the headline number is already measured. The risk was never the
engine — it is the rest of a submission: a live URL, a deck, a video, a cover image and the written
answers the health track demands. As of today the URL is containerised and verified, and the deck,
video and safety answers exist as specs.

## Where the credits sit

Applied 13 Oct, expected within one to two days, three accounts. So **the GPU work cannot start
before the 14th or 15th**, and the plan is built to survive it never starting at all. Everything
measured so far ran on CPU, and the headline curve is baked into the app — the page does not need
a droplet to be alive.

## Day by day

**Tue 13 — the floor.** Space live on CPU with the curve rendering. The container is already built
and verified; what remains is the account and one push. Check the credit balance on all three
accounts under Billing, which does not populate on its own.
*Done when a stranger can open a URL and watch it refuse a thin case.*

**Wed 14 — the two things judges actually see.** The refusal view on the page: the dial, the ranked
gaps with cost and minutes, the panel saying what the answer rests on. Then the deck, built as a
file in this repo rather than in a slide tool, so every number on it can be regenerated instead of
retyped.
*Done when the deck renders eleven slides and each figure traces to `docs/results/`.*

**Thu 15 — the GPU day, the hour credits land.** Serve the open model, then in order: the proposer
go/no-go at the 40%-recall bar, then model confidence against the naive Bayes margin on the
risk-coverage curve. The second one is the only claim that genuinely requires the hardware, so it
gets the bulk of the budget. Snapshot and destroy the droplet at the end of the day — a powered-off
droplet still bills.
*Done when one table compares the two confidence signals at matched coverage.*

**Fri 16 — freeze.** No new features after today. Fix what the stranger test finds, test the page
on a phone, and ship or cut module B in writing. Re-run every number quoted anywhere against the
committed scripts; strike any that does not reproduce.
*Done when feature freeze holds and every quoted number has been re-derived today.*

**Sat 17 — the video and the cover.** Record against the deployed URL, not localhost. Script is in
`docs/VIDEO.md` and runs about 2:50 — read it with a stopwatch before recording. Export the cover
image. Fill the submission form and save it as a draft.
*Done when the video plays in a fresh browser and the draft is saved.*

**Sun 18 — submit by 18:00 IST.** Two and a half hours of slack, not zero. Then re-open the live
URL from a phone on mobile data and confirm it still works.

## The cut order, agreed in advance

When the week runs short, things come off the top of this list, in this order, and the cut gets
written down rather than quietly made:

1. **Module B / ESM-2.** A demo on 182 contested CIViC groups. It cannot carry a headline and it
   is the only piece whose removal costs no claim. **Hard gate: if one HGVS-to-protein mapping is
   not working within two hours of starting, it is cut that same day.**
2. **The question-ranking claim.** Already measured neutral — 28.4% against 26.0% for asking at
   random, intervals overlapping. The feature stays visible in the product as an aid; the claim
   comes out of the deck without any further work.
3. **The MedQA cross-check.** Worth having to answer "your data is synthetic", but the limitation
   can be stated honestly instead of answered empirically.
4. **Page polish beyond one phone screen.**

## What never gets cut

The live URL. The refusal curve and its price, because that is the whole submission. The video,
the deck and the cover image, because without them there is nothing to judge. The safety answers
in `docs/SAFETY.md`, because the track requires them. And **an honest statement of limits** — four
dead ends with dates, the 92.8% floor rather than the 98.7% headline, the synthetic-data caveat,
and the fact that MediQ posed this problem first.

## What nobody should do, including on day five

Rewrite the ranking objective. Add a second dataset. Switch the page to a framework. Retry any of
the four dead ends in `docs/STATE.md` — each one cost half a day, and the result is written down so
it never has to cost that again.
