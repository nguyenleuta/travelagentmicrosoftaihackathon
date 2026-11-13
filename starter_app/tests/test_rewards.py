import unittest
from travel.engine import validate, demo_offers, compare
from travel.rewards import equivalents
from test_engine import BASE


class WalletTests(unittest.TestCase):
    def test_equivalents_use_separate_values_and_balances(self):
        q = validate({**BASE, "chase_balance": 30000, "amex_balance": 1000,
                      "chase_value_cents": 2, "amex_value_cents": 1})
        f, h = demo_offers(q)
        offer = compare(q, f, h)["flights"][0]
        chase, amex = offer["points_payment"]["cash_equivalents"]
        self.assertEqual(chase["points"], 12650)
        self.assertEqual(chase["shortfall"], 0)
        self.assertEqual(amex["points"], 25300)
        self.assertEqual(amex["shortfall"], 24300)
        self.assertEqual(offer["total_cash_usd"], 253)
        self.assertEqual(q["point_value_cents"], BASE["point_value_cents"])

    def test_cash_price_does_not_invent_american_airlines_awards(self):
        record = equivalents({"carrier":"American Airlines", "total_cash_usd":300}, validate(BASE))
        self.assertIsNone(record["award_points"])
        self.assertEqual(record["transfers"], [])

    def test_hilton_rounds_bank_points_and_keeps_cash_fees(self):
        record = equivalents({"total_cash_usd":500, "award_program":"Hilton Honors",
            "points_required":45001,"award_fees_usd":25,"award_price_complete":True},
            validate({**BASE,"amex_balance":22000}))
        transfer = record["transfers"][0]
        self.assertEqual(transfer["points"],23000)
        self.assertEqual(transfer["partner_points"],46000)
        self.assertEqual(transfer["leftover_partner_points"],999)
        self.assertEqual(transfer["shortfall"],1000)
        self.assertEqual(record["award_fees_usd"],25)

    def test_no_name_based_award_inference(self):
        record = equivalents({"name":"Hilton Hotel", "total_cash_usd":500}, validate(BASE))
        self.assertEqual(record["transfers"],[])

    def test_wallet_validation(self):
        for key, value in (("chase_balance",-1),("amex_balance",1.5),("chase_value_cents",0),("amex_value_cents",float("nan"))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate({**BASE,key:value})
