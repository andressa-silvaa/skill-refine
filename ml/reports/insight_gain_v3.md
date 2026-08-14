# Insight ordering by measured gain — v3 corpus

Generated 2026-08-12 · 1399 resumes scored through the real production path (sections, signals, `bullet_probe`, `quality_probe`), with `derive_insights` itself deciding which improvements fire.

Mean quality score across the corpus: **59.5**

`gain` is `mean(quality | suggestion absent) - mean(quality | suggestion shown)`: how many points separate resumes that do not have this deficiency from those that do.

| improvement | pooled gain | within-band gain | n shown | n absent | mean when shown | mean when absent |
|---|---|---|---|---|---|---|
| `add_metrics` | **+14.58** | +2.90 | 507 | 892 | 50.2 | 64.8 |
| `use_action_verbs` | **+8.66** | +1.73 | 424 | 975 | 53.4 | 62.1 |
| `fill_core_sections` | **+2.23** | -0.18 | 45 | 1354 | 57.3 | 59.5 |
| `add_education` | **+0.29** | +0.33 | 124 | 1275 | 59.2 | 59.5 |
| `relevant_links` | **-0.46** | -0.08 | 1070 | 329 | 59.6 | 59.1 |
| `add_skills` | **-0.69** | -0.66 | 323 | 1076 | 60 | 59.3 |
| `education_target_gap` | **-3.24** | -0.80 | 270 | 1129 | 62.1 | 58.8 |

## How to read this, and how not to

- **Correlational.** These are score differences between resumes, not the effect of acting on the advice. Nothing here promises a user gains the listed points by following it.
- **The pooled column is confounded by resume level.** A weak resume trips several conditions at once, so part of every pooled gap is just "this resume is weak". The within-band column recomputes the gap inside each quality band, which holds the level roughly fixed and is the number the ordering should lean on.
- **Suggestions that always fire cannot be measured.** A condition that never varies has no contrast group and is dropped from the table; `ats_keywords` fires for every resume with an experience body, so it carries no evidence about its own worth and inherits the floor.
- **The score being predicted is our own.** `quality_probe` reads the same resume text the `bullet_probe` flags read, so "resumes without metrics score lower" is partly one head agreeing with another about the same sentences. That makes this a statement about the number this product publishes, not about how a recruiter reacts. For ordering advice on how to raise the published score it is the right target; as evidence about real hiring outcomes it is none.
- **A negative gain is a finding, not noise.** `education_target_gap` is shown to resumes that score *higher* than the ones it is withheld from, which is what a misfiring condition looks like. It is the suggestion driven by the education keyword lists that ml/reports/education_alignment_v3.md failed to replace, and it currently carries a hand-written `priority=high`.
- **Ordering is stable across both columns except one entry.** Pooled and within-band agree on every rank but `fill_core_sections`, which falls from third to fifth once level is held fixed — its pooled gap was almost entirely "this resume is weak". The shipped table reads the within-band column.
- What this replaces is a hand-written `high`/`medium`/`low` on each branch and the order the `if`s happen to run in. Both were guesses; this is not.
