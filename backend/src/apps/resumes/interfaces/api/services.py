"""
Compatibility facade for resume API services.

The implementation is split by responsibility in smaller modules:
- service_utils.py
- service_tokens.py
- service_queries.py
- service_mutations.py
"""
from __future__ import annotations

from .service_mutations import (
    create_resume_draft,
    delete_resume_soft,
    duplicate_resume,
    update_resume_draft,
)
from .service_queries import (
    ResumeListFilters,
    get_resume_by_id_and_user,
    get_resume_for_edit,
    get_resume_for_pdf_data,
    list_resumes,
    list_resumes_paginated,
)
from .service_tokens import (
    PDF_TOKEN_SALT,
    PDF_TOKEN_TTL_SECONDS,
    create_pdf_token,
    parse_pdf_token,
)
from .service_utils import (
    normalize_optional,
    parse_month,
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
    section_order,
    unique_copy_name,
    validate_complete,
)

__all__ = [
    "PDF_TOKEN_SALT",
    "PDF_TOKEN_TTL_SECONDS",
    "ResumeListFilters",
    "create_pdf_token",
    "create_resume_draft",
    "delete_resume_soft",
    "duplicate_resume",
    "get_resume_by_id_and_user",
    "get_resume_for_edit",
    "get_resume_for_pdf_data",
    "list_resumes",
    "list_resumes_paginated",
    "normalize_optional",
    "parse_month",
    "parse_pdf_token",
    "replace_educations",
    "replace_experiences",
    "replace_languages",
    "replace_skills",
    "section_order",
    "unique_copy_name",
    "update_resume_draft",
    "validate_complete",
]
