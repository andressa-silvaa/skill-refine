# Education-to-target alignment — threshold calibration

Replaces `_TECH_EDU_RE` / `_NON_TECH_EDU_RE`, two closed lists of degree names that decide whether a candidate's education matches their target role.

**This is a proxy calibration, and the number must be read as one.** The v3 corpus records only the degree level (12 distinct strings: `Graduacao`, `Bachelor`, `Master`, ...) and never a field of study, so there is no labelled education-to-occupation pair to fit on. What follows measures the same encoder on the same kind of short career-domain string, using ESCO occupation pairs where same ISCO-08 group counts as related.

Encoder `paraphrase-multilingual-MiniLM-L12-v2` · 4000 pairs per language · background sample 64 occupations · seed 20260812

| language | n occupations | AUC cosine | AUC margin | threshold (margin) | accuracy |
|---|---|---|---|---|---|
| pt | 1701 | 0.724 | **0.746** | 0.048 | 68.6% |
| en | 1701 | 0.781 | **0.790** | 0.067 | 72.1% |
| es | 1701 | 0.779 | **0.791** | 0.111 | 72.4% |

**Shipped thresholds, per language: {"pt": 0.048, "en": 0.067, "es": 0.111}**

Per language rather than pooled, because the spread is 2.3x (0.048 to 0.111) and a single constant would misfire at both ends. The scale differs by language for a structural reason, not noise: ESCO's pt labels are long double-gender compounds ("Operador de maquinas.../Operadora de maquinas...") while its en labels are short noun phrases, so the background similarity they sit against differs.

## The test that settled it: are the two classes separable at all?

The proxy above says the encoder ranks career-domain strings sensibly. It does not say a threshold exists for *this* decision. Ten hand-written pairs, chosen to be easy, answer that directly — a threshold classifies them only if every aligned pair outscores every unrelated one.

| field of study | target role | aligned? | margin |
|---|---|---|---|
| Enfermagem | Enfermeiro chefe | yes | +0.6130 |
| Pedagogia | Professor do ensino fundamental | yes | +0.4608 |
| Ciencia da Computacao | Programador | yes | +0.3169 |
| Computer Science | Software Engineer | yes | +0.3002 |
| Biologia | Programador | no | +0.1842 |
| Marketing | Contador | no | +0.1667 |
| Analise e Desenvolvimento de Sistemas | Desenvolvedor Backend | yes | +0.1523 |
| Ingenieria en Sistemas | Desarrollador de software | yes | +0.1130 |
| Direito | Programador | no | +0.0935 |
| Historia | Engenheiro civil | no | +0.0099 |

Lowest aligned pair **+0.1130** (Ingenieria en Sistemas / Desarrollador). Highest unrelated pair **+0.1842** (Biologia / Programador). **Separable: no.**

The classes overlap, so **no threshold on this score classifies even these ten pairs**, and the swap was reverted. `education_aligned_with_target` keeps its keyword lists.

Why the proxy did not transfer: ESCO pairs are occupation-label against occupation-label, two strings of the same kind. The real task compares a *field of study* against a *job title*, which are different registers, and the margin scale moves with them. The proxy measured the encoder, not the decision.

What would unblock it, in order of cost: education field-of-study text in the corpus (the generator writes only the degree level today, 12 distinct strings), then a few hundred human-judged education-to-target pairs to fit and validate a boundary on. Neither exists on disk, and inventing the threshold is what this measurement prevents.

## What this does and does not license

- It does **not** license shipping encoder similarity as the decider for this feature.
- It does **not** license publishing an accuracy figure for education alignment. The real task is unmeasured until resumes carry a field of study.
- The separation is only moderate even on the proxy (AUC 0.75-0.79, accuracy 69-72%), which was the first warning; the hand-case overlap above is the confirmation.
- The incumbent keyword lists remain wrong in the ways already documented — pt-BR shaped, gated on a closed 'tech target' list, literal token overlap otherwise. **Both options are bad, and this measurement says which is not yet demonstrably better.**
- One design idea worth keeping for the retry: a bare degree level sits equidistant from every occupation, so a margin near zero is a usable abstention signal. That part behaved as intended (`Graduacao Bacharelado` scored -0.012); it is the aligned/unrelated boundary that does not exist, not the ability to spot an uninformative degree.
