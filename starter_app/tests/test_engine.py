import unittest
from travel.engine import validate, demo_offers, compare, price_flight, price_hotel


BASE = {
    "origin": "DALLAS", "destination": "NYC", "depart_date": "2027-03-11",
    "return_date": "2027-03-15", "travelers": 1, "mode": "demo",
    "carry_on": True, "checked_bag": False, "card_name": "Demo Card",
    "card_multiplier": 3, "point_value_cents": 1.5, "award_points_balance": 90000,
}


class EngineTests(unittest.TestCase):
    def test_validate_dates(self):
        with self.assertRaises(ValueError):
            validate({**BASE, "return_date": "2027-03-11"})
        with self.assertRaises(ValueError):
            validate({**BASE, "return_date": "garbage"})

    def test_losing_award_remains_available_for_comparison(self):
        q = validate({**BASE, "point_value_cents": 2})
        f, h = demo_offers(q)
        summary = compare(q, f, h)["summary"]
        self.assertIsNone(summary["best_illustrative_award"])
        candidate = summary["comparison_illustrative_award"]
        self.assertIsNotNone(candidate)
        self.assertLess(candidate["economic_savings_usd"], 0)
        self.assertGreater(candidate["trip_economic_cost_usd"], summary["modeled_trip_cash_usd"])

    def test_comparison_award_still_respects_balance(self):
        q = validate({**BASE, "award_points_balance": 0})
        f, h = demo_offers(q)
        self.assertIsNone(compare(q, f, h)["summary"]["comparison_illustrative_award"])

    def test_unknown_fees_do_not_produce_complete_trip(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        for offer in f:
            offer["fees_incomplete"] = True
        result = compare(q, f, h)
        self.assertFalse(result["summary"]["price_complete"])
        self.assertEqual(result["summary"]["known_trip_cash_usd"], 1003)
        self.assertIsNone(result["summary"]["modeled_trip_cash_usd"])
        self.assertIsNone(result["summary"]["best_illustrative_award"])
        self.assertTrue(result["flights"][0]["unknown_fee_categories"])
        self.assertIn("unknown", result["summary"]["recommendations"][0])

    def test_missing_bag_price_is_unknown_but_included_bag_is_complete(self):
        q = validate({**BASE, "checked_bag": True})
        f, _ = demo_offers(q)
        offer = {**f[0], "checked_bag_included": False, "checked_bag_per_traveler_usd": None}
        self.assertIn("Checked bags", price_flight(offer, q)["unknown_fee_categories"])
        offer["checked_bag_included"] = True
        self.assertTrue(price_flight(offer, q)["price_complete"])

    def test_missing_hotel_fees_are_not_complete(self):
        q = validate(BASE)
        _, h = demo_offers(q)
        quote = price_hotel({**h[0], "mandatory_fees_usd": None}, q)
        self.assertFalse(quote["price_complete"])
        self.assertIn("Mandatory hotel taxes and fees", quote["unknown_fee_categories"])

    def test_missing_component_has_no_trip_total(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        for flights, hotels in ((f, []), ([], h), ([], [])):
            result = compare(q, flights, hotels)["summary"]
            self.assertIsNone(result["known_trip_cash_usd"])
            self.assertIsNone(result["modeled_trip_cash_usd"])
            self.assertIsNone(result["best_illustrative_award"])

    def test_award_must_beat_cheapest_cash_not_its_own_price(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        cheap = {**f[0], "base_per_traveler_usd": 100, "mandatory_per_traveler_usd": 0,
                 "carry_on_included": True, "award_points_per_traveler": 0}
        expensive = {**cheap, "id": "EXPENSIVE", "base_per_traveler_usd": 1000,
                     "award_points_per_traveler": 20000, "award_taxes_per_traveler_usd": 20}
        hotel = {**h[0], "award_points_total": 0}
        self.assertIsNone(compare(q, [cheap, expensive], [hotel])["summary"]["best_illustrative_award"])
        expensive["award_points_per_traveler"] = 1000
        result = compare(q, [cheap, expensive], [hotel])["summary"]
        award = result["best_illustrative_award"]
        self.assertEqual(award["economic_savings_usd"], 65)
        self.assertEqual(award["cash_alternative_usd"], 100)
        self.assertEqual(award["trip_economic_cost_usd"], result["modeled_trip_cash_usd"] - 65)
        self.assertTrue(award["scenario_only"])

    def test_missing_award_taxes_and_insufficient_balance_exclude_awards(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        for offer in f:
            offer["award_taxes_per_traveler_usd"] = None
        for offer in h:
            offer["award_taxes_usd"] = None
        self.assertIsNone(compare(q, f, h)["summary"]["best_illustrative_award"])
        f, h = demo_offers(q)
        self.assertIsNone(compare({**q, "award_points_balance": 0}, f, h)["summary"]["best_illustrative_award"])

    def test_validate_party_and_rewards(self):
        for bad in (0, 7):
            with self.assertRaises(ValueError):
                validate({**BASE, "travelers": bad})
        with self.assertRaises(ValueError):
            validate({**BASE, "point_value_cents": 10000})

    def test_never_fabricate_missing_fixture(self):
        q = validate({**BASE, "depart_date": "2027-03-12"})
        f, h = demo_offers(q)
        result = compare(q, f, h)
        self.assertEqual(result["flights"], [])
        self.assertIsNone(result["summary"]["modeled_trip_cash_usd"])

    def test_invalid_numeric_inputs_are_not_silently_replaced(self):
        for field in ("travelers", "card_multiplier", "point_value_cents", "award_points_balance"):
            for value in (None, True, "invalid", float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        validate({**BASE, field: value})

    def test_counts_must_be_whole_numbers(self):
        for field in ("travelers", "award_points_balance"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "whole number"):
                    validate({**BASE, field: 1.5})
        self.assertEqual(validate({**BASE, "travelers": "2"})["travelers"], 2)

    def test_baggage_flags_must_be_boolean(self):
        for field in ("carry_on", "checked_bag"):
            for value in ("false", 0, None):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "true or false"):
                        validate({**BASE, field: value})

    def test_demo_sources_clearly_fictional(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        self.assertTrue(all(o["data_status"] == "FICTIONAL DEMO DATA" for o in f+h))
        self.assertTrue(all(o["checkout_verified"] is False for o in f+h))
        self.assertTrue(all(o["booking_url"] is None for o in f+h))
        self.assertIn("fictional", compare(q, f, h)["warnings"][0].lower())

    def test_checked_bag_increases_unincluded_fare(self):
        q = validate(BASE)
        flights, _ = demo_offers(q)
        f1 = next(f for f in flights if f["id"] == "NYC-F1")
        without = price_flight(f1, q)["total_cash_usd"]
        with_bag = price_flight(f1, {**q, "checked_bag": True})["total_cash_usd"]
        self.assertEqual(without, 253)
        self.assertEqual(with_bag, 298)
        self.assertEqual(with_bag - without, 45)

    def test_points_are_not_cash_discount(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        result = compare(q, f, h)
        self.assertEqual(result["summary"]["modeled_trip_cash_usd"], 1003)
        first = result["flights"][0]
        self.assertEqual(first["reward_points_earned"], 759)
        self.assertEqual(first["total_cash_usd"], 253)
        self.assertLess(first["cash_after_rewards_estimate_usd"], 253)
        self.assertIn("Lowest modeled flight cost", result["summary"]["recommendations"][0])

    def test_tokyo_two_travelers(self):
        q = validate({**BASE, "destination": "TOKYO", "depart_date": "2027-04-23", "return_date": "2027-04-30", "travelers": 2})
        f, h = demo_offers(q)
        result = compare(q, f, h)
        self.assertEqual(result["flights"][0]["total_cash_usd"], 1700)
        self.assertEqual(result["hotels"][0]["total_cash_usd"], 1040)
        self.assertEqual(result["summary"]["modeled_trip_cash_usd"], 2740)

    def test_awards_balance_and_valuation(self):
        q = validate(BASE)
        f, h = demo_offers(q)
        candidate = next(a for a in f if a["id"] == "NYC-F2")
        low = price_flight(candidate, {**q, "award_points_balance": 1000})
        high = price_flight(candidate, {**q, "award_points_balance": 100000})
        self.assertFalse(low["award_affordable"])
        self.assertTrue(high["award_affordable"])
        self.assertEqual(high["points_required"], 18000)
        self.assertAlmostEqual(high["award_economic_cost_usd"], 290.0)

    def test_hotel_award_not_double_counted(self):
        q = validate(BASE)
        _, h = demo_offers(q)
        hotel = next(a for a in h if a["id"] == "NYC-H2")
        quote = price_hotel(hotel, q)
        self.assertEqual(quote["total_cash_usd"], 810)
        self.assertEqual(quote["award_economic_cost_usd"], 750)


if __name__ == "__main__":
    unittest.main()
