from __future__ import annotations

from django.core import signing

PDF_TOKEN_SALT = "resume-pdf"
PDF_TOKEN_TTL_SECONDS = 120


def create_pdf_token(resume_id: str, user_id: str) -> str:
    return signing.dumps({"resume_id": resume_id, "user_id": user_id}, salt=PDF_TOKEN_SALT)


def parse_pdf_token(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    try:
        data = signing.loads(token, salt=PDF_TOKEN_SALT, max_age=PDF_TOKEN_TTL_SECONDS)
    except signing.SignatureExpired:
        return None
    except signing.BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    resume_id = str(data.get("resume_id") or "").strip()
    user_id = str(data.get("user_id") or "").strip()
    if not resume_id or not user_id:
        return None
    return {"resume_id": resume_id, "user_id": user_id}
