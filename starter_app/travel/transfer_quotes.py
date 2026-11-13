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


def compare_quotes(data):
    if not isinstance(data, dict) or data.get("route") not in RULES:
        raise ValueError("Choose a supported transfer route.")
    rule = RULES[data["route"]]

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
    existing_used = min(award, partner_balance)
    # Value existing partner points separately; do not treat them as free.
    partner_cpp = numeric("partner_value_cents", positive=True)
    if partner_cpp > 10:
        raise ValueError("Partner point value must be at most 10 cents.")
    portal_economic = portal_cash + portal * cpp / 100
    transfer_cash = award_cash + (transfer_fee if bank_used else 0)
    transfer_economic = transfer_cash + bank_used * cpp / 100 + existing_used * partner_cpp / 100
    difference = portal_economic - transfer_economic
    portal_ok, transfer_ok = balance >= portal, balance >= bank_used
    confirmed = data.get("same_offer_confirmed") is True and data.get("eligible_confirmed") is True
    return {"rule": rule, "checked_date": "2026-11-13", "evidence_status": "user_entered_unverified",
        "offer_id": str(data.get("offer_id", ""))[:100],
        "portal": {"bank_points": int(portal), "cash_usd": float(portal_cash),
                   "economic_cost_usd": float(round(portal_economic, 2)), "shortfall": int(max(0, portal-balance))},
        "transfer": {"bank_points": int(bank_used), "partner_points_received": int(received),
            "existing_partner_points_used": int(existing_used), "leftover_partner_points": int(received-deficit),
            "cash_usd": float(transfer_cash), "economic_cost_usd": float(round(transfer_economic, 2)),
            "shortfall": int(max(0, bank_used-balance))},
        "bank_points_difference": int(portal-bank_used), "economic_difference_usd": float(round(difference, 2)),
        "lower_economic_cost": "transfer" if difference > 0 else "portal" if difference < 0 else "tie",
        "both_affordable": portal_ok and transfer_ok, "comparison_confirmed_by_user": confirmed,
        "note": "User-entered quotes, not independently verified. US base ratios; no transfer bonus. Confirm exact itinerary/room, dates, travelers, taxes, availability and account eligibility before transferring. Transfers may be irreversible."}
