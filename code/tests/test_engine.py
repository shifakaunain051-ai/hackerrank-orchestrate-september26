import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import D, Engine, IMAGE_AMOUNTS, money


class FinancialEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()

    def request(self, number):
        import csv
        with (Path(__file__).resolve().parents[2] / 'dataset' / 'sample_requests.csv').open(encoding='utf-8-sig') as f:
            return next(r for r in csv.DictReader(f) if r['request_id'] == f'request_{number:02d}')

    def test_affordable_purchase(self):
        row = self.engine.decide(self.request(1))
        self.assertEqual(row['recommended_payment_method'], 'full_payment')

    def test_installment_candidate_respects_option(self):
        row = self.engine.decide(self.request(12))
        self.assertEqual(row['recommended_payment_method'], 'installments')
        self.assertEqual(len(row['payment_plan'].split('|')), 3)

    def test_wait_and_not_affordable_paths(self):
        self.assertEqual(self.engine.decide(self.request(18))['recommended_payment_method'], 'wait')
        self.assertEqual(self.engine.decide(self.request(10))['recommended_payment_method'], 'not_recommended')

    def test_minimum_balance_and_recurring_expenses_are_used(self):
        request = self.request(1)
        safe = self.engine.safe_today(request['user_id'], request)
        self.assertLessEqual(safe, D(request['requested_amount']))
        ok, low, _, series = self.engine.simulate(request['user_id'], date.fromisoformat(request['request_date']))
        self.assertTrue(series)
        self.assertGreaterEqual(low, D(self.engine.profiles[request['user_id']]['minimum_balance_to_keep']))

    def test_future_income_and_currency_conversion(self):
        request = self.request(1)
        flows, _ = self.engine.base_cashflows(request['user_id'], date.fromisoformat(request['request_date']))
        self.assertTrue(any(delta > 0 for delta in flows.values()))
        event = next(e for e in self.engine.events['user_01'] if e['event_id'] == 'event_103')
        self.assertEqual(self.engine.amount_home(event, 'ZAR'), Decimal('23320'))

    def test_image_amounts_and_untrusted_text_boundary(self):
        self.assertEqual(IMAGE_AMOUNTS['event_253'], Decimal('4365000'))
        self.assertNotIn('ignore', self.engine.decide(self.request(3))['decision_explanation'].lower())

    def test_payment_and_spending_syntax(self):
        self.assertEqual(money('620.40'), '620.4')
        for action_group in self.engine.change_candidates('user_06', self.request(6)):
            self.assertLessEqual(len(action_group), 3)
            self.assertEqual(len({a[1] for a in action_group}), len(action_group))


if __name__ == '__main__':
    unittest.main()
