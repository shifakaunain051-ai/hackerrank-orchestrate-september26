"""Independent structural validator for the generated submission."""
import csv
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from main import D, Engine, OUT_COLUMNS, VALID_METHODS, VALID_STATUS, dt

def main():
    with (ROOT / "output.csv").open(encoding="utf-8", newline="") as f: output = list(csv.DictReader(f))
    with (ROOT / "dataset" / "requests.csv").open(encoding="utf-8-sig", newline="") as f: requests = list(csv.DictReader(f))
    assert list(output[0]) == OUT_COLUMNS, "column order/name mismatch"
    assert len(output) == len(requests) == 250, "wrong row count"
    expected = {r["request_id"]: Decimal(r["requested_amount"]) for r in requests}
    request_by_id = {r["request_id"]: r for r in requests}
    assert set(r["request_id"] for r in output) == set(expected), "request ids mismatch"
    for r in output:
        assert r["affordability_status"] in VALID_STATUS
        assert r["recommended_payment_method"] in VALID_METHODS
        assert Decimal("0") <= Decimal(r["amount_safe_to_pay"]) <= expected[r["request_id"]]
        if r["payment_plan"] != "none":
            parts = r["payment_plan"].split("|"); dates = [dt(p.split(":", 1)[0]) for p in parts]
            assert dates == sorted(dates), f"nonchronological {r['request_id']}"
            amounts = [D(p.split(":", 1)[1]) for p in parts]
            if r["recommended_payment_method"] in {"full_payment", "partial_payment"}:
                assert sum(amounts) == expected[r["request_id"]], f"payment total {r['request_id']}"
            if r["recommended_payment_method"] == "partial_payment":
                q = request_by_id[r["request_id"]]
                assert q["allows_partial_payment"].lower() == "true" and len(parts) == 2
                assert D(r["amount_safe_to_pay"]) == amounts[0]
                assert r["earliest_date_for_full_payment"] == dates[1].isoformat()
        if r["recommended_payment_method"] == "not_recommended":
            assert r["payment_plan"] == "none"
        if r["affordability_status"] == "affordable_now":
            assert r["earliest_date_for_full_payment"]
    # Recompute every recommendation. This verifies minimum-balance safety,
    # installment-option eligibility, partial-payment rules, and only-allowed
    # flexible spending changes using the same deterministic source data.
    engine = Engine()
    for row in output:
        recomputed = engine.decide(request_by_id[row["request_id"]])
        assert row == recomputed, f"unverified or impossible recommendation {row['request_id']}"
    print("PASS: schema, IDs, values, totals, chronology, option rules, cash safety, and spending changes validated")

if __name__ == "__main__": main()
