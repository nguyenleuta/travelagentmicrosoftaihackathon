"""Compare user-entered portal and award quotes; no inventory claims."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING

RULES = {
    "chase_southwest": {"bank": "chase", "name": "Chase", "partner": "Southwest Rapid Rewards",
        "bank_block": 1000, "partner_block": 1000,
        "source": "https://www.chase.com/personal/credit-cards/education/basics/how-to-transfer-chase-ultimate-rewards-points",
        "ratio_source": "https://thepointsguy.com/loyalty-programs/transfer-chase-ultimate-rewards-southwest"},
    "amex_hilton": {"bank": "amex", "name": "Amex", "partner": "Hilton Honors",
        "bank_block": 1000, "partner_block": 2000,
        "source": "https://global.americanexpress.com/rewards/transfer?partner=5629f189e4b0b3d3bd79cc4f"},
}

CHASE_SOURCE = "https://www.chase.com/personal/credit-cards/education/basics/how-to-transfer-chase-ultimate-rewards-points"
AMEX_SOURCE = "https://global.americanexpress.com/rewards/transfer"
AMEX_TERMS = "https://www.americanexpress.com/content/dam/amex/us/rewards/membership-rewards/mr-terms-conditions-november-2026.pdf"
for key, partner in (("united", "United MileagePlus"), ("jetblue", "JetBlue TrueBlue"),
                     ("aeroplan", "Air Canada Aeroplan"), ("british_airways", "British Airways Avios"),
                     ("flying_blue", "Air France / KLM Flying Blue")):
    RULES["chase_" + key] = {"bank":"chase", "name":"Chase", "partner":partner,
        "bank_block":1000, "partner_block":1000, "source":CHASE_SOURCE,
        "ratio_source":"https://thepointsguy.com/loyalty-programs/chase-ultimate-rewards-transfer-partners"}
for key, partner in (("delta", "Delta SkyMiles"), ("jetblue", "JetBlue TrueBlue"),
                     ("aeroplan", "Air Canada Aeroplan"), ("british_airways", "British Airways Avios"),
                     ("flying_blue", "Air France / KLM Flying Blue")):
    RULES["amex_" + key] = {"bank":"amex", "name":"Amex", "partner":partner,
        "bank_block":250 if key == "jetblue" else 1000,
        "partner_block":200 if key == "jetblue" else 1000,
        "source":AMEX_SOURCE,
        "ratio_source": "https://www.aircanada.com/ca/en/ado/home/aeroplan/your-aeroplan/conversion-programs.html" if key == "aeroplan" else AMEX_SOURCE,
        "us_airline_fee":key in {"delta", "jetblue"}}
for key, rule in RULES.items():
    rule["kind"] = "hotel" if key == "amex_hilton" else "flight"

CHASE_CARDS = {"sapphire_preferred":"Sapphire Preferred", "sapphire_reserve":"Sapphire Reserve",
    "freedom_only":"Freedom Unlimited only", "freedom_with_preferred":"Freedom + Sapphire Preferred",
    "freedom_with_reserve":"Freedom + Sapphire Reserve"}
RULES["chase_hyatt"] = {"bank":"chase", "name":"Chase", "partner":"World of Hyatt", "kind":"hotel",
    "bank_block":1000, "partner_block":750,
    "source":"https://media.chase.com/news/Meet-the-New-Chase-Sapphire-Preferred"}


def card_rules(card="sapphire_preferred"):
    if card not in CHASE_CARDS:
        raise ValueError("Choose a supported Chase card.")
    rules = {key:dict(value) for key,value in RULES.items() if not (card=="freedom_only" and value["bank"]=="chase")}
    if "chase_hyatt" in rules and card in {"sapphire_reserve", "freedom_with_reserve"}:
        rules["chase_hyatt"]["partner_block"] = 1000
    return rules


def compare_quotes(data):
    if not isinstance(data, dict) or data.get("route") not in RULES:
        raise ValueError("Choose a supported transfer route.")
    rule = card_rules(data.get("chase_card", "sapphire_preferred")).get(data["route"])
    if rule is None:
        raise ValueError("Freedom Unlimited alone cannot transfer to travel partners. An eligible Sapphire card is required.")

    def numeric(key, whole=False, positive=False):
        try:
            if isinstance(data.get(key), bool):
                raise ValueError()
            value = Decimal(str(data.get(key)))
            if not value.is_finite() or not 0 <= value <= 100000000 or (positive and value == 0):
                raise ValueError()
            if whole and value != value.to_integral_value():
                raise ValueError()
            if not whole and value != value.quantize(Decimal("0.01")):
                raise ValueError()
            return value
        except (InvalidOperation, ValueError):
            raise ValueError(f"Enter a valid {'whole number' if whole else 'amount (up to two decimal places)'} for {key}.") from None

    portal = numeric("portal_points", whole=True, positive=True)
    award = numeric("award_points", whole=True, positive=True)
    balance = numeric("bank_balance", whole=True)
    partner_balance = numeric("partner_balance", whole=True)
    cpp = numeric("point_value_cents", positive=True)
    if cpp > 10:
        raise ValueError("Point value must be at most 10 cents.")
    portal_cash = numeric("portal_cash_usd")
    award_cash = numeric("award_cash_usd")
    transfer_fee = numeric("transfer_fee_usd")
    deficit = max(Decimal(0), award - partner_balance)
    blocks = (deficit / rule["partner_block"]).to_integral_value(rounding=ROUND_CEILING)
    bank_used = blocks * rule["bank_block"]
    received = blocks * rule["partner_block"]
    excise_fee = min(Decimal("99"), bank_used * Decimal("0.0006")) if rule.get("us_airline_fee") else Decimal(0)
    existing_used = min(award, partner_balance)
    # Value existing partner points separately; do not treat them as free.
    partner_cpp = numeric("partner_value_cents", positive=True)
    if partner_cpp > 10:
        raise ValueError("Partner point value must be at most 10 cents.")
    portal_economic = portal_cash + portal * cpp / 100
    transfer_cash = award_cash + (transfer_fee if bank_used else 0) + excise_fee
    transfer_economic = transfer_cash + bank_used * cpp / 100 + existing_used * partner_cpp / 100
    difference = portal_economic - transfer_economic
    portal_ok, transfer_ok = balance >= portal, balance >= bank_used
    confirmed = data.get("same_offer_confirmed") is True and data.get("eligible_confirmed") is True
    return {"rule": rule, "checked_date": "2026-11-13", "evidence_status": "user_entered_unverified",
        "offer_id": str(data.get("offer_id", ""))[:100],
        "portal": {"bank_points": int(portal), "cash_usd": float(portal_cash),
                   "economic_cost_usd": float(round(portal_economic, 2)), "shortfall": int(max(0, portal-balance))},
        "transfer": {"bank_points": int(bank_used), "partner_points_received": int(received),
            "excise_fee_usd": float(round(excise_fee, 2)),
            "existing_partner_points_used": int(existing_used), "leftover_partner_points": int(received-deficit),
            "cash_usd": float(transfer_cash), "economic_cost_usd": float(round(transfer_economic, 2)),
            "shortfall": int(max(0, bank_used-balance))},
        "bank_points_difference": int(portal-bank_used), "economic_difference_usd": float(round(difference, 2)),
        "lower_economic_cost": "transfer" if difference > 0 else "portal" if difference < 0 else "tie",
        "both_affordable": portal_ok and transfer_ok, "comparison_confirmed_by_user": confirmed,
        "fee_source": AMEX_TERMS if rule.get("us_airline_fee") else None,
        "note": "User-entered quotes, not independently verified. US base ratios; no transfer bonus. Amex US-airline excise fee is added automatically where applicable; entered transfer fees are additional fees only. Airline program is the booking program, not necessarily the operating carrier. Confirm matching itinerary/room, dates, travelers, fees, award availability and eligibility. Transfers may be irreversible."}
