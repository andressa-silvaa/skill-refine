"""
Preprocess dataset: normalize text, extract sections, optional BERTimbau tokenization.
PII masking applied; token_length saved for truncation info. Language preserved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LABELING_DIR = SCRIPT_DIR.parent / "labeling"
HEURISTICS_DIR = LABELING_DIR / "heuristics"

LANGUAGES = ("pt", "en", "es")
PII_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PII_PHONE = re.compile(r"\+?[\d\s\-()]{10,}")


def _load_section_headers(lang: str) -> dict:
    path = HEURISTICS_DIR / f"section_headers_{lang}.json"
    if not path.exists():
        path = HEURISTICS_DIR / "section_headers_pt.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_unicode(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", text.strip()) if text else ""


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split()) if text else ""


def mask_pii(text: str) -> str:
    t = PII_EMAIL.sub("[EMAIL]", text)
    t = PII_PHONE.sub("[PHONE]", t)
    return t


def extract_sections(text: str, language: str) -> dict[str, str]:
    """
    Split resume text into sections using common headers (from heuristics JSON).
    Returns dict: summary, experience, education, skills, projects, contact, other.
    """
    data = _load_section_headers(language)
    sections_config = data.get("sections", {})
    section_labels = list(sections_config.keys())
    current = "OTHER"
    chunks: dict[str, list[str]] = {s: [] for s in section_labels}
    if "OTHER" not in chunks:
        chunks["OTHER"] = []
    lines = text.splitlines()
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()
        found = None
        for label, keywords in sections_config.items():
            if not keywords:
                continue
            for kw in keywords:
                if kw.lower() in line_lower and len(line_stripped) < 80:
                    found = label
                    break
            if found:
                break
        if found:
            current = found
            continue
        if current in chunks:
            chunks[current].append(line_stripped)
    result = {}
    for k, v in chunks.items():
        result[k.lower() if k != "OTHER" else "other"] = "\n".join(v) if v else ""
    return result


def tokenize_bertimbau(text: str) -> list[str]:
    """Optional: tokenize with BERTimbau. Requires transformers; returns token count if unavailable."""
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("neuralmind/bert-base-portuguese-cased")
        return tok.tokenize(text)
    except Exception:
        return []


def preprocess_record(
    record: dict,
    *,
    normalize: bool = True,
    extract_sections_flag: bool = True,
    tokenize: bool = False,
) -> dict:
    """
    Normalize resume_text, optionally extract sections and tokenize.
    Sets resume_text (normalized), sections, token_length, language.
    """
    out = dict(record)
    text = out.get("resume_text") or out.get("input_text") or ""
    lang = (out.get("language") or "pt").replace("-BR", "").replace("-US", "").replace("-ES", "")
    if lang not in LANGUAGES:
        lang = "pt"
    out["language"] = lang

    if normalize:
        text = normalize_unicode(text)
        text = normalize_whitespace(text)
        text = mask_pii(text)
    out["resume_text"] = text
    if "input_text" not in out and text:
        out["input_text"] = text

    if extract_sections_flag and text:
        out["sections"] = extract_sections(text, lang)

    if tokenize:
        tokens = tokenize_bertimbau(text)
        out["token_length"] = len(tokens)
    else:
        out["token_length"] = len(text.split())

    return out


def run(input_path: Path, output_path: Path, *, tokenize: bool = False) -> int:
    """Read JSONL, preprocess each record, write JSONL. Returns count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out = preprocess_record(rec, tokenize=tokenize)
            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Preprocess resumes: normalize, sections, optional tokenization")
    p.add_argument("input", type=Path, help="Input JSONL")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL")
    p.add_argument("--tokenize", action="store_true", help="Use BERTimbau tokenizer (requires transformers)")
    args = p.parse_args()
    n = run(args.input, args.output, tokenize=args.tokenize)
    print(f"Preprocessed {n} records -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
