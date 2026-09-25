import csv
import json
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "http://127.0.0.1:8000/api/analyze"
INPUT_FILE = Path("targeted_validation_cases.csv")
OUTPUT_FILE = Path("targeted_validation_results.csv")

def call_api(text, category):
    payload = json.dumps({
        "text": text,
        "category": category
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))

rows = []
with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

results = []

for i, row in enumerate(rows, start=1):
    print(f"[{i}/{len(rows)}] {row['id']}")

    try:
        result = call_api(row["report"], row["category"])

        actual_sif = bool(result.get("is_sif", False))
        expected_sif = row["expected_sif"].strip().lower() == "true"
        decision_pass = actual_sif == expected_sif

        results.append({
            "id": row["id"],
            "category": row["category"],
            "type": row["type"],
            "expected_sif": expected_sif,
            "actual_sif": actual_sif,
            "decision_pass": decision_pass,
            "confidence": result.get("sif_prob"),
            "risk_tier": result.get("risk_tier"),
            "iogp_rule": result.get("iogp_rule"),
            "controls_present": result.get("controls_present"),
            "review_required": result.get("review_required"),
            "report": row["report"]
        })

    except Exception as e:
        print(f"  ERROR: {e}")

        results.append({
            "id": row["id"],
            "category": row["category"],
            "type": row["type"],
            "expected_sif": row["expected_sif"],
            "actual_sif": "ERROR",
            "decision_pass": False,
            "confidence": "",
            "risk_tier": "",
            "iogp_rule": "",
            "controls_present": "",
            "review_required": "",
            "report": row["report"]
        })

with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

total = len(results)
passed = sum(r["decision_pass"] is True for r in results)
failed = total - passed

print()
print("=" * 60)
print("TARGETED VALIDATION COMPLETE")
print("=" * 60)
print(f"Total cases : {total}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")
print(f"Pass rate   : {passed / total * 100:.1f}%")
print(f"Results     : {OUTPUT_FILE.resolve()}")
print("=" * 60)

print()
print("FAILED CASES:")
for r in results:
    if r["decision_pass"] is not True:
        print(
            f"{r['id']} | "
            f"{r['category']} | "
            f"Expected={r['expected_sif']} | "
            f"Actual={r['actual_sif']} | "
            f"Score={r['confidence']}"
        )
