"""
Evaluate Groq (llama-3.1-8b-instant, already configured for the rewrite feature)
as a PROMPTED seniority classifier — few-shot + self-consistency voting, no
fine-tuning — against the held-out test split of the synthetic gold dataset
(ml/data/raw/resumes_v2), using the same ground truth (intended_seniority) the
sklearn signals_ml model was evaluated against.

v2: adds 4 few-shot examples (pulled from the TRAIN split only, never test) that
demonstrate the "trust real signals, not the job title" rule concretely, plus
self-consistency (N samples per case at temperature>0, majority vote) to reduce
single-sample noise.

This is a standalone evaluation script — it does NOT touch the live inference
pipeline. Run it, inspect the accuracy/confusion matrix, and only wire this into
orchestrator.py if the numbers are actually good.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_groq_seniority_classifier.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1].parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.signals.resume_signals import extract_resume_signals  # noqa: E402

RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v2"
TEST_SPLIT = REPO_ROOT / "ml" / "data" / "splits" / "seniority_text_synthetic_v2" / "test.jsonl"
TRAIN_SPLIT = REPO_ROOT / "ml" / "data" / "splits" / "seniority_text_synthetic_v2" / "train.jsonl"

LABELS = ("intern", "junior", "mid", "senior")
N_VOTES = 5
VOTE_TEMPERATURE = 0.6

# Hand-picked from the TRAIN split (never test) — all are title/keyword-mismatch
# cases chosen specifically to demonstrate "trust the real signals over the
# job title or a stray keyword" to the model via worked examples. The last two
# (mid_boundary / senior_boundary) target the specific 55-60 month mid/senior
# ambiguity zone where evaluation showed the model wavering.
FEWSHOT_IDS = {
    "intern": "110c288f-3c57-4d76-a429-4bc7ede68fc3",
    "junior": "7c4f7d78-9524-42c1-b4e2-c9695ecb8cba",
    "mid": "0a9e95f1-0325-432b-8965-7aae359379d6",
    "senior": "10fb977c-9c8d-4527-9e11-9d2ffa852f12",
    "mid_boundary": "d4c0da87-9d1d-4e86-97e5-95b0fbfd756b",
    "senior_boundary": "16dff94a-e98b-43ba-9103-6919ad6068ba",
}
FEWSHOT_REASONING = {
    "intern": "O cargo diz \"Cientista de Dados Sênior\", mas há apenas 5 meses reais de experiência, "
    "1 vínculo e 2 realizações — o título não é sustentado por tempo real. Classificação correta: intern.",
    "junior": "Há um estágio (Estagiário de TI) na história, mas é um vínculo anterior — o vínculo mais "
    "recente já é \"Analista de Sistemas Júnior\", e o total real é de 13 meses em 2 vínculos com "
    "realizações concretas. Um estágio passado não deve, sozinho, forçar \"intern\" quando a "
    "trajetória já avançou. Classificação correta: junior.",
    "mid": "Também há um vínculo de trainee mais antigo, mas o total real é de 62 meses em 2 vínculos, "
    "com 7 realizações — a presença de um estágio na história não anula anos reais de experiência "
    "posterior. Classificação correta: mid.",
    "senior": "A história tem um cargo antigo chamado \"Júnior\", mas o total agregado real é de 98 meses "
    "(~8 anos) em 3 vínculos com 11 realizações — nomes de cargo antigos não definem o nível atual; "
    "o que importa é o tempo e o escopo reais acumulados. Classificação correta: senior.",
    "mid_boundary": "57 meses reais (quase 5 anos), 2 vínculos, 6 realizações, com menção a liderança em "
    "um dos cargos. É bastante tempo, mas o número de vínculos e realizações é moderado — não é um caso "
    "excepcional. Perto de 58-60 meses com escopo apenas moderado (2 vínculos, poucas realizações) deve "
    "ficar em \"mid\", reservando \"senior\" para quando o escopo também for excepcional, não só o tempo. "
    "Classificação correta: mid.",
    "senior_boundary": "56 meses reais (pouco menos de 5 anos, portanto abaixo do patamar usual de "
    "senior), mas com 4 vínculos distintos, 11 realizações listadas e liderança mencionada — um volume "
    "e amplitude de responsabilidades excepcionais para o tempo. Quando o ESCOPO é claramente "
    "excepcional (muitos vínculos, muitas realizações, liderança real), ele pode compensar um tempo "
    "total um pouco abaixo do patamar usual de 58-60 meses. Classificação correta: senior.",
}

SYSTEM_PROMPT = """Você é um recrutador técnico sênior especialista em avaliar o nível de senioridade \
de um profissional a partir do currículo.

