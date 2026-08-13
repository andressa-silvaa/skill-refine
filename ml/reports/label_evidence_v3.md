# What the paid labels already prove — v3 corpus

Every table here comes from files already on disk. Regenerating any of them costs days of free-tier quota, so they are treated as evidence, not as intermediate output.

## 1. Writer monotonicity — the mandatory confound check
The corpus has two prose writers. `quality_target` is an instruction given to a writer, not a measurement of what it produced, so the label only means one thing if both writers degraded by the same amount. Teacher `impact` per writer per planted level:
| writer | poor (n) | fair (n) | good (n) | monotonic |
|---|---|---|---|---|
| `llama-3.1-8b-instant` | 1.79 (68) | 3.15 (82) | 3.82 (72) | yes |

Teacher coverage per writer, on rows that have a planted quality level: `llama-3.1-8b-instant` 222 labelled / 95 unlabelled · `meta-llama/Llama-3.3-70B-Instruct` 0 labelled / 3 unlabelled · `mistral-small-latest` 0 labelled / 350 unlabelled

**The teacher-label form of this check cannot be completed yet.** Every teacher label so far sits on prose written by one writer, because the labelling job walks the ids in order and the second writer's rows are still in the queue. Comparing a populated row against an empty one would be a fabricated result.

So the check is run in a stronger form that needs no teacher label at all, in `train_text_probes_v3.py`: **train the quality head on one writer's resumes and test it on the other's**. `quality_target` exists for both writers, and if the two writers responded to the same instruction the same way, a head fitted on one must transfer to the other. If they are different treatments under one label, transfer collapses. That is the question the mean-comparison was a proxy for, answered directly and across the whole corpus rather than the labelled slice — see the cross-writer transfer table in the probe report.

And on the human review, which does not depend on the teacher at all:

| writer | poor (n) | fair (n) | good (n) |
|---|---|---|---|
| `llama-3.1-8b-instant` | 1.50 (14) | 2.74 (19) | 3.54 (13) |

The human sample was drawn for label review, not balanced by writer, so these cells are thin; they are here as a direction check on the teacher table above.

## 2. Two annotators from different model families
Deduped first: 34 repeated lines in `labels_rubric.jsonl` and 9 in `labels_mistral.jsonl` came from resumable jobs run more than once.
On the **221** resumes both have judged: band exact 127/221 (57%) · ±1 band 219/221 (99%) · linear-weighted kappa **0.612**.
- band deviation (Mistral minus teacher): `{-2: 2, -1: 89, 0: 127, 1: 3}`
- mean absolute difference per dimension: `impact` 0.48 · `clarity` 0.88 · `ats` 1.05 · `language` 1.65

91 of the disagreements put Mistral one band lower and 3 put it higher. A one-sided error is calibration, not noise: it is a threshold that can be shifted, which is why Mistral is kept as a second annotator instead of being discarded. `language` remains the worst-agreeing dimension, consistent with it being dropped from scope.

## 3. Teacher x prompt ablation, from the probes already paid for
First, what the rubric file actually contains, because it is not one annotator:

- `llama-3.3-70b-versatile`: 147 rows
- `meta-llama/Llama-3.3-70B-Instruct`: 60 rows
- `Meta-Llama-3.3-70B-Instruct`: 15 rows

Those are three endpoints serving the same `Llama-3.3-70B-Instruct` weights, which is why they were allowed to share one file. The table below is the evidence for that decision.

Reference: the **147** rubric rows labelled by Groq `llama-3.3-70b-versatile`. Each row below is scored only on the ids it shares with that reference, so `n` differs by design. A provider is never compared against rows it labelled itself.

| annotator | n | band exact | ±1 | kappa | MAE impact | MAE clarity | MAE ats |
|---|---|---|---|---|---|---|---|
| Hugging Face `Llama-3.3-70B-Instruct` (same weights) | 45 | 93% | 100% | 0.94 | 0.16 | 0.11 | 0.13 |
| SambaNova `Meta-Llama-3.3-70B-Instruct` (same weights) | 19 | 95% | 100% | 0.95 | 0.21 | 0.21 | 0.21 |
| Mistral `mistral-small-latest` (smaller, other family) | 60 | 55% | 98% | 0.61 | 0.43 | 0.87 | 0.98 |
| OpenRouter `Nemotron-3-super-120b` (other family) | 14 | 64% | 93% | 0.65 | 0.36 | 0.79 | 0.79 |
| Gemini `flash-latest` (other family) | 7 | 71% | 86% | 0.63 | 0.29 | 0.57 | 0.29 |
| Groq `llama-3.1-8b` terse (smaller, same family) | 0 | — | — | — | — | — | — |
| Groq `llama-3.1-8b` fewshot (smaller, long prompt) | 0 | — | — | — | — | — | — |
| Groq `llama-3.3-70b` terse probe (self, sanity row) | 0 | — | — | — | — | — | — |

The pattern that decided the labelling plan: the **same weights on another provider** agree with the reference at the level of sampling noise, while a **smaller model on the same prompt** does not. Swapping providers to buy quota is therefore free, and swapping teachers is not.

Rows showing `n = 0` are not failures: the two small Groq probes were run over `gen*` ids and the provider probes over `q*` ids, so they share no resume. That is also why the reference here is the rubric file rather than the 8-row terse probe — reported so the empty cells are not read as a missing measurement. Every `n` in this table is small; these are probes.

## 4. The third vote on the split decisions
`labels_disagree.jsonl` holds 51 resumes where the Groq teacher and Mistral chose different bands. OpenRouter Nemotron voted on 36 of them; 36 have all three bands plus a planted target.
- sides with the Groq teacher: 25/36 (69%)
- sides with Mistral: 10/36 (28%)
- sides with neither: 1/36 (3%)
- lands on the planted `band_target`: 28/36 (78%)

On these same contested rows the Groq teacher hits the planted target 27/36 (75%) and Mistral 7/36 (19%).
Read carefully: this stratum is *selected* for disagreement, so nothing here estimates a corpus average. Within it, the third vote is not neutral — it backs the 70B teacher over Mistral by better than two to one, and it lands on the planted `band_target` more often than it lands on either annotator. Two independent findings follow, and they point the same way as the human review did by a different route: Mistral's one-band-low deviation in section 2 is a calibration bias a third family does not share, and `band_target` is the label the annotators converge toward when they are forced apart. That is the evidence for training on `band_target` and holding the teachers back as validation.

## 5. The human anchor
46 of 46 rows reviewed. Teacher agrees with the human on 29/46 (63%) of the sample, 46/46 (100%) within one band.
- stratum A: 4/20 (20%)
- stratum B: 1/2 (50%)
- stratum C: 24/24 (100%)

Stratum C is the only unbiased estimate; A oversamples disagreements on purpose. That is what makes the extrapolation in handoff 7.2.2d legitimate and the raw sample number misleading on its own.

On `impact`, the dimension behind the 78% pillar: n=46, mean absolute error **0.35** point, bias -0.30 (negative means the teacher is generous). This is the number that lets the quality head claim a human-anchored label rather than a model-anchored one.

| planted quality | n | mean human `impact` |
|---|---|---|
| poor | 14 | 1.50 |
| fair | 18 | 2.61 |
| good | 14 | 3.64 |

Human scores rise with the planted level and the ordering is **monotonic**. A person, reading only the text, recovers the instruction the generator was given — which is what licences `quality_target` as a training label.
