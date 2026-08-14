# Text probes over frozen multilingual MiniLM — v3 corpus
Generated 2026-08-12 · encoder `paraphrase-multilingual-MiniLM-L12-v2` · transform `sections_chunked_mean_60w_l2_v2` · dim 1920
Frame: **1559 resumes** after dropping 90 duplicated prose lines and 41 duplicated label lines. Both files are appended to by resumable jobs that were run more than once; left in, those rows would train with double weight.
## Seniority head — text only, label `band_target`
1559 resumes, 932 distinct occupations, 5-fold GroupKFold over the occupation.
Label distribution: {'intern': 486, 'mid': 309, 'junior': 379, 'senior': 385}
### Probe, sections + document, tenure visible (production)
- accuracy **75.9%** · ±1 band 94.5% · macro-F1 0.749
- predicted distribution: {'junior': 368, 'intern': 486, 'senior': 404, 'mid': 301}
```
true \ pred     intern  junior     mid  senior
intern             394      56      23      13
junior              59     269      41      10
mid                 17      37     197      58
senior              16       6      40     323
```
### Probe, sections only, no month count anywhere
- accuracy **74.3%** · ±1 band 94.0% · macro-F1 0.734
- predicted distribution: {'junior': 381, 'intern': 470, 'senior': 406, 'mid': 302}
```
true \ pred     intern  junior     mid  senior
intern             376      68      29      13
junior              58     268      42      11
mid                 24      40     189      56
senior              12       5      42     326
```
### Probe, sections + document with tenure stripped
- accuracy **74.7%** · ±1 band 94.3% · macro-F1 0.736
- predicted distribution: {'junior': 369, 'intern': 478, 'senior': 408, 'mid': 304}
```
true \ pred     intern  junior     mid  senior
intern             384      61      26      15
junior              58     266      47       8
mid                 20      38     190      61
senior              16       4      41     324
```
### Baselines on the same rows and the same label
- `rule_based_seniority`: accuracy **70.4%** · ±1 100.0% · macro-F1 0.696
- majority class (`intern`): accuracy 31.2% · macro-F1 0.119
```
true \ pred     intern  junior     mid  senior
intern             405      81       0       0
junior              24     221     134       0
mid                  0       0     247      62
senior               0       0     160     225
```
**The rule comparison is biased in favour of the rules and must be reported that way.** `rule_based_seniority` thresholds `effective_months_experience`, and the generator built each resume from `total_months_design` — the very number the rules read. The rules are scored against a label derived from their own input, while the probe has to recover the band from words. The tenure-stripped row above is the probe measured under the same handicap the rules never face.
### Second ablation: resumes that name their own level
The generator was allowed to write the band into the job title on a 22% slice (`may_state_seniority`), so on those rows the answer is partly readable off the `roles` block. Splitting the same out-of-fold predictions:

| slice | n | accuracy | ±1 | macro-F1 |
|---|---|---|---|---|
| title may state the level | 339 | **76.4%** | 94.7% | 0.754 |
| title must not state it | 1220 | **75.7%** | 94.5% | 0.747 |

The gap is +0.7 points. The unstated slice is 78% of the corpus and is the number to quote for a resume that does not advertise its own level; the stated slice is what a real resume with `Senior` in the title would give. Both are legitimate inputs — a real candidate does write their own title — so neither slice is leakage, but reporting only the pooled figure would hide which one is doing the work.
### Cross-writer transfer on `band_target` — the mandatory confound check
`band_target` is an instruction to a writer, not a measurement of the output. Fitting the head on one writer and scoring it on the other asks directly whether both writers answered that instruction the same way — no teacher label involved, so the whole corpus is available rather than the labelled slice.

| trained on | n train | tested on | n test | accuracy | ±1 | macro-F1 |
|---|---|---|---|---|---|---|
| `llama-3.1-8b-instant` | 1185 | `mistral-small-latest` | 326 | **78.2%** | 94.8% | 0.773 |
| `mistral-small-latest` | 326 | `llama-3.1-8b-instant` | 1185 | **62.4%** | 90.3% | 0.612 |

**The two directions are not comparable.** One trains on 1185 rows and the other on 326, so the weaker direction is measuring sample size as much as writer style. The well-powered direction — `llama-3.1-8b-instant->mistral-small-latest` at 78.2% — is the one to read, and averaging the two understates the head.

Within-writer reference on the same rows, occupation held out: `llama-3.1-8b-instant` 72.4% · `mistral-small-latest` 74.2%

Cross-writer accuracy averages 70.3% against 73.3% within writer, a drop of **3.0 points**. Chance on 4 classes is 25%.

The number that matters for the defence is the cross-writer one, and it is lower than the headline. A real user is always a third writer the head has never read, so cross-writer is the honest estimate of what production delivers on `band_target` and the pooled figure is an upper bound. Both go in the report; quoting only the pooled figure would be a claim about generalisation that this corpus does not support.

