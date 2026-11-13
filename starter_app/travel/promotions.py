"""Discover public transfer offer sources without claiming account eligibility."""
import copy
import os
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from .providers import _request

OFFICIAL = {"chase.com", "americanexpress.com", "southwest.com", "united.com", "delta.com",
            "jetblue.com", "aircanada.com", "britishairways.com", "flyingblue.com", "hilton.com"}
CACHE_SECONDS = 1800
_cache = {}
_lock = threading.Lock()


def official_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "https" and not parsed.username and not parsed.password and any(host == d or host.endswith("."+d) for d in OFFICIAL):
            return value
    except ValueError:
        pass
    return None


def public_promotions(bank):
    if bank not in {"chase", "amex"}:
        raise ValueError("Choose Chase or Amex.")
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        raise ValueError("Add SERPAPI_KEY to .env and restart the server to check public promotions.")
    with _lock:
        saved = _cache.get(bank)
        if saved and time.monotonic()-saved[0] < CACHE_SECONDS:
            return {**copy.deepcopy(saved[1]), "cached": True}
        now = datetime.now(timezone.utc)
        issuer = "Chase Ultimate Rewards" if bank == "chase" else "American Express Membership Rewards"
        sites = " OR ".join("site:"+domain for domain in sorted(OFFICIAL))
        search_name = "Chase" if bank == "chase" else "Amex Membership Rewards"
        query = f'({sites}) {search_name} transfer bonus {now:%Y}'
        try:
            payload = _request({"engine":"google", "q":query, "gl":"us", "hl":"en", "num":10},key)
        except Exception:
            # Never expose provider responses that might contain account or key information.
            raise ValueError("Public offer lookup failed. Check the SerpApi key, quota and network, then try again.") from None
        if not isinstance(payload, dict):
            raise ValueError("Public offer lookup returned an invalid response.")
        results, seen = [], set()
        for item in payload.get("organic_results") or []:
            if not isinstance(item, dict):
                continue
            link = official_url(item.get("link"))
            if not link or link in seen:
                continue
            seen.add(link)
            results.append({"title":str(item.get("title") or "Official source")[:160],
                "source_url":link, "excerpt":str(item.get("snippet") or "Open the source to read the offer terms.")[:600],
                "reported_publication_date":str(item["date"])[:80] if item.get("date") else None,
                "status":"unverified_search_result", "bonus_applied":False,
                "expiry_confirmed":False, "eligibility_confirmed":False})
        result = {"bank":bank, "issuer":issuer, "observed_utc":now.isoformat(),
            "cached":False, "results":results, "source_type":"SerpApi Google Search / official-domain results",
            "note":"Public search results, not confirmed active promotions. Search excerpts may be stale or incomplete. Open the official source to check dates, partner, US account eligibility and exclusions. No bonus is applied to prices; targeted account offers cannot be confirmed here."}
        _cache[bank] = (time.monotonic(),copy.deepcopy(result))
        return result
