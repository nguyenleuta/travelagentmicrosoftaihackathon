"""Separate subjective cash equivalents from award transfer scenarios."""
from decimal import Decimal, ROUND_CEILING

HILTON_SOURCE = "https://global.americanexpress.com/rewards/transfer?partner=5629f189e4b0b3d3bd79cc4f"


def equivalents(offer, query):
    options = []
    for bank, name in (("chase", "Chase"), ("amex", "Amex")):
        cpp = Decimal(str(query.get(bank + "_value_cents", 1)))
        points = int((Decimal(str(offer["total_cash_usd"])) * 100 / cpp).to_integral_value(rounding=ROUND_CEILING))
        balance = query.get(bank + "_balance", 0)
        options.append({"bank": bank, "name": name, "points": points,
                        "balance": balance, "shortfall": max(0, points - balance),
                        "value_cents": float(cpp), "type": "value_equivalent",
                        "note": "Value estimate only, not a portal rate, transfer quote or booking price."})
    program = offer.get("award_program")
    award_points = offer.get("points_required", 0)
    transfers = []
    # US base rate only; never infer award inventory or program from hotel name.
    if program == "Hilton Honors" and award_points > 0:
        needed = max(1000, int((Decimal(str(award_points)) / 2000).to_integral_value(rounding=ROUND_CEILING)) * 1000)
        transfers.append({"bank": "amex", "name": "Amex", "points": needed,
                          "partner_points": needed * 2, "leftover_partner_points": needed * 2 - award_points,
                          "ratio_label": "1,000 Amex → 2,000 Hilton points",
                          "shortfall": max(0, needed - query.get("amex_balance", 0)),
                          "source_url": HILTON_SOURCE, "checked_date": "2026-11-13",
                          "note": "US base ratio; no bonus applied. Confirm account eligibility, transfer fees and award availability. Scenario only."})
    return {"cash_equivalents": options, "award_program": program,
            "award_points": award_points if award_points > 0 else None,
            "award_fees_usd": offer.get("award_fees_usd") if offer.get("award_price_complete") else None,
            "transfers": transfers,
            "note": "Cash equivalents use your chosen point values. They do not establish transfer eligibility or award availability."}