Classifique em EXATAMENTE uma das 4 categorias: intern, junior, mid, senior.

REGRAS CRÍTICAS (siga à risca, nesta ordem de prioridade):
1. Baseie sua decisão principalmente nos SINAIS ESTRUTURADOS fornecidos (meses reais de \
experiência, calculados a partir de datas verificadas) — não no que o resumo/texto livre \
alega sobre "anos de experiência". Uma frase como "5 anos de experiência" no resumo, sem \
datas estruturadas reais que sustentem isso, NÃO deve elevar a classificação.
2. NUNCA confie apenas no título do cargo (atual ou de vínculos antigos). Um título inflado \
("Sênior", "Head of X", "Gerente") sem tempo real de experiência não vale nada. Uma palavra \
como "estagiário"/"trainee" aparecendo em um vínculo ANTIGO da carreira não deve, sozinha, \
forçar "intern" se a trajetória e o tempo total real já avançaram além disso — olhe o \
conjunto da carreira, não uma palavra isolada.
3. Nunca classifique como "senior" sem evidência real: tipicamente 48+ meses reais E \
(múltiplas experiências OU claro sinal de liderança/autonomia nos bullets).
4. Na faixa de 55-60 meses reais (a fronteira mais ambígua entre "mid" e "senior"), o tempo \
sozinho não decide: exija ESCOPO excepcional para justificar "senior" abaixo do patamar usual \
de ~60 meses — ou seja, várias experiências distintas (3+) E muitas realizações listadas (9+) \
E liderança real. Sem essa combinação excepcional, mesmo com liderança mencionada, prefira "mid".
5. Nunca invente ou presuma informação que não está no currículo.

Veja os exemplos a seguir (todos são casos reais de currículo com cargo enganoso, e mostram \
como aplicar as regras acima corretamente) antes de responder ao caso pedido.

Responda APENAS com um JSON no formato exato:
{"label": "intern|junior|mid|senior", "confidence": "low|medium|high", "reasoning": "uma frase curta"}
"""

USER_TEMPLATE = """CURRÍCULO (texto completo, com datas reais):
---
{full_text}
---

SINAIS ESTRUTURADOS VERIFICADOS (calculados a partir das datas reais do currículo, mais \
confiáveis que qualquer menção textual de "anos de experiência" ou palavra isolada no cargo):
- total_months_experience (meses reais de experiência, por datas): {total_months}
- experiences_count (número de empregos distintos): {experiences_count}
- bullets_count (número de descrições/realizações listadas): {bullets_count}
- has_internship_terms (algum vínculo, atual ou passado, menciona estágio/trainee): {has_internship}
- has_leadership_terms (menção a liderança/coordenação/gestão em algum vínculo): {has_leadership}

