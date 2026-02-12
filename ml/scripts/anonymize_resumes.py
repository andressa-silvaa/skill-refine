"""
Anonymize resume text: mask PII (names, email, phone, URLs). Optionally replace specific companies with "Empresa X".
Raw data must stay outside repo (gitignored); only anonymized output is stored.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

# Patterns (same as normalize_resume + extra for names/URLs)
PII_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PII_PHONE = re.compile(r"\+?[\d\s\-()]{10,}")
PII_URL = re.compile(r"https?://[^\s]+|www\.[^\s]+|linkedin\.com/[^\s]*|github\.com/[^\s]*", re.I)
# Generic name-like (optional: 2+ capitalized words in a row often used as names in headers)
# We mask only if explicitly requested via --mask-names
NAME_LIKE = re.compile(r"\b([A-ZÁÉÍÓÚ][a-záéíóúãõç]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóúãõç]+)+)\b")

PLACEHOLDER_EMAIL = "[EMAIL]"
PLACEHOLDER_PHONE = "[PHONE]"
PLACEHOLDER_URL = "[URL]"
PLACEHOLDER_LINKEDIN = "[LINK_LINKEDIN]"
PLACEHOLDER_GITHUB = "[LINK_GITHUB]"
PLACEHOLDER_NAME = "[NOME]"
PLACEHOLDER_COMPANY = "Empresa X"


def mask_email(text: str) -> str:
    return PII_EMAIL.sub(PLACEHOLDER_EMAIL, text)


def mask_phone(text: str) -> str:
    return PII_PHONE.sub(PLACEHOLDER_PHONE, text)


def mask_urls(text: str, generic_url: bool = True) -> str:
    """Replace LinkedIn/GitHub with placeholders; other URLs with [URL] if generic_url."""
    t = text
    t = re.sub(r"linkedin\.com/[^\s\)\]\"]*", PLACEHOLDER_LINKEDIN, t, flags=re.I)
    t = re.sub(r"github\.com/[^\s\)\]\"]*", PLACEHOLDER_GITHUB, t, flags=re.I)
    if generic_url:
        t = PII_URL.sub(PLACEHOLDER_URL, t)
    return t


def mask_names(text: str) -> str:
    """Replace name-like sequences (2+ capitalized words) with placeholder. Use with care (may over-mask)."""
    return NAME_LIKE.sub(PLACEHOLDER_NAME, text)


def mask_companies(text: str, company_list: list[str] | None = None) -> str:
    """Replace known company names with Empresa X. If company_list is None, skip."""
    if not company_list:
        return text
    t = text
    for c in company_list:
        if c:
            t = re.sub(re.escape(c), PLACEHOLDER_COMPANY, t, flags=re.I)
    return t


def anonymize_text(
    text: str,
    *,
    mask_email_flag: bool = True,
    mask_phone_flag: bool = True,
    mask_urls_flag: bool = True,
    mask_names_flag: bool = False,
    company_list: list[str] | None = None,
) -> str:
    t = text
    if mask_email_flag:
        t = mask_email(t)
    if mask_phone_flag:
        t = mask_phone(t)
    if mask_urls_flag:
        t = mask_urls(t)
    if mask_names_flag:
        t = mask_names(t)
    if company_list:
        t = mask_companies(t, company_list)
    return t


def anonymize_record(
    record: dict,
    *,
    text_keys: list[str] | None = None,
    mask_names_flag: bool = False,
    company_list: list[str] | None = None,
) -> dict:
    """Anonymize all text fields in record. Modifies copy; adds anonymized_source if not present."""
    text_keys = text_keys or ["resume_text", "input_text", "line_text"]
    out = dict(record)
    for key in text_keys:
        if key in out and out[key]:
            out[key] = anonymize_text(
                str(out[key]),
                mask_names_flag=mask_names_flag,
                company_list=company_list,
            )
    if "sections" in out and isinstance(out["sections"], dict):
        out["sections"] = {
            k: anonymize_text(str(v), mask_names_flag=mask_names_flag, company_list=company_list)
            for k, v in out["sections"].items()
        }
    out["source"] = "anonymized"
    return out


def run(
    input_path: Path,
    output_path: Path,
    *,
    mask_names_flag: bool = False,
    company_list_path: Path | None = None,
) -> int:
    """Read JSONL, anonymize each record, write JSONL. Returns count."""
    company_list: list[str] | None = None
    if company_list_path and company_list_path.exists():
        company_list = [line.strip() for line in company_list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            anon = anonymize_record(rec, mask_names_flag=mask_names_flag, company_list=company_list)
            if "resume_id" not in anon:
                anon["resume_id"] = rec.get("resume_id") or str(uuid4())
            fout.write(json.dumps(anon, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Anonymize resumes (PII mask); raw data stays out of repo")
    p.add_argument("input", type=Path, help="Input JSONL (raw)")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL (anonymized)")
    p.add_argument("--mask-names", action="store_true", help="Mask name-like sequences (may over-mask)")
    p.add_argument("--company-list", type=Path, help="File with one company name per line to replace with Empresa X")
    args = p.parse_args()
    n = run(args.input, args.output, mask_names_flag=args.mask_names, company_list_path=args.company_list)
    print(f"Anonymized {n} records -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
