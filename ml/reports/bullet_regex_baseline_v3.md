# Per-bullet regex baseline — v3 corpus

Labels `labels_bullets.jsonl` (764 resumes) · second annotator `labels_bullets_mistral.jsonl` (92 resumes) · **5750 bullets scored**

Language: {'es': 1884, 'pt': 1869, 'en': 1997} · band: {'intern': 1285, 'mid': 1560, 'junior': 1393, 'senior': 1512}

Positive rate in the labels:

| attribute | positives | rate |
|---|---|---|
| `quantified` | 2644 | 46.0% |
| `outcome` | 2777 | 48.3% |
| `leadership` | 1146 | 19.9% |

### Inter-annotator agreement

716 bullets labelled twice by different model families. Cohen's kappa against the chance rate implied by each labeller's own positive rate.

| attribute | agreement | kappa | positive rate A | positive rate B |
|---|---|---|---|---|
| `quantified` | 90.1% | 0.77 | 0.65 | 0.75 |
| `outcome` | 81.7% | 0.54 | 0.65 | 0.82 |
| `leadership` | 89.5% | 0.70 | 0.19 | 0.26 |

### Regex vs single annotator (n=5750)

| attribute | regex | n | agreement | precision | recall | misses | false fires |
|---|---|---|---|---|---|---|---|
| `quantified` | `METRICS_PATTERN` | 5750 | 84.9% | 0.96 | 0.70 | 786 | 85 |
| `outcome` | `ACTION_VERBS` | 5750 | 58.4% | 0.74 | 0.22 | 2174 | 216 |
| `leadership` | `LEADERSHIP_WORDS` | 5750 | 79.0% | 0.45 | 0.25 | 855 | 353 |

### Regex vs two-annotator consensus (from 716 paired bullets, 277 attribute-level disagreements dropped)

| attribute | regex | n | agreement | precision | recall | misses | false fires |
|---|---|---|---|---|---|---|---|
| `quantified` | `METRICS_PATTERN` | 645 | 83.3% | 1.00 | 0.77 | 108 | 0 |
| `outcome` | `ACTION_VERBS` | 585 | 35.0% | 0.88 | 0.21 | 367 | 13 |
| `leadership` | `LEADERSHIP_WORDS` | 641 | 82.4% | 0.57 | 0.32 | 84 | 29 |

### Regex recall by language, on label positives

| language | `quantified` | `outcome` | `leadership` |
|---|---|---|---|
| en | 0.70 (n=928) | 0.39 (n=923) | 0.29 (n=393) |
| es | 0.68 (n=746) | 0.12 (n=857) | 0.22 (n=391) |
| pt | 0.72 (n=970) | 0.14 (n=997) | 0.25 (n=362) |

### Examples the regex misses — label positive, regex silent

- `quantified` (es) — Trabajé junto a un equipo para gestionar el volumen mensual de 1500 solicitudes de soporte técnico.
- `quantified` (pt) — Realizei cálculos e simulações para otimizar o fluxo de produção e reduzir custos operacionais.
- `quantified` (en) — Maintained detailed records of news archives and scripts.
- `outcome` (pt) — Realizei cálculos e simulações para otimizar o fluxo de produção e reduzir custos operacionais.
- `outcome` (en) — Produced accurate and timely news updates for broadcast.
- `outcome` (es) — Mejoré significativamente las ventas en el área de pizza, alcanzando un aumento del 18% en un período de 6 meses debido a la mejora en la atención al 
- `leadership` (es) — Trabajé junto a un equipo para gestionar el volumen mensual de 1500 solicitudes de soporte técnico.
- `leadership` (es) — Ayudé a preparar y organizar el equipo para las citas
- `leadership` (es) — Realicé una coordinación efectiva con los proveedores para reducir los costos de producción y asegurar la calidad de los ingredientes

### Examples the regex false-fires on — label negative, regex fires

- `quantified` (en) — Improved client self-awareness ratings by 25% through in-depth coaching sessions.
- `quantified` (en) — Analyzed customer behavior and preferences to inform product development and improve customer satisfaction by 18%.
- `quantified` (en) — Designed and implemented a data-driven decision-making process, improving decision accuracy by 25%.
- `outcome` (en) — Maintained detailed records of news archives and scripts.
- `outcome` (en) — Compiled and organized news clips for use in future broadcasts.
- `outcome` (en) — Observed and assisted in the development of technical documentation and knowledge bases.
- `leadership` (pt) — Processei e analisei dados de produção para fornecer relatórios de status atualizado aos gerentes de operações.
- `leadership` (es) — Implementé un sistema de capacitación para los empleados, lo que mejoró la productividad y la eficiencia en la producción de pizzas
- `leadership` (es) — Seguí las instrucciones del supervisor para garantizar el cumplimiento de los protocolos de seguridad en la sala de control.

