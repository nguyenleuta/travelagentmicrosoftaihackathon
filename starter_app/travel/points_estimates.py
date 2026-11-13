"""Explicit cash-based planning estimates, never airline award quotes."""
from decimal import Decimal, ROUND_CEILING
from .transfer_quotes import card_rules

PROGRAMS = {"southwest":"Southwest Rapid Rewards", "jetblue":"JetBlue TrueBlue",
    "united":"United MileagePlus", "delta":"Delta SkyMiles", "air canada":"Air Canada Aeroplan",
    "british airways":"British Airways Avios", "air france":"Air France / KLM Flying Blue",
    "klm":"Air France / KLM Flying Blue", "american airlines":"AAdvantage miles",
    "frontier":"FRONTIER Miles", "hilton":"Hilton Honors", "hyatt":"World of Hyatt"}


def cash_points_estimate(offer, query):
    if query["mode"] != "live" or offer.get("points_required",0) > 0:
        return None
    name = str(offer.get("carrier") or offer.get("name") or "").lower()
    program = next((p for keyword,p in PROGRAMS.items() if keyword in name), None)
    points = int((Decimal(str(offer["total_cash_usd"])) * 100).to_integral_value(rounding=ROUND_CEILING))
    rules = card_rules(query.get("chase_card","sapphire_preferred"))
    payments=[]
    for bank,label in (("chase","Chase"),("amex","Amex")):
        rule = next((r for r in rules.values() if r["bank"]==bank and r["partner"]==program),None)
        if not rule:
            payments.append({"bank":bank,"label":label,"supported":False,
                "reason":"Freedom Unlimited alone cannot transfer." if bank=="chase" and query.get("chase_card")=="freedom_only" else "No supported direct transfer." if program else "Loyalty program not identified."})
            continue
        blocks=int((Decimal(points)/rule["partner_block"]).to_integral_value(rounding=ROUND_CEILING))
        needed=blocks*rule["bank_block"]
        fee=min(Decimal(99),Decimal(needed)*Decimal("0.0006")) if rule.get("us_airline_fee") else Decimal(0)
        payments.append({"bank":bank,"label":label,"supported":True,"points":needed,
            "shortfall":max(0,needed-query.get(bank+"_balance",0)),
            "bank_block":rule["bank_block"],"partner_block":rule["partner_block"],
            "source_url":rule["source"],"transfer_fee_usd":float(round(fee,2))})
    return {"type":"cash_based_estimate","program":program,"points":points,"payments":payments,
        "cash_usd":offer["total_cash_usd"],"cash_complete":offer["price_complete"],
        "assumed_cents_per_partner_point":1,
        "note":"Estimate: $1 = 100 airline/hotel points (1 cent per point). Not an actual award quote, portal price or availability check. Base transfer ratios only; no promotions applied. Award taxes and fees are unknown. Unknown cash charges also remain excluded."}
