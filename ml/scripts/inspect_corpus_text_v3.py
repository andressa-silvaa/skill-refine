"""
Inspect whether the v3 prose actually carries the properties the corpus exists for.

validate_corpus_v3.py checks the NUMERIC signals. This checks the TEXT itself, where the four
ways the generation could be silently useless are:

  1. scope signal — if the LLM writes the same register for `assist` and `lead`, a text model
     has nothing to learn and the whole corpus is decorative. Measured as the rate of
     autonomy/leadership verbs vs subordinate verbs per band, which should rise across bands.
  2. language purity — nothing in the pipeline forces the reply to be in the requested
     language; drift would poison the multilingual training set.
  3. occupation grounding — if bullets are generic filler, ESCO diversity is cosmetic: the
     title changes and the text stays interchangeable.
  4. seniority-word rate — the deliberate ~20% valve that lets real phrasing appear without
     making the label readable as a keyword.

Usage (from repo root):
  python ml/scripts/inspect_corpus_text_v3.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
PROSE_PATH = ML_ROOT / "data" / "raw" / "resumes_v3" / "prose.jsonl"
BANDS = ("intern", "junior", "mid", "senior")

LEAD_VERBS = {
    "pt-BR": r"lider|coorden|supervis|geri|gerenci|defini|dirigi|orientei|deleg|estrutur|"
    r"negoci|aprov|priorizei|conduzi|estabeleci",
    "en-US": r"led|lead|coordinat|supervis|manag|direct|defin|oversaw|delegat|negotiat|"
    r"approv|prioritis|prioritiz|establish|drove",
    "es-ES": r"lider|coordin|supervis|gestion|dirig|defin|deleg|negoci|aprob|prioric|establec",
}
SUBORDINATE_VERBS = {
    "pt-BR": r"auxili|apoi|acompanh|assisti|colabor|particip|ajud|observ|aprend|suporte",
    "en-US": r"assist|support|shadow|help|particip|collaborat|observ|learn|aided",
    "es-ES": r"asisti|apoy|colabor|particip|ayud|acompañ|observ|aprend",
}

STOPWORDS = {
    "pt-BR": {"de", "para", "com", "em", "do", "da", "que", "os", "as", "uma", "um", "por"},
    "en-US": {"the", "of", "and", "to", "for", "with", "in", "on", "a", "by", "from"},
    "es-ES": {"de", "para", "con", "en", "del", "que", "los", "las", "una", "un", "por"},
}

SENIORITY_WORDS = re.compile(
    r"\b(est[aá]gi\w*|estagi[aá]ri\w*|j[uú]nior|pleno|s[êe]nior|senior|trainee|intern|"
    r"internship|entry[- ]level|mid[- ]level|becari\w*|pr[aá]cticas|pasante|semi-senior)\b",
    re.I,
)


def load() -> list[dict]:
    if not PROSE_PATH.exists():
        raise SystemExit(f"missing {PROSE_PATH}")
    rows = []
    for line in PROSE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def bullets_of(row: dict) -> list[str]:
    return [
        b for e in row["resume_data"]["data"]["experiences"] for b in e["description"]
    ]


def body_text(row: dict) -> str:
    d = row["resume_data"]["data"]
    return " ".join([d["summary"]] + bullets_of(row))


def main() -> None:
    rows = load()
    print(f"linhas analisadas: {len(rows)}\n")
    problems: list[str] = []

    print("=" * 78)
    print("1. SINAL DE ESCOPO — verbos de lideranca vs subordinacao, por banda")
    print("=" * 78)
    print(f"  {'banda':8s} {'n':>4s} {'lideranca/100 bullets':>22s} {'subordinacao/100':>18s}")
    lead_rate: dict[str, float] = {}
    for band in BANDS:
        sub = [r for r in rows if r["band_target"] == band]
        if not sub:
            continue
        lead = subord = total = 0
        for r in sub:
            lg = r["language"]
            for b in bullets_of(r):
                total += 1
                low = b.lower()
                if re.search(LEAD_VERBS[lg], low):
                    lead += 1
                if re.search(SUBORDINATE_VERBS[lg], low):
                    subord += 1
        lr = 100 * lead / total if total else 0.0
        sr = 100 * subord / total if total else 0.0
        lead_rate[band] = lr
        print(f"  {band:8s} {len(sub):>4d} {lr:>22.1f} {sr:>18.1f}")
    if len(lead_rate) == len(BANDS):
        ordered = [lead_rate[b] for b in BANDS]
        if ordered[-1] <= ordered[0]:
            problems.append("escopo: senior nao usa mais linguagem de lideranca que intern")
        gap = ordered[-1] - ordered[0]
        print(f"\n  diferenca senior - intern = {gap:+.1f} pontos", end="")
        print("  [OK]" if gap >= 8 else "  [FRACO — modelo de texto tera pouco a aprender]")
        if gap < 8:
            problems.append(f"escopo: diferenca de lideranca senior-intern de apenas {gap:.1f}pp")

    print("\n" + "=" * 78)
    print("2. PUREZA DE IDIOMA — stopwords do idioma pedido aparecem no texto?")
    print("=" * 78)
    for lg in ("pt-BR", "en-US", "es-ES"):
        sub = [r for r in rows if r["language"] == lg]
        if not sub:
            continue
        bad = []
        for r in sub:
            words = set(re.findall(r"[a-záàâãéêíóôõúüñç]+", body_text(r).lower()))
            own = len(words & STOPWORDS[lg])
            others = max(
                len(words & STOPWORDS[o]) for o in STOPWORDS if o != lg
            )
            if own < 2 or others > own:
                bad.append(r["id"])
        print(f"  {lg}  n={len(sub):4d}  suspeitos de idioma errado: {len(bad)}")
        if bad:
            print(f"    ex: {bad[:4]}")
        if len(bad) > max(1, 0.05 * len(sub)):
            problems.append(f"idioma: {len(bad)}/{len(sub)} linhas {lg} possivelmente no idioma errado")

    print("\n" + "=" * 78)
    print("3. ANCORAGEM NA OCUPACAO — palavra-chave da ocupacao aparece nos bullets?")
    print("=" * 78)
    hits = 0
    misses: list[str] = []
    for r in rows:
        label = str((r.get("occupation") or {}).get("label") or "").lower()
        tokens = [
            w
            for w in re.findall(r"[a-záàâãéêíóôõúüñç]{5,}", label)
            if w not in STOPWORDS[r["language"]]
        ]
        if not tokens:
            continue
        blob = " ".join(bullets_of(r)).lower()
        stems = [w[:6] for w in tokens]
        if any(s in blob for s in stems):
            hits += 1
        else:
            misses.append(f"{r['occupation']['label'][:34]}")
    checked = hits + len(misses)
    rate = hits / checked if checked else 0.0
    print(f"  bullets mencionam a ocupacao em {hits}/{checked} ({rate:.1%})")
    if misses:
        print(f"  exemplos sem ancoragem: {misses[:5]}")
    if rate < 0.70:
        problems.append(f"ancoragem: so {rate:.1%} dos curriculos citam a propria ocupacao")

    print("\n" + "=" * 78)
    print("4. PALAVRA DE SENIORIDADE NO TEXTO — alvo ~20% (a valvula de realismo)")
    print("=" * 78)
    allowed = [r for r in rows if r.get("may_state_seniority")]
    denied = [r for r in rows if not r.get("may_state_seniority")]
    leak_allowed = sum(1 for r in allowed if SENIORITY_WORDS.search(body_text(r)))
    leak_denied = sum(1 for r in denied if SENIORITY_WORDS.search(body_text(r)))
    print(f"  liberados:  {len(allowed):4d} ({len(allowed)/len(rows):.0%} do corpus),"
          f" com palavra: {leak_allowed}")
    print(f"  proibidos:  {len(denied):4d}, com palavra: {leak_denied} (deve ser 0)")
    by_band = Counter(r["band_target"] for r in rows if SENIORITY_WORDS.search(body_text(r)))
    print("  distribuicao das ocorrencias por banda:", dict(by_band))
    if leak_denied:
        problems.append(f"valvula: {leak_denied} curriculos proibidos contem palavra de senioridade")

    print("\n" + "=" * 78)
    if problems:
        print(f"PROBLEMAS — {len(problems)}:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("OK — o texto carrega as propriedades esperadas")


if __name__ == "__main__":
    main()
