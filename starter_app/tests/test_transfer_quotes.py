import unittest
from travel.transfer_quotes import compare_quotes, RULES


BASE = {"route":"chase_southwest", "offer_id":"SW1", "portal_points":27500,
        "award_points":20000, "bank_balance":50000, "partner_balance":0,
        "point_value_cents":1, "partner_value_cents":1,
        "portal_cash_usd":0, "award_cash_usd":5.60, "transfer_fee_usd":0,
        "same_offer_confirmed":True, "eligible_confirmed":True}


class TransferQuoteTests(unittest.TestCase):
    def test_main_airline_rules(self):
        for route, rule in RULES.items():
            with self.subTest(route=route):
                r = compare_quotes({**BASE,"route":route})
                self.assertGreaterEqual(r["transfer"]["partner_points_received"],20000)
                self.assertEqual(r["transfer"]["bank_points"] % rule["bank_block"],0)
                self.assertEqual(rule["kind"],"hotel" if route=="amex_hilton" else "flight")

    def test_jetblue_amex_costs_more_bank_points_than_chase(self):
        chase = compare_quotes({**BASE,"route":"chase_jetblue"})
        amex = compare_quotes({**BASE,"route":"amex_jetblue"})
        self.assertEqual(chase["transfer"]["bank_points"],20000)
        self.assertEqual(amex["transfer"]["bank_points"],25000)
        self.assertEqual(amex["transfer"]["excise_fee_usd"],15)
        self.assertEqual(amex["transfer"]["cash_usd"],20.6)

    def test_amex_delta_excise_fee_cap_and_no_transfer_case(self):
        r=compare_quotes({**BASE,"route":"amex_delta","award_points":1000000})
        self.assertEqual(r["transfer"]["excise_fee_usd"],99)
        r=compare_quotes({**BASE,"route":"amex_delta","partner_balance":20000})
        self.assertEqual(r["transfer"]["excise_fee_usd"],0)

    def test_portal_vs_southwest_example(self):
        r = compare_quotes(BASE)
        self.assertEqual(r["transfer"]["bank_points"],20000)
        self.assertEqual(r["bank_points_difference"],7500)
        self.assertEqual(r["economic_difference_usd"],69.4)
        self.assertEqual(r["evidence_status"],"user_entered_unverified")

    def test_hilton_ratio_rounding_and_leftovers(self):
        r = compare_quotes({**BASE,"route":"amex_hilton","award_points":45001})
        self.assertEqual(r["transfer"]["bank_points"],23000)
        self.assertEqual(r["transfer"]["partner_points_received"],46000)
        self.assertEqual(r["transfer"]["leftover_partner_points"],999)

    def test_existing_partner_points_are_not_free(self):
        r = compare_quotes({**BASE,"partner_balance":20000,"partner_value_cents":2,"transfer_fee_usd":10})
        self.assertEqual(r["transfer"]["bank_points"],0)
        self.assertEqual(r["transfer"]["cash_usd"],5.6)
        self.assertEqual(r["transfer"]["economic_cost_usd"],405.6)
        self.assertEqual(r["lower_economic_cost"],"portal")

    def test_fees_can_reverse_points_savings(self):
        r = compare_quotes({**BASE,"award_cash_usd":100})
        self.assertEqual(r["bank_points_difference"],7500)
        self.assertEqual(r["lower_economic_cost"],"portal")

    def test_insufficient_balance_and_unconfirmed_inputs(self):
        r = compare_quotes({**BASE,"bank_balance":1000,"eligible_confirmed":False})
        self.assertFalse(r["both_affordable"])
        self.assertFalse(r["comparison_confirmed_by_user"])
        self.assertEqual(r["transfer"]["shortfall"],19000)

    def test_bad_or_missing_quotes_rejected(self):
        for field, value in (("route","amex_aa"),("portal_points",1.5),("award_points",-1),
                             ("portal_cash_usd",None),("award_cash_usd",float("nan")),
                             ("transfer_fee_usd",True),("point_value_cents",0),("partner_balance",float("inf"))):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compare_quotes({**BASE,field:value})
