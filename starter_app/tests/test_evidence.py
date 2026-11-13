import unittest
from travel.engine import compare, demo_offers, validate
from travel.evidence import evidence, source_link
from test_engine import BASE


class EvidenceTests(unittest.TestCase):
    def test_party_breakdown_adds_up_and_unselected_bags_are_explicit(self):
        q = validate({**BASE, "travelers": 2})
        f, h = demo_offers(q)
        result = compare(q, f, h)
        offer = next(o for o in result["flights"] if o["id"] == "NYC-F1")
        rows = offer["price_breakdown"]["components"]
        self.assertEqual(offer["total_cash_usd"], 506)
        self.assertEqual(sum(row["amount_usd"] for row in rows), 506)
        self.assertEqual(rows[-1]["status"], "not_selected")
        self.assertEqual(rows[-1]["amount_usd"], 0)

    def test_live_placeholder_zero_fees_are_unknown(self):
        q = validate({**BASE, "mode": "live"})
        offer = {"base_per_traveler_usd": 200, "mandatory_per_traveler_usd": 0,
                 "carry_on_per_traveler_usd": 0, "carry_on_included": None, "fees_incomplete": True}
        record = evidence(offer, q)
        self.assertFalse(record["price_complete"])
        self.assertIsNone(record["price_breakdown"]["components"][1]["amount_usd"])
        self.assertIsNone(record["price_breakdown"]["components"][2]["amount_usd"])
        self.assertEqual(record["price_breakdown"]["known_total_usd"], 200)

    def test_demo_cannot_be_upgraded_to_verified_or_get_booking_links(self):
        record = evidence({"checkout_verified": True, "booking_url": "https://example.com"}, validate(BASE))
        self.assertEqual(record["verification"]["status"], "synthetic_demo")
        self.assertFalse(record["verification"]["checkout_verified"])
        self.assertIsNone(record["verification"]["booking_url"])

    def test_bad_price_values_are_unknown_not_negative_discounts(self):
        for value in (None, -10, True, float("nan"), float("inf"), "bad"):
            record = evidence({"stay_rate_usd": value, "mandatory_fees_usd": 10}, validate(BASE), hotel=True)
            self.assertFalse(record["price_complete"])
            self.assertIsNone(record["price_breakdown"]["components"][0]["amount_usd"])
            self.assertEqual(record["price_breakdown"]["known_total_usd"], 10)

    def test_source_links_allow_only_web_urls_without_credentials(self):
        for value in ("javascript:alert(1)", "file:///secret", "https://user:password@example.com", "/relative", None):
            self.assertIsNone(source_link(value))
        self.assertEqual(source_link("https://example.com/offer?id=1"), "https://example.com/offer?id=1")

    def test_live_observation_is_preserved_without_claiming_verification(self):
        offer = {"observed_utc": "2026-11-13T17:00:00+00:00", "source": "Test provider", "checkout_verified": True}
        record = evidence(offer, validate({**BASE, "mode": "live"}))["verification"]
        self.assertEqual(record["observed_utc"], offer["observed_utc"])
        self.assertEqual(record["status"], "live_search_unverified")
        self.assertFalse(record["checkout_verified"])
