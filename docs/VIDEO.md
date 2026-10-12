# The video — three minutes, timed

Read it out loud with a stopwatch before recording. The script below runs about 2:50 at a normal
speaking pace, which leaves room to breathe. Record the screen capture first and narrate over it;
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

**0:45-1:25 — the live demo, thin case**

*On screen:* type a thin case into the live app. Chest pain, nothing else. Hit assess.

> One symptom. Watch what it does — it won't answer. It says the record can't support an answer
> yet, and it ranks what's missing: troponin first, at nought point three nine bits of information,
> costing nine units, back in ninety minutes. ECG second. And here's what matters — it also shows
> what the current guess is resting on, so a person can disagree with the reasoning rather than
> just the conclusion.

*Then:* add the troponin. Hit assess again.

> Add the troponin and it crosses its threshold and answers — and it still shows the fields the
> answer depends on. Every case produces a work item. It refuses the answer, never the interaction.

**1:25-2:05 — the measurement**

*On screen:* the risk-coverage curve, then the cost table.

> This is measured, not demonstrated. Fifteen hundred held-out patients, forty-nine conditions,
> two percent chance. Answer every case and it gets twenty-one percent right, with eleven hundred
> and eighty-five confident wrong answers. Answer only the most confident tenth and accuracy goes
> to eighty-five point three, with twenty-two.
>
> Price it — a confident wrong decision at a hundred, a referral to a person at five — and cost per
> case falls from seventy-nine to four point eight two. Ninety-four percent cheaper. We tested seven
> different price ratios; the saving ranges from forty-one to ninety-nine percent, so the result
> doesn't depend on us picking flattering numbers.

**2:05-2:30 — why AMD**

*On screen:* the vLLM request with `echo=True`, the logprobs coming back, the MI300X.

> This only works on open weights. The whole product is built on the model's distribution —
> entropy, information gain, a calibrated threshold. A closed API gives you text, not a
> distribution. So it runs on vLLM on an MI300X, and we read the prompt logprobs directly.
>
> And a better model doesn't make the answers cheaper. It makes more of them answerable. That's
> what the hardware buys, and we have the CPU baseline to measure it against.

**2:30-2:50 — the limits, said out loud**

*On screen:* the repo's results directory, the dates visible.

> What we won't claim. No clinician has reviewed this and it is not medical advice. The data is
> synthetic and we say so. The ninety-eight point seven figure rests on seventy-five cases, so we
> quote ninety-two point eight. The question-ranking half is neutral so far, not proven. MediQ at
> NeurIPS posed this problem before us. And one of our own ranking objectives made results worse
> than asking at random — we measured it, diagnosed it and replaced it, and it's all in the repo
> with dates on it.
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
