---
title: askfirst
emoji: 🩺
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Finds the missing fact that would change the answer, and refuses until it has it
---

# askfirst

Not a diagnosis tool. It sits in front of whatever model makes the call and answers a narrower
question: **is there enough here?** When there isn't, it refuses, names what to go and get, and
hands the case to a person.

The curve on the page is measured on 1,500 held-out DDXPlus patients across 49 conditions.
Answering every case gets 21.0% right. Answering only the most confident tenth gets 85.3% right
and costs 94% less, because the wrong confident answers are the expensive ones.

Source, every measurement and every dead end: https://github.com/shivang-goliyan/askfirst

No clinician has reviewed any output. This is a research prototype.
