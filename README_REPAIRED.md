# OIL Guardian AI — repaired integration build

## Start

From this directory:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

The backend now has runtime adapters for all three modules:
- `ml_modules/near_miss/inference.py`
- `ml_modules/unsafe_condition/inference.py`
- `ml_modules/unsafe_act/inference.py` (V3 model)

The V3 dataset header was repaired because the source CSV contained an accidental first line:
`python predict_v3.py`

## Important model note

The three module outputs are SIF-likelihood scores. The current ensemble selects the module with the highest SIF score as a **routing heuristic**; it is not a trained 3-class category classifier.

## Validation

V3 leakage validation and strict similarity-group validation were run after repairing the CSV header. Both remained around 99.4% accuracy/F1 internally. This does not replace evaluation on a genuinely independent real-world dataset.
