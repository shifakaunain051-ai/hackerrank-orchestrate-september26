# Buy or Wait? submission engine

Run from the repository root:

```powershell
python code/main.py
python code/evaluation/main.py
python -m unittest discover -s code/tests -v
```

`main.py` uses only Python's standard library. It reads the participant-facing
CSV data, transcribes the supplied image-only amounts through a reviewed mapping,
constructs a 90-day deterministic forecast, ranks valid full/partial/installment/
wait candidates, and writes root-level `output.csv`. `evaluation/main.py` checks
the final file's schema, IDs, bounds, categorical values, and payment chronology.

No model, API, credential, or live financial data is used.
