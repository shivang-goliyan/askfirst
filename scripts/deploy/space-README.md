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
On a mixed stream of records of undeclared completeness, answering everything gets 67.1% right.
Holding a 95% bar it answers about 35% of them at 99.6% and hands the rest to a person.

(This file said "21.0% to 85.3%, 94% cheaper" until 13 Oct. That came from a naive Bayes that was
retired the same day, and it survived here because this mirror is not deployed on every change.)

Source, every measurement and every dead end: https://github.com/shivang-goliyan/askfirst

No clinician has reviewed any output. This is a research prototype.
