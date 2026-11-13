"""Automatic, strictly fictional redemption comparisons for demo fixtures."""
import json
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from .transfer_quotes import card_rules, CHASE_CARDS

DATA = Path(__file__).resolve().parent.parent / "data" / "demo_redemptions.json"


def attach_demo_redemptions(offers, query, config=None):
    if query["mode"] != "demo":
        return
    config = config or json.loads(DATA.read_text(encoding="utf-8"))
    as_of = date.fromisoformat(config["calculation_date"])
    rules = card_rules(query.get("chase_card", "sapphire_preferred"))
    for offer in offers:
        fixture = config["offers"].get(offer["id"])
        if not fixture:
            continue
        flight = "points_per_traveler" in fixture
        points = fixture["points_per_traveler"] * query["travelers"] if flight else fixture["points_total"]
        fees = Decimal(str(fixture["tax_per_traveler_usd"])) * query["travelers"] if flight else Decimal(str(fixture["tax_total_usd"]))
        if flight:
            fees += sum(Decimal(str(row["amount_usd"] or 0)) for row in offer["price_breakdown"]["components"] if row["label"] in {"Carry-on bags", "Checked bags"})
        payments = []
        for bank, label in (("chase", "Chase"), ("amex", "Amex")):
            route, rule = next(((key, r) for key, r in rules.items() if r["bank"] == bank and r["partner"] == fixture["program"]), (None, None))
            if not rule:
                reason = "Freedom Unlimited alone cannot transfer to travel partners." if bank=="chase" and query.get("chase_card")=="freedom_only" else "No supported direct transfer to this program."
                payments.append({"bank": bank, "label": label, "supported": False, "reason":reason})
                continue
            promo = next((p for p in config["promotions"] if p["route"] == route and date.fromisoformat(p["starts"]) <= as_of <= date.fromisoformat(p["ends"])), None)
            promo = promo if query.get("demo_bonuses", True) else None
            bonus = promo["bonus_percent"] if promo else 0
            effective_block = Decimal(rule["partner_block"]) * (1 + Decimal(bonus) / 100)
            blocks = (Decimal(points) / effective_block).to_integral_value(rounding=ROUND_CEILING)
            bank_points = int(blocks) * rule["bank_block"]
            received = int((blocks * effective_block).to_integral_value(rounding=ROUND_FLOOR))
            no_bonus = int((Decimal(points) / rule["partner_block"]).to_integral_value(rounding=ROUND_CEILING)) * rule["bank_block"]
            excise = min(Decimal(99), Decimal(bank_points) * Decimal("0.0006")) if rule.get("us_airline_fee") else Decimal(0)
            cash = fees + excise
            payments.append({"bank":bank, "label":label, "supported":True, "bank_points":bank_points,
                "card_label":CHASE_CARDS[query.get("chase_card","sapphire_preferred")] if bank=="chase" else "Membership Rewards",
                "cash_usd":float(round(cash, 2)), "excise_fee_usd":float(round(excise, 2)),
                "economic_cost_usd":float(round(cash + Decimal(bank_points) * Decimal(str(query.get(bank+"_value_cents",1))) / 100, 2)),
                "shortfall":max(0, bank_points-query.get(bank+"_balance",0)),
                "bank_block":rule["bank_block"], "partner_block":rule["partner_block"],
                "bonus_percent":bonus, "promotion_ends":promo["ends"] if promo else None,
                "without_bonus_points":no_bonus, "bonus_saves_points":no_bonus-bank_points,
                "received_partner_points":received, "leftover_partner_points":received-points})
        offer["demo_redemption"] = {"status":"fictional_demo", "program":fixture["program"],
            "carrier":fixture.get("carrier"), "points":points, "cash_usd":float(round(fees,2)),
            "calculation_date":config["calculation_date"], "payments":payments,
            "note":config["notice"]}
