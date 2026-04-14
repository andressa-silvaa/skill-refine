import json, csv, os

inp = r"ml\data\processed\low_confidence_review.jsonl"
out = r"ml\data\processed\low_confidence_review.csv"

fields = [
  "analysis_key",
  "resume_key",
  "labels.seniority_label",
  "signals.confidence",
  "signals.total_months_experience",
  "signals.experiences_count",
  "signals.bullets_count",
  "signals.has_internship_terms",
  "signals.has_leadership_terms",
  "signals.skills_count",
  "signals.education_present",
  "signals.completeness_score",
  "signals.insufficient_data",
  "signals.reasons",
]

def get_path(d, path):
    cur = d
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur

rows = []
with open(inp, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        row = {k: get_path(d, k) for k in fields}
        if isinstance(row.get("signals.reasons"), list):
            row["signals.reasons"] = ",".join(row["signals.reasons"])
        rows.append(row)

os.makedirs(os.path.dirname(out), exist_ok=True)

with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields + ["review_label", "review_note"])
    w.writeheader()
    for r in rows:
        r["review_label"] = ""
        r["review_note"] = ""
        w.writerow(r)

print("OK ->", out, "rows:", len(rows))