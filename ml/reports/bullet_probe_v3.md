# Per-bullet attribute probe over frozen multilingual MiniLM — v3 corpus

Generated 2026-08-12 · encoder `paraphrase-multilingual-MiniLM-L12-v2` · transform `bullet_mean_l2_v1` · dim 384

**5750 bullets** from 764 resumes, 573 distinct occupations. 5-fold GroupKFold over the occupation, so a resume and its parallel renderings never straddle the split.

Language: {'es-ES': 1884, 'pt-BR': 1869, 'en-US': 1997}

Prose writer: {'llama-3.1-8b-instant': 4523, 'mistral-small-latest': 1227}

## Label noise — the ceiling any head is measured against

716 bullets carry a second annotator of a different model family. A head cannot be expected to exceed the agreement of the labellers that produced its target.

| attribute | annotator agreement | kappa |
|---|---|---|
| `quantified` | 90.1% | 0.77 |
| `outcome` | 81.7% | 0.54 |
| `leadership` | 89.5% | 0.70 |

## Heads, out-of-fold

| attribute | positives | probe acc | probe P | probe R | probe F1 | regex acc | regex P | regex R | majority acc |
|---|---|---|---|---|---|---|---|---|---|
| `quantified` | 2644 (46.0%) | **92.8%** | 0.92 | 0.93 | 0.92 | 84.9% | 0.96 | 0.70 | 54.0% |
| `outcome` | 2777 (48.3%) | **83.8%** | 0.85 | 0.81 | 0.83 | 58.4% | 0.74 | 0.22 | 51.7% |
| `leadership` | 1146 (19.9%) | **85.6%** | 0.60 | 0.83 | 0.70 | 79.0% | 0.45 | 0.25 | 80.1% |

Regex compared: `quantified` = `METRICS_PATTERN`, `outcome` = `ACTION_VERBS`, `leadership` = `LEADERSHIP_WORDS`.

## By language, out-of-fold accuracy

| attribute | en-US | es-ES | pt-BR |
|---|---|---|---|
| `quantified` | 92.2% (regex 84.5%) | 93.7% (regex 86.6%) | 92.6% (regex 83.5%) |
| `outcome` | 86.6% (regex 63.5%) | 81.9% (regex 59.5%) | 82.8% (regex 51.9%) |
| `leadership` | 86.7% (regex 81.4%) | 84.3% (regex 78.6%) | 85.6% (regex 76.8%) |

## Cross-writer transfer

Trained on the bullets of one prose writer and scored on the other's, the test handoff 9.5 used to show quality was partly writer style. Row counts differ, so the two directions are not symmetric and the weaker one is the data-starved one.

| attribute | direction | train rows | test rows | accuracy | F1 |
|---|---|---|---|---|---|
| `quantified` | llama-3.1-8b-instant -> mistral-small-latest | 4523 | 1227 | 91.3% | 0.85 |
| `quantified` | mistral-small-latest -> llama-3.1-8b-instant | 1227 | 4523 | 91.5% | 0.92 |
| `outcome` | llama-3.1-8b-instant -> mistral-small-latest | 4523 | 1227 | 84.2% | 0.72 |
| `outcome` | mistral-small-latest -> llama-3.1-8b-instant | 1227 | 4523 | 81.1% | 0.83 |
| `leadership` | llama-3.1-8b-instant -> mistral-small-latest | 4523 | 1227 | 83.4% | 0.64 |
| `leadership` | mistral-small-latest -> llama-3.1-8b-instant | 1227 | 4523 | 82.5% | 0.62 |

## Bundle

Wrote `ml/models/bullet_probe_v1/` (transform `bullet_mean_l2_v1`).

