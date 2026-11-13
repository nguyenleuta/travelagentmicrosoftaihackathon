import copy
import json
import unittest
from travel.demo_rewards import DATA, attach_demo_redemptions
from travel.engine import validate, demo_offers, compare
from test_engine import BASE


class DemoRewardsTests(unittest.TestCase):
    def test_card_specific_hyatt_and_base_jetblue(self):
        _,preferred=self.search({"demo_bonuses":False,"chase_card":"sapphire_preferred"})
        _,reserve=self.search({"demo_bonuses":False,"chase_card":"sapphire_reserve"})
        hotel=lambda r:next(o for o in r["hotels"] if o["id"]=="NYC-H2")["demo_redemption"]
        self.assertEqual(hotel(preferred)["payments"][0]["bank_points"],32000)
        self.assertEqual(hotel(reserve)["payments"][0]["bank_points"],24000)
        jet=next(o for o in preferred["flights"] if o["id"]=="NYC-F2")["demo_redemption"]
        self.assertEqual(jet["payments"][0]["bank_points"],18000)
        self.assertEqual(jet["payments"][1]["bank_points"],22500)
        self.assertEqual(jet["payments"][1]["bonus_percent"],0)

    def test_freedom_alone_is_blocked_and_pooled_sapphire_works(self):
        _,r=self.search({"chase_card":"freedom_only"})
        self.assertFalse(r["flights"][0]["demo_redemption"]["payments"][0]["supported"])
        _,r=self.search({"chase_card":"freedom_with_preferred"})
        self.assertTrue(r["flights"][0]["demo_redemption"]["payments"][0]["supported"])

    def search(self, overrides=None):
        q=validate({**BASE, **(overrides or {})})
        f,h=demo_offers(q)
        return q,compare(q,f,h)

    def test_southwest_bonus_automatic_and_amex_unsupported(self):
        _,r=self.search({"chase_balance":16000})
        d=r["flights"][0]["demo_redemption"]
        self.assertEqual(d["points"],20000)
        chase,amex=d["payments"]
        self.assertEqual(chase["bank_points"],16000)
        self.assertEqual(chase["bonus_saves_points"],4000)
        self.assertEqual(chase["shortfall"],0)
        self.assertFalse(amex["supported"])
        self.assertEqual(d["cash_usd"],46.2)  # selected carry-on + demo award taxes

    def test_two_travelers_and_checked_bags(self):
        _,r=self.search({"travelers":2,"checked_bag":True})
        d=next(o for o in r["flights"] if o["id"]=="NYC-F1")["demo_redemption"]
        self.assertEqual(d["points"],40000)
        self.assertEqual(d["payments"][0]["bank_points"],32000)
        self.assertEqual(d["cash_usd"],182.4)

    def test_expired_demo_bonus_not_applied(self):
        q,r=self.search()
        config=json.loads(DATA.read_text(encoding='utf-8'))
        config["calculation_date"]="2026-12-01"
        attach_demo_redemptions(r["flights"],q,config)
        d=r["flights"][0]["demo_redemption"]
        self.assertEqual(d["payments"][0]["bonus_percent"],0)
        self.assertEqual(d["payments"][0]["bank_points"],20000)

    def test_jetblue_rounding_and_modeled_excise(self):
        _,r=self.search()
        d=next(o for o in r["flights"] if o["id"]=="NYC-F2")["demo_redemption"]
        amex=d["payments"][1]
        self.assertEqual(amex["bank_points"],18000)
        self.assertEqual(amex["without_bonus_points"],22500)
        self.assertEqual(amex["excise_fee_usd"],10.8)
        self.assertGreaterEqual(amex["received_partner_points"],d["points"])

    def test_hilton_demo_bonus_and_unavailable_chase(self):
        _,r=self.search()
        d=r["hotels"][0]["demo_redemption"]
        self.assertFalse(d["payments"][0]["supported"])
        amex=d["payments"][1]
        self.assertEqual(amex["bank_points"],35000)
        self.assertEqual(amex["leftover_partner_points"],1000)

    def test_live_mode_cannot_inherit_demo_prices(self):
        q,r=self.search()
        live=compare({**q,"mode":"live"},copy.deepcopy(r["flights"]),copy.deepcopy(r["hotels"]))
        self.assertTrue(all("demo_redemption" not in o for o in live["flights"]+live["hotels"]))

    def test_selection_returns_chosen_fixture_comparison(self):
        q,r=self.search()
        selected=compare(q,r["flights"],r["hotels"],selected={"flight":"NYC-F3","hotel":"NYC-H1"})
        flight=next(o for o in selected["flights"] if o["id"]==selected["summary"]["flight_offer_id"])
        self.assertEqual(flight["demo_redemption"]["program"],"United MileagePlus")
