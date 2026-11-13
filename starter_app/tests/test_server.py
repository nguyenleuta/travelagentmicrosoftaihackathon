import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from server import Handler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_health(self):
        with urlopen(self.base + "/api/health", timeout=5) as resp:
            self.assertTrue(json.load(resp)["ok"])

    def test_selection_recalculates_without_provider_calls(self):
        from travel.engine import validate, demo_offers
        from unittest.mock import patch
        q = validate({"origin":"DALLAS", "destination":"NYC", "depart_date":"2027-03-11", "return_date":"2027-03-15"})
        f, h = demo_offers(q)
        body = json.dumps({"query":q,"flights":f,"hotels":h,"selected":{"flight":"NYC-F2","hotel":"NYC-H2"}}).encode()
        req = Request(self.base + "/api/compare", data=body, headers={"Content-Type":"application/json"})
        with patch("server.live_offers", side_effect=AssertionError("Must not call provider")):
            with urlopen(req, timeout=5) as resp:
                result = json.load(resp)
        self.assertEqual(result["summary"]["modeled_trip_cash_usd"], 1098)

    def test_static_html(self):
        with urlopen(self.base + "/", timeout=5) as resp:
            text = resp.read().decode()
        self.assertIn("FareForge", text)

    def test_search_api(self):
        body = json.dumps({"origin":"DALLAS","destination":"NYC", "depart_date":"2027-03-11",
                           "return_date":"2027-03-15","travelers":1,"mode":"demo"}).encode()
        req = Request(self.base + "/api/search", data=body, headers={"Content-Type":"application/json"}, method="POST")
        with urlopen(req, timeout=5) as resp:
            result = json.load(resp)
        self.assertGreaterEqual(len(result["flights"]), 2)
        self.assertIsNotNone(result["summary"]["modeled_trip_cash_usd"])

    def test_static_path_escape_blocked(self):
        with self.assertRaises(HTTPError) as ex:
            urlopen(self.base + "/%2e%2e/server.py", timeout=5)
        self.assertEqual(ex.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
