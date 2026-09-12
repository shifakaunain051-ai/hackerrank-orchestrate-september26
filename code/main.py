"""Deterministic submission engine for HackerRank Orchestrate: Buy or Wait?.

Run from the repository root with: python code/main.py
No network, credentials, or model calls are used.  Supporting prose is evidence only;
it is never executed or treated as an instruction.
"""
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset"
OUT_COLUMNS = ["request_id", "amount_safe_to_pay", "affordability_status",
               "recommended_payment_method", "payment_plan",
               "earliest_date_for_full_payment", "spending_changes_needed",
               "decision_explanation"]
VALID_STATUS = {"affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"}
VALID_METHODS = {"full_payment", "partial_payment", "installments", "wait", "not_recommended"}


def rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def D(value, default="0"):
    return Decimal(str(value if value not in (None, "") else default))


def dt(value):
    return date.fromisoformat(value[:10])


def money(value):
    value = D(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


# Values transcribed from the supplied financial documents.  They are data, not
# instructions; keeping this small mapping makes image-derived records explicit
# and avoids silently converting an unknown blank amount into zero.
IMAGE_AMOUNTS = {
    "event_253": D("4365000"), "event_1442": D("24500"), "event_1545": D("15450"),
    "event_1700": D("4875"), "event_1786": D("1450"), "event_3051": D("6190"),
    "event_3231": D("1280"), "event_4535": D("28500"), "event_5170": D("1690"),
    "event_6033": D("7725"), "event_6859": D("41300"), "event_7307": D("42.75"),
    "event_7941": D("890"), "event_9421": D("615"), "event_9806": D("1299"),
    "event_10521": D("3700"),
}


class Engine:
    def __init__(self):
        self.profiles = {r["user_id"]: r for r in rows("financial_profiles.csv")}
        self.events = defaultdict(list)
        for r in rows("financial_events.csv"):
            r["amount_d"] = IMAGE_AMOUNTS.get(r["event_id"], D(r["amount"]))
            self.events[r["user_id"]].append(r)
        self.options = defaultdict(list)
        for r in rows("request_payment_options.csv"):
            self.options[r["request_id"]].append(r)
        self.rates = {(r["rate_date"], r["from_currency"], r["to_currency"]): D(r["rate"])
                      for r in rows("exchange_rates.csv")}

    def amount_home(self, event, home):
        amount = event["amount_d"]
        cur = event["currency"]
        if not cur or cur == home:
            return amount
        day = event["settlement_date"] or event["event_date"]
        rate = self.rates.get((day, cur, home))
        if rate is not None:
            return amount * rate
        inverse = self.rates.get((day, home, cur))
        if inverse:
            return amount / inverse
        raise ValueError(f"No exchange rate for {event['event_id']}: {cur}->{home} on {day}")

    def recurring_series(self, user, start):
        """Find repeating, cash-relevant records prior to the request date."""
        profile = self.profiles[user]
        home = profile["home_currency"]
        grouped = defaultdict(list)
        for e in self.events[user]:
            if e["status"] in {"failed", "cancelled", "unrealized"} or not e["amount_d"]:
                continue
            day = dt(e["settlement_date"] or e["event_date"])
            # A specifically scheduled next salary is confirmation of the same
            # recurring payroll pattern, but no other future settled record is
            # allowed to leak into the decision.
            is_near_scheduled_income = (e["status"] == "scheduled" and e["event_type"] == "income"
                                        and day <= start + timedelta(days=45))
            if (day >= start and not is_near_scheduled_income) or e["direction"] not in {"credit", "debit"}:
                continue
            # Variable essentials rotate merchants, so their category rather
            # than merchant text identifies the recurring commitment.
            key = (e["direction"], e["event_type"], e["category"])
            grouped[key].append((day, self.amount_home(e, home), e))
        result = []
        for key, vals in grouped.items():
            vals.sort()
            if len(vals) < 3 and not (key[0] == "credit" and key[2] == "salary" and len(vals) >= 2):
                continue
            gaps = [(vals[i][0] - vals[i - 1][0]).days for i in range(1, len(vals))]
            gaps = [g for g in gaps if 2 <= g <= 45]
            if len(gaps) < 2 and not (key[0] == "credit" and key[2] == "salary" and len(gaps) == 1):
                continue
            gaps.sort(); gap = gaps[len(gaps) // 2]
            # A cadence needs consistent enough intervals; random one-off records do not qualify.
            if max(gaps) - min(gaps) > max(3, gap // 2):
                continue
            recent = vals[-min(4, len(vals)):]
            amounts = [x[1] for x in recent]
            direction = key[0]
            # Expenses are deliberately conservative; income is only confirmed recurring salary.
            if direction == "credit" and key[2] != "salary":
                continue
            projected = max(amounts) if direction == "debit" else amounts[-1]
            result.append({"key": key, "last": vals[-1][0], "gap": gap, "amount": projected,
                           "event": vals[-1][2], "direction": direction})
        return result

    def base_cashflows(self, user, start, changes=()):
        """Return dated deltas for the next 90 days, plus recurring series metadata."""
        end = start + timedelta(days=90)
        profile = self.profiles[user]; home = profile["home_currency"]
        flows = defaultdict(Decimal)
        series = self.recurring_series(user, start)
        changed = {c[1]: c for c in changes}
        # Explicit future scheduled/pending cash events are stronger than a forecast.
        explicit_keys = set()
        for e in self.events[user]:
            day = dt(e["settlement_date"] or e["event_date"])
            if not (start <= day <= end) or e["status"] not in {"scheduled", "pending"}:
                continue
            if e["direction"] == "credit" and (e["status"] == "pending" or e["event_type"] != "income"):
                continue
            if e["direction"] not in {"credit", "debit"}:
                continue
            amount = self.amount_home(e, home)
            flows[day] += amount if e["direction"] == "credit" else -amount
            explicit_keys.add((e["direction"], e["event_type"], e["category"], day))
        for s in series:
            day = s["last"] + timedelta(days=s["gap"])
            while day < start:
                day += timedelta(days=s["gap"])
            while day <= end:
                key_day = (*s["key"], day)
                if key_day not in explicit_keys:
                    amount = s["amount"]
                    action = changed.get(s["event"]["event_id"])
                    if s["direction"] == "debit" and action:
                        if action[0] == "stop":
                            day += timedelta(days=s["gap"]); continue
                        amount = action[2]
                    flows[day] += amount if s["direction"] == "credit" else -amount
                day += timedelta(days=s["gap"])
        return flows, series

    def simulate(self, user, start, payments=(), changes=()):
        p = self.profiles[user]
        flows, series = self.base_cashflows(user, start, changes)
        for day, amount in payments:
            flows[day] -= amount
        balance = D(p["current_available_balance"]); minimum = D(p["minimum_balance_to_keep"])
        lowest = balance
        for n in range(91):
            day = start + timedelta(days=n)
            balance += flows[day]
            lowest = min(lowest, balance)
        return lowest >= minimum - Decimal("0.01"), lowest, flows, series

    def safe_today(self, user, request):
        start = dt(request["request_date"]); requested = D(request["requested_amount"])
        p = self.profiles[user]
        _, low, _, _ = self.simulate(user, start)
        return max(D(0), min(requested, (low - D(p["minimum_balance_to_keep"])).quantize(Decimal("0.01"))))

    def earliest_full(self, user, request):
        start = dt(request["request_date"]); amount = D(request["requested_amount"])
        for n in range(91):
            day = start + timedelta(days=n)
            ok, _, _, _ = self.simulate(user, start, [(day, amount)])
            if ok:
                return day
        return None

    def change_candidates(self, user, request):
        profile = self.profiles[user]
        reduce_cats = set(filter(None, profile["expense_categories_user_is_willing_to_reduce"].split("|")))
        stop_cats = set(filter(None, profile["expense_categories_user_is_willing_to_stop"].split("|")))
        _, series = self.base_cashflows(user, dt(request["request_date"]))
        options = []
        for s in series:
            e = s["event"]
            if s["direction"] != "debit" or e["category"] in set(profile["expense_categories_to_protect"].split("|")):
                continue
            if e["flexibility"] == "stoppable" and e["category"] in stop_cats:
                options.append(("stop", e["event_id"], D(0)))
            if e["flexibility"] == "reducible" and e["category"] in reduce_cats and e["minimum_allowed_amount"]:
                options.append(("reduce_to", e["event_id"], D(e["minimum_allowed_amount"])))
        # Most useful changes first; combinations below are bounded by challenge rules.
        options.sort(key=lambda x: x[2])
        valid = []
        for size in range(1, min(3, len(options)) + 1):
            for group in combinations(options, size):
                if len({x[1] for x in group}) == size:
                    valid.append(group)
        return valid

    def installments(self, request):
        for opt in self.options[request["request_id"]]:
            if opt["payment_method"] != "installments":
                continue
            count = int(opt["number_of_payments"])
            first = dt(opt["first_payment_date"])
            freq = int(opt["payment_frequency_days"])
            yield opt, [(first + timedelta(days=freq * i), D(opt["payment_amount"])) for i in range(count)]

    def fmt_plan(self, payments):
        return "|".join(f"{day.isoformat()}:{money(amount)}" for day, amount in sorted(payments))

    def explain(self, request, method, changes, earliest):
        p = self.profiles[request["user_id"]]; amount = money(request["requested_amount"]); cur = p["home_currency"]
        if method == "full_payment":
            suffix = " after the permitted flexible-spending change" if changes else ""
            return f"Pay {cur} {amount} in full; the 90-day forecast keeps the {cur} {money(p['minimum_balance_to_keep'])} minimum{suffix}."
        if method == "installments":
            return f"Use the available installment schedule; every payment keeps the 90-day forecast above the {cur} {money(p['minimum_balance_to_keep'])} minimum."
        if method == "partial_payment":
            return f"Make a safe partial payment today and complete it by {earliest.isoformat()} without breaching the minimum balance."
        if method == "wait":
            return f"Wait until {earliest.isoformat()}; paying earlier would put the {cur} {money(p['minimum_balance_to_keep'])} minimum at risk."
        return "This request cannot be completed safely within the 90-day forecast while protecting essential commitments and the minimum balance."

    def decide(self, request):
        user = request["user_id"]; start = dt(request["request_date"]); deadline = dt(request["desired_completion_date"])
        requested = D(request["requested_amount"]); profile = self.profiles[user]
        methods = set(filter(None, profile["payment_methods_user_will_consider"].split("|")))
        safe = self.safe_today(user, request); earliest = self.earliest_full(user, request)
        full_ok, _, _, _ = self.simulate(user, start, [(start, requested)])
        if full_ok and "full_payment" in methods:
            return self.row(request, safe, "affordable_now", "full_payment", [(start, requested)], start, ())
        # Full payment with the smallest permitted changes is preferable to a dearer plan.
        if "full_payment" in methods:
            for changes in self.change_candidates(user, request):
                ok, _, _, _ = self.simulate(user, start, [(start, requested)], changes)
                if ok:
                    return self.row(request, safe, "affordable_with_plan", "full_payment", [(start, requested)], earliest, changes)
        candidates = []
        if "installments" in methods:
            limit = profile["max_installment_months"]
            for opt, plan in self.installments(request):
                if limit and int(opt["number_of_payments"]) > int(limit):
                    continue
                ok, _, _, _ = self.simulate(user, start, plan)
                if ok:
                    candidates.append((D(opt["total_payable_amount"]), len(plan), opt["payment_option_id"], plan))
            if candidates:
                _, _, _, plan = sorted(candidates)[0]
                return self.row(request, safe, "affordable_with_plan", "installments", plan, earliest, ())
        if (request["allows_partial_payment"].lower() == "true" and "partial_payment" in methods
                and D(0) < safe < requested and earliest and earliest <= deadline):
            plan = [(start, safe), (earliest, requested - safe)]
            ok, _, _, _ = self.simulate(user, start, plan)
            if ok:
                return self.row(request, safe, "affordable_with_plan", "partial_payment", plan, earliest, ())
        if earliest and "full_payment" in methods:
            return self.row(request, safe, "affordable_later", "wait", [(earliest, requested)], earliest, ())
        return self.row(request, safe, "not_affordable", "not_recommended", (), None, ())

    def row(self, request, safe, status, method, plan, earliest, changes):
        change_text = "none" if not changes else "|".join(
            f"stop:{event}" if kind == "stop" else f"reduce_to:{event}:{money(amount)}"
            for kind, event, amount in changes)
        return {"request_id": request["request_id"], "amount_safe_to_pay": money(safe),
                "affordability_status": status, "recommended_payment_method": method,
                "payment_plan": self.fmt_plan(plan) if plan else "none",
                "earliest_date_for_full_payment": earliest.isoformat() if earliest else "",
                "spending_changes_needed": change_text,
                "decision_explanation": self.explain(request, method, changes, earliest)}


def validate(output, requests):
    assert [*output[0].keys()] == OUT_COLUMNS
    assert len(output) == len(requests) and len({r["request_id"] for r in output}) == len(output)
    amounts = {r["request_id"]: D(r["requested_amount"]) for r in requests}
    for row in output:
        assert row["affordability_status"] in VALID_STATUS and row["recommended_payment_method"] in VALID_METHODS
        assert D(0) <= D(row["amount_safe_to_pay"]) <= amounts[row["request_id"]]
        if row["payment_plan"] != "none":
            dates = [dt(x.split(":", 1)[0]) for x in row["payment_plan"].split("|")]
            assert dates == sorted(dates)


def main():
    engine = Engine()
    requests = rows("requests.csv")
    output = [engine.decide(r) for r in requests]
    validate(output, requests)
    with (ROOT / "output.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS); writer.writeheader(); writer.writerows(output)
    print(f"Wrote {len(output)} validated predictions to {ROOT / 'output.csv'}")


if __name__ == "__main__":
    main()
