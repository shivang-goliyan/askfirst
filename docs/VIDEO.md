# The video — three minutes, timed

Read it out loud with a stopwatch before recording. The script below runs about 3:15 at a normal
speaking pace. If the platform caps at three minutes, cut the second domain — it is the only beat
that stands alone, and the link in the submission copy covers it. Record the screen capture first and narrate over it;
narrating live while clicking produces dead air and misclicks.

Capture from the **deployed URL**, never localhost. One browser window, no tabs, no bookmarks bar.

---

**0:00-0:25 — the failure, on screen**

*On screen:* the syringe photographs, three of them side by side with the model's answers overlaid.

> We gave a commercial vision model fifteen photographs of real syringes and told it that "unknown"
> was an acceptable answer. It was wrong on nine. It said unknown zero times. It read one millilitre
> from an empty syringe. And it gave two different answers to the same image file — byte-identical,
> same checksum. The problem isn't that it was wrong. It's that nothing in the output told us which
> of the fifteen to trust.

**0:25-0:45 — what it is**

*On screen:* the five-step diagram, built up one step at a time.

> askfirst doesn't diagnose. It sits in front of whatever model makes the call and answers a
> narrower question: is there enough here? It takes a record apart, scores it with an open model,
> removes one fact at a time to see what the answer actually rests on — and when the answer is
> unstable, it refuses, and tells you what to go and get.

**0:45-1:20 — the live demo, backwards**

*On screen:* the live page, first patient, all eleven findings in. Then click findings off, one at
a time, until it stops answering.

> This is a real patient the model has never seen — held out from the fitting set and from the set
> every number on this page was measured on. Eleven findings in, it answers, and it's right.
>
> Now take the record apart. Nine findings. Seven. Five — still answering, less sure. Three, and it
> stops. And look at the reason it gives: not "I'm not confident", but *"only about twenty-three
> percent of a record — too little to judge the answer by, whatever the confidence says."*
>
> Nobody told it that. It worked out how much of the record is missing. The only thing you set
> here is how right it has to be. It won't answer, it hands the case over, and it arrives with a
> work list.

**1:20-1:35 — why that matters more than it sounds**

*On screen:* the completeness read-out, then the table from slide 6.

> We used to ask the user how complete their record was, which is absurd — that's the problem, not
> an input to it. So we measured whether one threshold could work everywhere, and found the word
> "calibrated" was doing work it hadn't earned. The confidence is honest on a full record and
> forty points underconfident at forty percent evidence. A cut-off picked on complete records
> promises ninety-five and delivers forty-eight on a tenth of one.
>
> Thirty thousand records, nobody saying how complete any of them are. Answer everything: sixty-seven
> percent right, nine thousand eight hundred and seventy-four wrong. This rule: ninety-nine point six
> percent right, forty-five wrong, on the third of cases it chooses to answer.

**1:35-1:55 — what to go and get, and the thing we got wrong**

*On screen:* the "go get" table, the answers column visible.

> Here's what to go and get, ranked. And the ranking is the part I'd want a judge to push on,
> because our first four attempts at it were worse than guessing.
>
> The published approach is expected information gain. We implemented it, and over four thousand
> patients it scored worse than asking nothing at all — thirty-nine point nine against forty-two
> point nine. It's an expectation taken under the model's own beliefs, and on a thin record those
> beliefs are wrong.
>
> What works is stupider. Rank by how many answers the question even admits. Seventy-two point
> five percent. In clinical terms: characterise what you already have before asking about one more
> symptom.

**1:55-2:20 — the measurement**

*On screen:* the completeness selector, dragged from "complete" down to "20% in", then the cost table.

> This is measured, not demonstrated — and we measured it wrong the first time, so let me show you
> the version that survived. Six thousand held-out patients, forty-nine conditions. The scorer is
> ninety-nine point six percent right when it has the whole record. Then we take the record away.
>
> With a fifth of the evidence — about three findings — that same model is thirty-nine point nine
> percent right. Refusing the least confident cases takes it back to seventy-three point five.
>
> And the prices aren't ours. A triage call is ten to twenty-seven dollars; a confident wrong
> answer, costed from the published harm rate and the average paid claim, is four thousand to a
> hundred and sixty-seven thousand. So a wrong answer is worth two hundred handovers, not twenty.
>
> Which breaks the objective, honestly: above about four thousand to one, the cheapest policy is
> to answer nothing at all. Clinicians are finite, so that's not an option. Here's the number that
> survives. Answer everything and you put three hundred and thirty wrong answers into every
> thousand records. Hold a ninety-five percent bar and you put one point seven — and still take a
> third of the queue off a person's desk.

**2:20-2:40 — the second domain**

*On screen:* `askfirst.kgbnetwork.com/#level=B`, then click back to E.

> Same engine, different evidence. These are contested cancer-variant calls — cases where a public
> knowledge base disagrees with itself — and we put a protein language model's score in as one
> removable piece of evidence. This dial is the strength it's granted.
>
> At supporting strength, where the ACMG guidelines cap computational evidence, nothing moves.
> Nudge it to clinical strength and five of eleven calls flip, and the prediction lands on top
> every time. That one — documented evidence that a drug works, overruled by a conservation score.
> The cap isn't bureaucracy. It's the thing standing between a predictor and the call.

**2:40-2:55 — why AMD**

*On screen:* the vLLM request with `echo=True`, the logprobs coming back, the MI300X.

> This only works on open weights. The whole product is built on the model's distribution —
> entropy, information gain, a calibrated threshold. A closed API gives you text, not a
> distribution. So it runs on vLLM on an MI300X, and we read the prompt logprobs directly.
>
> And a better model doesn't make the answers cheaper. It makes more of them answerable. That's
> what the hardware buys, and we have the CPU baseline to measure it against.

**2:55-3:15 — the limits, said out loud**

*On screen:* the repo's results directory, the dates visible.

> What we won't claim. No clinician has reviewed this and it is not medical advice. The data is
> synthetic, and a linear model gets ninety-nine point six percent on it, which tells you how
> synthetic. On a complete record this product is nearly pointless and we say so on the page.
> Eleven variant groups is a demonstration, not a benchmark. MediQ at NeurIPS posed this problem
> before us.
>
> And the two biggest corrections are ours. Our first headline measured our own weak baseline —
> two of our files disagreed, we chased it, killed the claim and re-ran everything. Then we found
> three bugs in the ranking measurement, every one of them in our favour, and fixing them made the
> result we were beating worse rather than better. Both are in the repo, dated, in the order they
> happened.
>
> It knows when it doesn't know. That's the product.

---

## Recording notes

- 1080p minimum, 30fps. Browser zoom at 125% so text is readable on a phone.
- No background music under the numbers. Music over the first 25 seconds only, if at all.
- Do not speed up the live demo. The pause while it refuses is the point of the film.
- If a take fumbles a number, stop and restart the section. A wrong number in the video outlives
  the hackathon.
- Export under the platform's size limit and check it plays in a fresh browser before submitting.
