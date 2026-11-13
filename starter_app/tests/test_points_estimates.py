import unittest
from travel.points_estimates import cash_points_estimate
from travel.engine import validate
from test_engine import BASE


class PointsEstimateTests(unittest.TestCase):
    def test_cash_to_jetblue_then_bank_points(self):
        q=validate({**BASE,"mode":"live"})
        r=cash_points_estimate({"carrier":"JetBlue","total_cash_usd":100,"price_complete":True},q)
        self.assertEqual(r["points"],10000)
        self.assertEqual(r["payments"][0]["points"],10000)
        self.assertEqual(r["payments"][1]["points"],12500)
        self.assertEqual(r["payments"][1]["transfer_fee_usd"],7.5)
        self.assertEqual(r["type"],"cash_based_estimate")

    def test_no_fictional_transfer_for_aa_or_unknown_program(self):
        q=validate({**BASE,"mode":"live"})
        for carrier in ("American Airlines","Unknown airline"):
            r=cash_points_estimate({"carrier":carrier,"total_cash_usd":100,"price_complete":False},q)
            self.assertTrue(all(not p["supported"] for p in r["payments"]))
            self.assertFalse(r["cash_complete"])

    def test_actual_quote_and_demo_are_never_overwritten(self):
        offer={"carrier":"JetBlue","points_required":10000,"total_cash_usd":100,"price_complete":True}
        self.assertIsNone(cash_points_estimate(offer,validate({**BASE,"mode":"live"})))
        self.assertIsNone(cash_points_estimate({**offer,"points_required":0},validate(BASE)))

    def test_card_specific_hyatt_estimate(self):
        offer={"name":"Hyatt Hotel","total_cash_usd":100,"price_complete":True}
        preferred=cash_points_estimate(offer,validate({**BASE,"mode":"live","chase_card":"sapphire_preferred"}))
        reserve=cash_points_estimate(offer,validate({**BASE,"mode":"live","chase_card":"sapphire_reserve"}))
        self.assertEqual(preferred["payments"][0]["points"],14000)
        self.assertEqual(reserve["payments"][0]["points"],10000)
