# Five days, six people

Submission closes **18 Oct, 15:00 UTC — 20:30 IST**. Written 13 Oct. The engine already works and
the headline number is already measured, so almost nothing remaining is on the engine's critical
path. The risk is the other half of the submission: a video, a deck, a cover image, a live URL
and five written answers the health track demands. None of that existed this morning.

Owners are blank on purpose. Fill one name per line and do not split a lane across two people —
every lane below can be finished by one person without waiting on another.

## The lanes

| # | Lane | Owner | Why it is separable |
|---|---|---|---|
| 1 | Engine and the GPU runs | lead | Needs the credits and the endpoint. Nobody else should touch `src/askfirst/model.py`. |
| 2 | Variants, module B | ____ | Pure CPU. CIViC is already downloaded; ESM-2 is MIT and runs on a laptop. No overlap with lane 1. |
| 3 | The page | ____ | `ui/index.html` is one file with no build step. Talks to the API over three endpoints that are already frozen. |
| 4 | Deck and cover image | ____ | Needs the numbers, which are in `docs/results/`. Does not need the code to run. |
| 5 | Video | ____ | Script from the deck, capture from the deployed URL. Last to finish, first to be scripted. |
| 6 | Submission and QA | ____ | The five written answers, the licence sweep, the form fields, and being the stranger who breaks it. |

## Day by day

**Tue 13 — the floor.** Lane 6 claims the three AMD credit grants and reports, per account,
whether the balance is visible under Billing. Lane 3 reads the API contract. Lane 4 drafts the
deck skeleton against `docs/results/2026-10-13-the-refusal-works.md` and nothing else. Lane 2
gets ESM-2 producing a log-likelihood for one protein sequence, any sequence.
*Checkpoint: the Space is live on CPU with the curve rendering.*

**Wed 14 — the demo exists.** Lane 3 builds the refusal view: the dial, the ranked gaps with cost
and minutes, the panel saying what the answer rests on. Lane 2 maps one HGVS string to a protein
position by hand, end to end, and writes down how long it took — that number decides whether
module B ships. Lane 1 brings a droplet up the hour credits land and runs the proposer go/no-go.
*Checkpoint: a stranger can open the URL and watch it refuse a thin case.*

**Thu 15 — the number that needs AMD.** Lane 1 runs model confidence against the naive Bayes
margin on the risk-coverage curve. This is the only claim that genuinely requires the hardware,
so it gets a whole day and a snapshot-and-destroy at the end of it. Lane 4 has a full deck with
real figures. Lane 6 writes the five health-track answers.
*Checkpoint: one table comparing the two confidence signals at matched coverage.*

**Fri 16 — freeze.** No new features after today. Lane 3 polishes and tests on a phone. Lane 2
ships module B or cuts it, in writing. Lane 5 records the first full take. Lane 6 runs the stranger
test: fresh browser, no instructions, nothing installed, and writes down every place it was
confusing.
*Checkpoint: feature freeze. Only fixes after this line.*

**Sat 17 — the video.** Lane 5 cuts the final video. Lane 4 locks the deck and exports the cover
image. Lane 1 re-runs every number quoted in the deck against the committed scripts and signs off
on each one or strikes it. Lane 6 fills the form and saves a draft.
*Checkpoint: every number on a slide traces to a file in `docs/results/`.*

**Sun 18 — submit by 18:00 IST.** Two and a half hours of slack before the deadline, not zero.
Lane 6 submits. Everyone else re-opens the live URL from their own machine and confirms it works.

## Kill criteria, agreed in advance

- **Advice feature:** under 40% recall at k=10 with a real model, the ranked questions stay in the
  product as a visible aid and come out of the claims. The refusal does not depend on it.
- **Module B:** if a single HGVS-to-protein mapping takes over two hours on Wednesday, cut it. It is
  a demo, not a measurement — 182 contested CIViC groups cannot carry a headline.
- **GPU:** if credits have not landed by Friday morning, the submission ships on the CPU-measured
  curve with the droplet script and the serving config in the repo, and says plainly that the
  model path is written and unrun. Do not fake a number.
- **The curve stays.** If a late result contradicts the 21% to 85.3% figure, the contradiction goes
  in `docs/results/` with a date on it. Nothing gets quietly deleted.

## What nobody should do

Rewrite the ranking objective. Add a second dataset. Switch the UI to a framework. Retry any of
the four dead ends in `docs/STATE.md` — each one cost half a day and the result is written down.
