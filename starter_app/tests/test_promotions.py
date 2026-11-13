import os
import unittest
from unittest.mock import patch
from travel import promotions


class PromotionTests(unittest.TestCase):
    def setUp(self):
        promotions._cache.clear()

    def tearDown(self):
        promotions._cache.clear()

    def test_missing_key_and_invalid_bank(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,"SERPAPI_KEY"):
                promotions.public_promotions("chase")
        with self.assertRaises(ValueError):
            promotions.public_promotions("unknown")

    def test_only_official_https_results_and_never_apply_bonus(self):
        payload={"organic_results":[
            {"title":"Bonus", "link":"https://www.chase.com/offer", "snippet":"25% bonus", "date":"Yesterday"},
            {"title":"Duplicate", "link":"https://www.chase.com/offer"},
            {"link":"https://chase.com.attacker.example/offer"},
            {"link":"https://user:password@chase.com/offer"},
            {"link":"javascript:alert(1)"},
            {"link":"https://unofficial.example/bonus"}]}
        with patch.dict(os.environ,{"SERPAPI_KEY":"test-secret"}), patch.object(promotions,"_request",return_value=payload) as provider:
            result=promotions.public_promotions("chase")
        self.assertEqual(len(result["results"]),1)
        offer=result["results"][0]
        self.assertFalse(offer["bonus_applied"])
        self.assertFalse(offer["expiry_confirmed"])
        self.assertEqual(offer["reported_publication_date"],"Yesterday")
        self.assertNotIn("test-secret",str(result))
        self.assertEqual(provider.call_args[0][0]["engine"],"google")

    def test_cache_avoids_extra_provider_call(self):
        with patch.dict(os.environ,{"SERPAPI_KEY":"test"}), patch.object(promotions,"_request",return_value={}) as provider:
            first=promotions.public_promotions("amex")
            second=promotions.public_promotions("amex")
            self.assertFalse(first["cached"])
            self.assertTrue(second["cached"])
            self.assertEqual(provider.call_count,1)

    def test_empty_search_is_not_active_promotion(self):
        with patch.dict(os.environ,{"SERPAPI_KEY":"test"}), patch.object(promotions,"_request",return_value={}):
            result=promotions.public_promotions("chase")
        self.assertEqual(result["results"],[])
        self.assertIn("not confirmed active",result["note"])

    def test_provider_error_is_sanitized(self):
        with patch.dict(os.environ,{"SERPAPI_KEY":"secret"}), patch.object(promotions,"_request",side_effect=ValueError("secret")):
            with self.assertRaises(ValueError) as error:
                promotions.public_promotions("chase")
        self.assertNotIn("secret",str(error.exception))

    def test_real_subdomain_allowed(self):
        self.assertEqual(promotions.official_url("https://global.americanexpress.com/rewards/transfer"),"https://global.americanexpress.com/rewards/transfer")
