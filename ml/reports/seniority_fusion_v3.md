# Should the seniority probe decide, or keep sharing the decision with the rule?

1559 resumes. The probe row is out-of-fold with occupations held out; the rule and the blend are computed on every row. Mean weight `fuse_seniority` hands to the text: **0.36** (so the rule carries 0.64).

## Against `band_target`, the training label

| decision rule | accuracy | ±1 | macro-F1 | predicted spread |
|---|---|---|---|---|
| probe alone | **67.5%** | 93.5% | 0.665 | intern:461 junior:371 mid:338 senior:389 |
| rule_based_seniority alone | **70.4%** | 100.0% | 0.696 | intern:429 junior:302 mid:541 senior:287 |
| fuse_seniority (production blend) | **64.3%** | 98.1% | 0.641 | intern:353 junior:404 mid:495 senior:307 |

`band_target` flatters the rule: the generator built each resume from a month budget and the rule thresholds months, so it is being scored against a label derived from its own input.

## Against the 46 human verdicts, which neither side can game

| decision rule | accuracy | ±1 | macro-F1 | predicted spread |
|---|---|---|---|---|
| probe alone | **67.4%** | 93.5% | 0.671 | intern:12 junior:16 mid:8 senior:10 |
| rule_based_seniority alone | **67.4%** | 100.0% | 0.611 | intern:15 junior:5 mid:23 senior:3 |
| fuse_seniority (production blend) | **58.7%** | 97.8% | 0.542 | intern:12 junior:10 mid:21 senior:3 |

This stratum oversamples teacher/generator disagreements, so every number in it is pessimistic; what matters is the ordering and the spread column.

**Best macro-F1 against human judgement: probe alone.**

## What this settles

The blend cannot be reported as a model-driven answer while the rule holds ~0.85 of the weight on a well-formed resume — that is a rule with a model advising it, which is the arrangement the project set out to remove. The rule keeps its edge on `band_target` because it reads the generator's own month budget, and that edge shrinks or inverts against human judgement, where a balanced macro-F1 matters more than accuracy on a stratum built out of hard cases.

So the probe becomes the primary decision when its bundle loads, the rule becomes the fallback for when it does not, and `clamp_seniority_vetoes` stays in place. The vetoes are not a competing judgement — they are product safety on absent evidence (never `senior` with no experience section), and they are declared as policy rather than dressed up as inference.