Classifique a senioridade deste profissional."""


def _signals_dict(rs) -> dict:
    return {
        "total_months": rs.total_months_experience,
        "experiences_count": rs.experiences_count,
        "bullets_count": rs.bullets_count,
        "has_internship": rs.has_internship_terms,
        "has_leadership": rs.has_leadership_terms,
    }


def _build_fewshot_messages() -> list[dict]:
    train_ids = {json.loads(l)["id"] for l in TRAIN_SPLIT.open(encoding="utf-8")}
    raw_by_id = {}
    for fp in RAW_DIR.glob("*.json"):
        row = json.loads(fp.read_text(encoding="utf-8"))
        raw_by_id[row["id"]] = row

    messages = []
    for label, rid in FEWSHOT_IDS.items():
        assert rid in train_ids, f"few-shot id {rid} must come from the TRAIN split, not test"
        raw = raw_by_id[rid]
        sections = resume_to_text(raw["resume_data"], language="pt-BR")
        rs = extract_resume_signals(raw["resume_data"], sections, language="pt-BR")
        user_msg = USER_TEMPLATE.format(full_text=sections.full_text, **_signals_dict(rs))
        assistant_msg = json.dumps(
            {"label": label, "confidence": "high", "reasoning": FEWSHOT_REASONING[label]},
            ensure_ascii=False,
        )
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
    return messages


def call_groq_once(messages: list[dict], *, temperature: float, max_retries: int = 6) -> dict:
    base_url = getattr(settings, "AI_CLOUD_BASE_URL", "").rstrip("/")
    api_key = getattr(settings, "AI_CLOUD_API_KEY", "")
    model = getattr(settings, "AI_CLOUD_MODEL", "")

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after")
                wait = float(retry_after) if retry_after else (2.0 * (attempt + 1))
                time.sleep(min(wait, 20.0) + 0.5)
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Groq call failed after {max_retries} retries: {last_exc}")


def classify_with_voting(fewshot_messages: list[dict], full_text: str, signals: dict) -> dict:
    user_prompt = USER_TEMPLATE.format(full_text=full_text, **signals)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *fewshot_messages, {"role": "user", "content": user_prompt}]

    votes: list[str] = []
    reasonings: list[str] = []
    for _ in range(N_VOTES):
        result = call_groq_once(messages, temperature=VOTE_TEMPERATURE)
        lab = str(result.get("label", "")).strip().lower()
        if lab in LABELS:
            votes.append(lab)
            reasonings.append(str(result.get("reasoning", "")))
        time.sleep(2.2)

    if not votes:
        return {"label": "ERROR", "reasoning": "no valid votes"}
    tally = Counter(votes)
    winner, count = tally.most_common(1)[0]
    return {"label": winner, "votes": dict(tally), "reasoning": reasonings[votes.index(winner)]}


def main() -> None:
    print("Building few-shot examples from TRAIN split...")
    fewshot_messages = _build_fewshot_messages()

    test_rows = [json.loads(l) for l in TEST_SPLIT.open(encoding="utf-8")]
    raw_by_id = {}
    for fp in RAW_DIR.glob("*.json"):
        row = json.loads(fp.read_text(encoding="utf-8"))
        raw_by_id[row["id"]] = row

    y_true: list[str] = []
    y_pred: list[str] = []
    errors: list[dict] = []

    for i, trow in enumerate(test_rows):
        rid = trow["id"]
        raw = raw_by_id.get(rid)
        if raw is None:
            print(f"WARN: {rid} not found in raw dir, skipping")
            continue
        resume_data = raw["resume_data"]
        sections = resume_to_text(resume_data, language="pt-BR")
        rs = extract_resume_signals(resume_data, sections, language="pt-BR")
        true_label = raw["intended_seniority"]

        result = classify_with_voting(fewshot_messages, sections.full_text, _signals_dict(rs))
        pred_label = result["label"]

        y_true.append(true_label)
        y_pred.append(pred_label)
        status = "OK" if pred_label == true_label else "MISS"
        votes_str = result.get("votes", {})
        print(f"[{i+1}/{len(test_rows)}] true={true_label:8s} pred={pred_label:8s} votes={votes_str} {status}")
        if pred_label != true_label:
            errors.append({
                "id": rid,
                "true": true_label,
                "pred": pred_label,
                "votes": votes_str,
                "reasoning": result.get("reasoning"),
            })

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    n = len(y_true)
    print()
    print(f"Accuracy: {correct}/{n} = {100*correct/n:.1f}%")

    cm = Counter(zip(y_true, y_pred))
    print("\nConfusion (true, pred): count")
    for k, v in sorted(cm.items()):
        marker = "" if k[0] == k[1] else "  <-- MISS"
        print(f"  {k}: {v}{marker}")

    if errors:
        print("\nMisclassified cases:")
        for e in errors:
            print(f"  {e['id']}: true={e['true']} pred={e['pred']} votes={e['votes']} reasoning={e['reasoning']!r}")

    out_path = REPO_ROOT / "ml" / "training" / "reports" / "groq_seniority_eval_v2_fewshot_voting.json"
    out_path.write_text(
        json.dumps(
            {"accuracy": correct / n, "n": n, "correct": correct, "n_votes": N_VOTES, "errors": errors},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
