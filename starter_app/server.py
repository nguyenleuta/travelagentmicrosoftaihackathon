"""Run with: python server.py. No third-party Python packages required."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from travel.engine import compare, demo_offers, validate
from travel.providers import live_offers
from travel.transfer_quotes import compare_quotes
from travel.promotions import public_promotions
from travel.live_rates import check_rate

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
MIME = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml"}


def load_local_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in {"SERPAPI_KEY", "PORT"} and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == "/api/health":
            return self._json(200, {"ok": True, "app": "FareForge Student Starter", "live_configured": bool(os.environ.get("SERPAPI_KEY"))})
        if path == "/":
            path = "/index.html"
        file_path = (WEB / path.lstrip("/")).resolve()
        if not file_path.is_relative_to(WEB.resolve()) or not file_path.is_file():
            return self._json(404, {"error": "Not found"})
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(file_path.suffix, "application/octet-stream") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path not in {"/api/search", "/api/compare", "/api/rewards-quote", "/api/promotions", "/api/transfer-rate"}:
            return self._json(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > (200000 if self.path == "/api/compare" else 20000):
                raise ValueError("Invalid request size")
            supplied = json.loads(self.rfile.read(length).decode("utf-8"))
            if self.path == "/api/transfer-rate":
                return self._json(200, check_rate(supplied))
            if self.path == "/api/promotions":
                if not isinstance(supplied, dict):
                    raise ValueError("Provide a JSON object.")
                return self._json(200, public_promotions(supplied.get("bank")))
            if self.path == "/api/rewards-quote":
                return self._json(200, compare_quotes(supplied))
            if self.path == "/api/compare":
                if not isinstance(supplied, dict):
                    raise ValueError("Provide a JSON object.")
                query = validate(supplied.get("query"))
                flights, hotels = supplied.get("flights"), supplied.get("hotels")
                selected = supplied.get("selected")
                if (not isinstance(flights, list) or not isinstance(hotels, list) or
                    len(flights) > 100 or len(hotels) > 100 or
                    not all(isinstance(o, dict) and isinstance(o.get("id"), str) for o in flights + hotels) or
                    not isinstance(selected, dict)):
                    raise ValueError("Provide valid offers and selected IDs.")
                return self._json(200, compare(query, flights, hotels, selected=selected))
            query = validate(supplied)
            if query["mode"] == "demo":
                flights, hotels = demo_offers(query)
                warnings = []
            else:
                flights, hotels, warnings = live_offers(query)
            return self._json(200, compare(query, flights, hotels, warnings))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)[:400]})
        except Exception as exc:
            self.log_error("Request failed: %s", type(exc).__name__)
            return self._json(502, {"error": "Provider or server error. See terminal log and try again."})


def main() -> None:
    load_local_env()
    port = int(os.environ.get("PORT", "8000"))
    print(f"FareForge Student Starter: http://127.0.0.1:{port}")
    print("Demo mode = FICTIONAL OFFERS. Live mode requires an authorized SerpApi key.")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