The gap is small enough to pool the writers: a head fitted on one writer's prose still recovers the other writer's planted level far above chance, and neither direction collapses. `writer_model` stays in the metadata as a covariate to watch, not as a stratum the training has to respect.
### Against the teacher labels, as fine-resolution validation
On the 257 rows the LLM teacher has judged, the probe agrees 66.5% exactly and 96.1% within one band. The teacher is the validation set here, not the label: human review put `band_target` at ~94.9% against ~78.5% for the teacher (handoff 7.2.2d).
### Against the 46 human verdicts, the only non-model truth
- probe vs human: accuracy **82.6%** · ±1 97.8% (n=46)
- `rule_based_seniority` vs human: accuracy 67.4% · ±1 100.0%
This stratum oversamples teacher/generator disagreements by design, so it understates both decision rules; it is here because it is the one comparison neither side can game.
## Quality head — 78% of the score, today five regex flags
### Version A — label `quality_target`, 3 classes, every `q` resume
691 rows, 518 occupations. accuracy **75.1%** · ±1 98.6% · macro-F1 0.755
- label distribution: {'good': 235, 'poor': 220, 'fair': 236}
- predicted distribution: {'good': 234, 'poor': 219, 'fair': 238}
```
true \ pred     poor  fair  good
poor             200    15     5
fair              14   156    66
good               5    67   163
```
### What the incumbent heuristic scores on the same rows
`_heuristic_score` is the decision worth 78% of the score today. Its mean output per planted quality level, against the probe's, on identical rows:
| planted | n | `_heuristic_score` | probe (policy map) |
|---|---|---|---|
| poor | 220 | 41.4 | 32.8 |
| fair | 236 | 52.4 | 59.9 |
| good | 235 | 57.8 | 70.4 |
The heuristic reads links, metric patterns and action verbs, which the degradation instruction does not remove, so it is close to flat across levels it is supposed to separate.
### Version B — teacher `impact` 1-5, fine resolution
257 labelled rows, 235 occupations. MAE **0.62** against 1.30 for predicting the mean · exact 48.6% · ±1 93.0% · Spearman 0.859
- label distribution: {1.0: 58, 4.0: 27, 2.0: 55, 5.0: 68, 3.0: 49}
### Version B — teacher `clarity` 1-5, fine resolution
257 labelled rows, 235 occupations. MAE **0.39** against 0.53 for predicting the mean · exact 68.9% · ±1 100.0% · Spearman 0.764
- label distribution: {3.0: 65, 4.0: 122, 5.0: 70}
### Version B — teacher `ats` 1-5, fine resolution
257 labelled rows, 235 occupations. MAE **0.42** against 0.53 for predicting the mean · exact 66.1% · ±1 99.6% · Spearman 0.731
- label distribution: {3.0: 64, 4.0: 124, 5.0: 69}
### Cross-writer transfer on `quality_target` — the mandatory confound check
`quality_target` is an instruction to a writer, not a measurement of the output. Fitting the head on one writer and scoring it on the other asks directly whether both writers answered that instruction the same way — no teacher label involved, so the whole corpus is available rather than the labelled slice.

| trained on | n train | tested on | n test | accuracy | ±1 | macro-F1 |
|---|---|---|---|---|---|---|
| `mistral-small-latest` | 326 | `llama-3.1-8b-instant` | 317 | **65.6%** | 95.9% | 0.638 |
| `llama-3.1-8b-instant` | 317 | `mistral-small-latest` | 326 | **63.5%** | 96.3% | 0.638 |

Within-writer reference on the same rows, occupation held out: `mistral-small-latest` 76.1% · `llama-3.1-8b-instant` 69.7%

Cross-writer accuracy averages 64.6% against 72.9% within writer, a drop of **8.3 points**. Chance on 3 classes is 33%.

The number that matters for the defence is the cross-writer one, and it is lower than the headline. A real user is always a third writer the head has never read, so cross-writer is the honest estimate of what production delivers on `quality_target` and the pooled figure is an upper bound. Both go in the report; quoting only the pooled figure would be a claim about generalisation that this corpus does not support.

The gap is wide enough to name as a limitation. Part of the pooled score is writer style rather than the construct, so the head is not yet demonstrably writer-invariant. Fixing it needs writer diversity in the corpus, which two generators cannot provide — not a different head. Until then the cross-writer row is the number to quote.
### The measured ceiling on splitting `ats` from `clarity`
The teacher awards the same number for `clarity` and `ats` on **251/257 (97.7%)** of labelled rows, Pearson **0.978**, and never differs by more than one point. Both also sit in a 3-5 range, never scoring 1 or 2.
So the two heads ship, but the honest claim is narrow. What is fixed is the defect that mattered: `ats` and `clarity` stop being literal copies of `quality_score` (`orchestrator.py:758-759`), a number about a different construct. What is *not* fixed is that they barely differ from each other, and that is a property of the rubric, not of the model — the prompt asks two questions that the teacher answers as one. Separating them needs a rubric that scores keyword hygiene and structure apart from concision, plus a generator whose `poor` instruction degrades formatting and not only content. That is the same limit already recorded for `language` in handoff 7.2.2b, and it is a relabelling job, not a retraining job.
### Reading of the ablation
Version A trains on 691 rows of a label that human review confirmed three ways (human 1.50/2.61/3.64 vs teacher 1.56/3.00/3.96 vs Mistral 1.50/2.73/3.75 across poor/fair/good). Version B trains on the teacher's 1-5 scale, which resolves finer but exists on far fewer rows and inherits the teacher's +0.30 generosity measured against the human. Version A therefore ships as the decision and Version B ships alongside it as the `impact`/`clarity`/`ats` resolution, which is also what finally splits `ats` and `clarity` from being literal copies of `quality_score`.
