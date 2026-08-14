"""
ISCO-08 code to product domain category.

ISCO major groups (1 digit) encode skill level, not field: group 2 puts a physician, a lawyer and
a civil engineer in the same bucket, so a 1-digit mapping is useless as a domain. The field lives
in the sub-major group (2 digits); where a sub-major group mixes fields, the minor (3) or unit (4)
group disambiguates. Lookup is longest-prefix: 4 digits, then 3, then 2.

Every value is a member of DOMAIN_CATEGORIES in domain_inference.py.
"""
from __future__ import annotations

_ISCO_PREFIX_DOMAIN: dict[str, str] = {
    "01": "operations",
    "02": "operations",
    "03": "operations",
    "11": "general",
    "111": "administrative",
    "12": "administrative",
    "1211": "finance",
    "1212": "hr",
    "122": "marketing",
    "1221": "sales",
    "1223": "science",
    "13": "operations",
    "133": "technology",
    "1341": "education",
    "1342": "health",
    "1343": "health",
    "1344": "health",
    "1345": "education",
    "1346": "finance",
    "14": "operations",
    "142": "sales",
    "1431": "creative",
    "21": "engineering",
    "211": "science",
    "212": "science",
    "213": "science",
    "2163": "creative",
    "2166": "creative",
    "22": "health",
    "23": "education",
    "24": "administrative",
    "241": "finance",
    "2423": "hr",
    "2424": "hr",
    "243": "marketing",
    "2433": "sales",
    "2434": "sales",
    "25": "technology",
    "26": "creative",
    "261": "legal",
    "263": "science",
    "2631": "finance",
    "2634": "health",
    "2635": "health",
    "2636": "general",
    "31": "engineering",
    "312": "operations",
    "313": "operations",
    "314": "science",
    "315": "operations",
    "32": "health",
    "33": "administrative",
    "331": "finance",
    "332": "sales",
    "3323": "operations",
    "3331": "operations",
    "3332": "marketing",
    "3333": "hr",
    "3334": "sales",
    "34": "creative",
    "341": "legal",
    "3412": "health",
    "3413": "general",
    "342": "health",
    "3434": "operations",
    "35": "technology",
    "41": "administrative",
    "42": "administrative",
    "421": "finance",
    "4221": "sales",
    "43": "operations",
    "431": "finance",
    "4313": "hr",
    "44": "administrative",
    "51": "operations",
    "5165": "education",
    "52": "sales",
    "53": "health",
    "531": "education",
    "54": "operations",
    "61": "operations",
    "62": "operations",
    "63": "operations",
    "71": "operations",
    "72": "operations",
    "73": "operations",
    "74": "operations",
    "742": "technology",
    "75": "operations",
    "81": "operations",
    "82": "operations",
    "83": "operations",
    "91": "operations",
    "92": "operations",
    "93": "operations",
    "94": "operations",
    "95": "sales",
    "96": "operations",
}


def isco_code_digits(isco: str) -> str:
    """ESCO stores codes as '2165.4.1'; the unit group is the part before the first dot."""
    head = str(isco or "").strip().split(".")[0]
    return "".join(c for c in head if c.isdigit())


def domain_for_isco(isco: str) -> str:
    digits = isco_code_digits(isco)
    for size in (4, 3, 2):
        hit = _ISCO_PREFIX_DOMAIN.get(digits[:size])
        if hit:
            return hit
    return "general"
