import os
import unittest
from unittest.mock import patch
from travel.live_rates import check_rate


class LiveRateTests(unittest.TestCase):
    def check(self, snippet, **values):
        payload={"organic_results":[{"title":"American Express Membership Rewards JetBlue", "link":"https://global.americanexpress.com/rewards/transfer", "snippet":snippet}]}
        with patch.dict(os.environ,{"SERPAPI_KEY":"test"}),patch("travel.live_rates._request",return_value=payload):
            return check_rate({"route":"amex_jetblue","award_points":20000,**values})

    def test_explicit_ratio_enables_non_one_to_one_conversion(self):
        r=self.check("250 Points = 200 TrueBlue points")
        self.assertEqual(r["status"],"ratio_supported_by_official_search_excerpt")
        self.assertEqual(r["conversion"]["bank_points"],25000)
        self.assertEqual(r["conversion"]["partner_points"],20000)

    def test_missing_award_quote_shows_rate_only(self):
        r=self.check("250 Points = 200 TrueBlue points",award_points="")
        self.assertIsNone(r["conversion"])

    def test_unrelated_or_bonus_excerpts_never_confirm_base_rate(self):
        for text in ("Book JetBlue flights", "250 Points = 250 TrueBlue points", "250 Points = 200 TrueBlue points with a promotion"):
            self.assertEqual(self.check(text)["status"],"rate_not_confirmed")

    def test_unconfirmed_lookup_still_calculates_labeled_stored_estimate(self):
        r=self.check("Read about JetBlue travel")
        self.assertEqual(r["status"],"rate_not_confirmed")
        self.assertEqual(r["conversion"]["bank_points"],25000)
        self.assertEqual(r["conversion"]["rate_basis"],"stored_base_rate_unconfirmed_live")

    def test_prose_ratio_is_recognized(self):
        r=self.check("250 Membership Rewards points = 200 TrueBlue points")
        self.assertEqual(r["status"],"ratio_supported_by_official_search_excerpt")

    def test_rounding_and_bad_award_input(self):
        r=self.check("250 Points = 200 TrueBlue points",award_points=20001)
        self.assertEqual(r["conversion"]["bank_points"],25250)
        with self.assertRaises(ValueError):
            self.check("250 Points = 200 TrueBlue points",award_points=-1)

    def test_foreign_account_source_rejected(self):
        payload={"organic_results":[{"title":"Amex JetBlue", "link":"https://www.americanexpress.com/en-ca/transfer", "snippet":"250 points = 200 points"}]}
        with patch.dict(os.environ,{"SERPAPI_KEY":"test"}),patch("travel.live_rates._request",return_value=payload):
            r=check_rate({"route":"amex_jetblue","award_points":20000})
        self.assertEqual(r["sources"],[])

    def test_freedom_alone_cannot_get_transfer_conversion(self):
        with self.assertRaises(ValueError):
            check_rate({"route":"chase_jetblue","chase_card":"freedom_only"})
