import csv
import json
import requests
from pathlib import Path

API_URL = "http://127.0.0.1:8000/api/analyze"
INPUT_FILE = Path("validation_cases.csv")
OUTPUT_FILE = Path("validation_results.csv")

rows = []

with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        print(f"Testing {row['case_id']} - {row['pair_type']}...")

        payload = {
            "text": row["text"],
            "category": row["module"],
        }

        try:
            response = requests.post(
                API_URL,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            result = response.json()

            expected_sif = row["pair_type"] == "Dangerous"
            actual_sif = bool(result.get("is_sif", False))

            control_evidence = result.get("control_evidence", [])
            controls_present = bool(result.get("controls_present", False))
            review_required = bool(result.get("review_required", False))

            decision_pass = actual_sif == expected_sif

            rows.append({
                "case_id": row["case_id"],
                "module": row["module"],
                "pair_type": row["pair_type"],
                "expected_state": row["expected_state"],
                "category_returned": result.get("category", ""),
                "sif_score": result.get("sif_prob", ""),
                "is_sif": actual_sif,
                "expected_sif": expected_sif,
                "decision_pass": decision_pass,
                "iogp_rule": result.get("iogp_rule", ""),
                "controls_present": controls_present,
                "review_required": review_required,
                "control_evidence": " | ".join(control_evidence),
                "error": "",
            })

        except Exception as exc:
            rows.append({
                "case_id": row["case_id"],
                "module": row["module"],
                "pair_type": row["pair_type"],
                "expected_state": row["expected_state"],
                "category_returned": "",
                "sif_score": "",
                "is_sif": "",
                "expected_sif": row["pair_type"] == "Dangerous",
                "decision_pass": False,
                "iogp_rule": "",
                "controls_present": False,
                "review_required": False,
                "control_evidence": "",
                "error": str(exc),
            })

with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as f:
    fieldnames = [
        "case_id",
        "module",
        "pair_type",
        "expected_state",
        "category_returned",
        "sif_score",
        "is_sif",
        "expected_sif",
        "decision_pass",
        "iogp_rule",
        "controls_present",
        "review_required",
        "control_evidence",
        "error",
    ]

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print()
print("Validation completed.")
print(f"Results saved to: {OUTPUT_FILE}")

total = len(rows)
passed = sum(1 for r in rows if r["decision_pass"] is True)
failed = total - passed

print(f"Total cases : {total}")
print(f"Decision pass: {passed}")
print(f"Decision fail: {failed}")
