"""Check maintained base ratios against official search excerpts; never infer award fares."""
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from .providers import _request
from .promotions import official_url
from .transfer_quotes import card_rules


def check_rate(data):
    if not isinstance(data, dict):
        raise ValueError("Provide a JSON object.")
    rule = card_rules(data.get("chase_card", "sapphire_preferred")).get(data.get("route"))
    if not rule:
        raise ValueError("Choose a transfer route supported by your card.")
    award = data.get("award_points")
    if award not in (None, ""):
        if isinstance(award, bool) or not str(award).isdigit() or not 0 < int(award) <= 100000000:
            raise ValueError("Award points must be a whole number greater than zero.")
        award = int(award)
    else:
        award = None
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        raise ValueError("Set SERPAPI_KEY in .env and restart the server.")
    bank = "Chase" if rule["bank"] == "chase" else "American Express Membership Rewards"
    issuer_site = "chase.com" if rule["bank"] == "chase" else "americanexpress.com"
    keyword = "JetBlue" if "jetblue" in data["route"] else rule["partner"]
    try:
        payload = _request({"engine":"google", "q":f'site:{issuer_site} {keyword} {rule["bank_block"]} {rule["partner_block"]}', "gl":"us", "hl":"en", "num":10}, key)
    except Exception:
        raise ValueError("Rate lookup failed. Check your SerpApi key, quota and network.") from None
    if not isinstance(payload, dict):
        raise ValueError("Rate lookup returned an invalid response.")
    a, b = rule["bank_block"], rule["partner_block"]
    # Search evidence must explicitly state this ratio, not just name the partner.
    from math import gcd
    common = gcd(a, b)
    ratios = {(a,b),(a//common,b//common)}
    patterns = [rf'(?<![\d.]){x}[\w\s®™]{{0,45}}?(?::|to|=|equals|becomes?)\s*{y}(?![\d.])' for x,y in ratios]
    aliases = {"chase_jetblue":"jetblue", "amex_jetblue":"trueblue", "chase_hyatt":"hyatt"}
    partner = aliases.get(data["route"], rule["partner"].split()[0].lower())
    sources, matched = [], []
    for item in payload.get("organic_results", []):
        if not isinstance(item, dict):
            continue
        link = official_url(item.get("link"))
        if not link or re.search(r'/(?:en-ca|en-gb|ca|uk|in|au|en-au)/',link,re.I):
            continue
        text = str(item.get("title", ""))+" "+str(item.get("snippet", ""))
        evidence = {"url":link,"title":str(item.get("title", "Official source"))[:160], "excerpt":str(item.get("snippet", ""))[:600]}
        sources.append(evidence)
        bank_named = "chase" in text.lower() if rule["bank"]=="chase" else any(x in text.lower() for x in ("american express", "membership rewards", "amex"))
        if data["route"] == "chase_hyatt":
            card_word = "reserve" if data.get("chase_card") in {"sapphire_reserve","freedom_with_reserve"} else "preferred"
            bank_named = bank_named and card_word in text.lower()
        if bank_named and partner in text.lower() and not re.search(r'bonus|promotion|\bexpired\b', text, re.I) and any(re.search(p,text.replace(",",""),re.I) for p in patterns):
            matched.append(evidence)
    converted = None
    if award:
        blocks = int((Decimal(award)/b).to_integral_value(rounding=ROUND_CEILING))
        converted = {"bank_points":blocks*a,"partner_points":blocks*b,"leftover":blocks*b-award,
                     "rate_basis":"official_search_excerpt" if matched else "stored_base_rate_unconfirmed_live"}
    return {"rule":rule,"observed_utc":datetime.now(timezone.utc).isoformat(),
        "status":"ratio_supported_by_official_search_excerpt" if matched else "rate_not_confirmed",
        "sources":matched or sources[:4], "award_points":award,"conversion":converted,
        "note":"The calculator uses the stored base ratio when the search does not confirm it. That fallback is not live verification. Open the issuer source to confirm current US terms and card eligibility. No promotional bonus applied. Airline/hotel award points are user-entered, not fetched or availability-verified. Cash taxes and transfer fees are additional."}
