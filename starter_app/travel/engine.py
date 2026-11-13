"""Deterministic quote normalization, card points, and recommendations.

CRITICAL: Demo offers are fictional. Live offers from adapters are search-result
estimates, not checkout-verified booking inventory. Never label as guaranteed.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from .evidence import evidence
from .rewards import equivalents
from .transfer_quotes import RULES
from .demo_rewards import attach_demo_redemptions

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_offers.json"
CITY_AIRPORTS = {
    "DALLAS": {"DFW", "DAL"}, "NYC": {"JFK", "LGA", "EWR"},
    "NEW YORK": {"JFK", "LGA", "EWR"}, "TYO": {"HND", "NRT"},
    "TOKYO": {"HND", "NRT"}, "LAS VEGAS": {"LAS"}, "LAS": {"LAS"},
}
HOTEL_CITIES = {"JFK": "NYC", "LGA": "NYC", "EWR": "NYC", "NYC": "NYC", "NEW YORK": "NYC",
                "HND": "TYO", "NRT": "TYO", "TYO": "TYO", "TOKYO": "TYO", "LAS": "LAS", "LAS VEGAS": "LAS"}


def airports(value: str) -> set[str]:
    value = value.strip().upper()
    if "," in value:
        return {part.strip() for part in value.split(",") if part.strip()}
    return CITY_AIRPORTS.get(value, {value})


def hotel_city(value: str) -> str:
    return HOTEL_CITIES.get(value.strip().upper(), value.strip().upper())


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if result != result or result in (float("inf"), float("-inf")):
            return default
        return result
    except (TypeError, ValueError):
        return default


def validate(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("Provide a JSON object.")
    origin = str(request.get("origin", "")).strip().upper()
    destination = str(request.get("destination", "")).strip().upper()
    depart = str(request.get("depart_date", ""))
    returning = str(request.get("return_date", ""))
    if not origin or not destination or len(origin) > 30 or len(destination) > 40:
        raise ValueError("Enter valid origin and destination airports or city names.")
    try:
        outbound = date.fromisoformat(depart)
        inbound = date.fromisoformat(returning)
    except ValueError as exc:
        raise ValueError("Use YYYY-MM-DD travel dates.") from exc
    if inbound <= outbound:
        raise ValueError("Return date must be after departure date.")
    def input_number(key: str, default: float) -> float:
        value = request.get(key, default)
        if isinstance(value, bool):
            raise ValueError(f"{key} must be a finite number.")
        parsed = number(value, float("nan"))
        if parsed != parsed:
            raise ValueError(f"{key} must be a finite number.")
        return parsed

    traveler_count = input_number("travelers", 1)
    if not traveler_count.is_integer():
        raise ValueError("Travelers must be a whole number.")
    travelers = int(traveler_count)
    if not (1 <= travelers <= 6):
        raise ValueError("Travelers must be between 1 and 6.")
    mode = str(request.get("mode", "demo")).lower()
    if mode not in {"demo", "live"}:
        raise ValueError("Mode must be demo or live.")
    card_name = str(request.get("card_name", "Illustrative travel card"))[:64]
    multiplier = input_number("card_multiplier", 2)
    cpp = input_number("point_value_cents", 1.25)
    balance = input_number("award_points_balance", 0)
    if not balance.is_integer():
        raise ValueError("Points balance must be a whole number.")
    points = int(balance)
    if not (0 <= multiplier <= 20 and 0.1 <= cpp <= 10 and 0 <= points <= 100000000):
        raise ValueError("Review your rewards input values.")
    for key in ("checked_bag", "carry_on"):
        if key in request and not isinstance(request[key], bool):
            raise ValueError(f"{key} must be true or false.")
    wallets = {}
    for bank in ("chase", "amex"):
        balance = input_number(bank + "_balance", 0)
        wallet_cpp = input_number(bank + "_value_cents", 1)
        if not balance.is_integer() or not 0 <= balance <= 100000000 or not 0.1 <= wallet_cpp <= 10:
            raise ValueError("Review your Chase and Amex balances and point values.")
        wallets[bank + "_balance"] = int(balance)
        wallets[bank + "_value_cents"] = wallet_cpp
    return {"origin": origin, "destination": destination, "depart_date": depart, "return_date": returning,
            "travelers": travelers, "mode": mode, "card_name": card_name,
            "card_multiplier": multiplier, "point_value_cents": cpp, "award_points_balance": points,
            "checked_bag": bool(request.get("checked_bag", False)),
            "carry_on": bool(request.get("carry_on", True)), **wallets}


def demo_offers(query: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    origin_codes, destination_codes = airports(query["origin"]), airports(query["destination"])
    flights = [f for f in data["flights"]
               if f["origin"] in origin_codes and f["destination"] in destination_codes
               and f["depart_date"] == query["depart_date"] and f["return_date"] == query["return_date"]]
    hotels = [h for h in data["hotels"] if h["city"] == hotel_city(query["destination"])
              and h["checkin"] == query["depart_date"] and h["checkout"] == query["return_date"]
              and query["travelers"] <= h["max_occupancy"]]
    for offer in flights + hotels:
        offer["data_status"] = "FICTIONAL DEMO DATA"
        offer["checkout_verified"] = False
        offer["booking_url"] = None
    return flights, hotels


def price_evidence(offer: dict, query: dict, hotel: bool = False) -> dict:
    """Keep missing charges distinct from a confirmed zero-dollar charge."""
    return evidence(offer, query, hotel)


def price_flight(offer: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    travelers = query["travelers"]
    points = int(number(offer.get("award_points_per_traveler", 0)) * travelers)
    award_fees = round(number(offer.get("award_taxes_per_traveler_usd")) * travelers, 2)
    enriched = dict(offer, points_required=points, award_fees_usd=award_fees)
    enriched.update(price_evidence(offer, query))
    total = enriched["price_breakdown"]["known_total_usd"]
    enriched["total_cash_usd"] = total
    enriched["award_price_complete"] = bool(points and enriched["price_complete"] and
        number(offer.get("award_taxes_per_traveler_usd"), -1) >= 0)
    enriched["reward_points_earned"] = int(total * query["card_multiplier"])
    enriched["cash_after_rewards_estimate_usd"] = round(total - enriched["reward_points_earned"] * query["point_value_cents"] / 100, 2)
    enriched["award_economic_cost_usd"] = round(award_fees + points * query["point_value_cents"] / 100, 2) if points else None
    enriched["award_affordable"] = bool(points and query["award_points_balance"] >= points)
    return enriched


def price_hotel(offer: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    points = int(number(offer.get("award_points_total", 0)))
    fees = round(number(offer.get("award_taxes_usd")), 2)
    enriched = dict(offer, points_required=points, award_fees_usd=fees)
    enriched.update(price_evidence(offer, query, hotel=True))
    total = enriched["price_breakdown"]["known_total_usd"]
    enriched["total_cash_usd"] = total
    enriched["award_price_complete"] = bool(points and enriched["price_complete"] and
        number(offer.get("award_taxes_usd"), -1) >= 0)
    enriched["reward_points_earned"] = int(total * query["card_multiplier"])
    enriched["cash_after_rewards_estimate_usd"] = round(total - enriched["reward_points_earned"] * query["point_value_cents"] / 100, 2)
    enriched["award_economic_cost_usd"] = round(fees + points * query["point_value_cents"] / 100, 2) if points else None
    enriched["award_affordable"] = bool(points and query["award_points_balance"] >= points)
    return enriched


def compare(query: dict[str, Any], flight_raw: list[dict], hotel_raw: list[dict], warnings: list[str] | None = None, selected: dict | None = None) -> dict[str, Any]:
    flights = sorted([price_flight(f, query) for f in flight_raw], key=lambda f: f["total_cash_usd"])
    hotels = sorted([price_hotel(h, query) for h in hotel_raw], key=lambda h: h["total_cash_usd"])
    for offer in flights + hotels:
        offer.pop("demo_redemption", None)
        offer["points_payment"] = equivalents(offer, query)
    attach_demo_redemptions(flights + hotels, query)
    lowest_flight, lowest_hotel = (flights[0] if flights else None), (hotels[0] if hotels else None)
    if selected:
        for kind, entries in (("flight", flights), ("hotel", hotels)):
            chosen = next((o for o in entries if o["id"] == selected.get(kind)), None)
            if entries and chosen is None:
                raise ValueError(f"Choose a valid {kind} offer.")
            if kind == "flight":
                lowest_flight = chosen
            else:
                lowest_hotel = chosen
    total = round((lowest_flight["total_cash_usd"] if lowest_flight else 0) +
                  (lowest_hotel["total_cash_usd"] if lowest_hotel else 0), 2)
    best_award = None
    comparison_award = None
    complete = bool(lowest_flight and lowest_hotel and lowest_flight["price_complete"] and lowest_hotel["price_complete"])
    award_flights = [lowest_flight] if selected and lowest_flight else flights
    award_hotels = [lowest_hotel] if selected and lowest_hotel else hotels
    for kind, entries in (("flight", award_flights), ("hotel", award_hotels)):
        baseline = entries[0] if entries else None
        other = lowest_hotel if kind == "flight" else lowest_flight
        for offer in entries:
            if complete and offer["award_affordable"] and offer["award_price_complete"]:
                savings = round(baseline["total_cash_usd"] - offer["award_economic_cost_usd"], 2)
                candidate = {"kind": kind, "offer_id": offer["id"], "points": offer["points_required"],
                             "fees_usd": offer["award_fees_usd"], "economic_savings_usd": savings,
                             "cash_alternative_offer_id": baseline["id"],
                             "cash_alternative_usd": baseline["total_cash_usd"],
                             "award_economic_cost_usd": offer["award_economic_cost_usd"],
                             "trip_cash_outlay_usd": round(other["total_cash_usd"] + offer["award_fees_usd"], 2),
                             "trip_economic_cost_usd": round(other["total_cash_usd"] + offer["award_economic_cost_usd"], 2),
                             "scenario_only": True,
                             "award_program": offer.get("award_program")}
                if comparison_award is None or savings > comparison_award["economic_savings_usd"]:
                    comparison_award = candidate
    if comparison_award and comparison_award["economic_savings_usd"] > 0:
        best_award = comparison_award
    recommendations = []
    if selected:
        recommendations.append("Comparison uses your selected flight and hotel. Only awards on those offers are considered.")
    if lowest_flight:
        label = "Selected flight cost" if selected else "Lowest modeled flight cost" if lowest_flight["price_complete"] else "Lowest known flight estimate"
        detail = "including modeled selected bag fees" if lowest_flight["price_complete"] else "required fees remain unknown"
        recommendations.append(f"{label}: ${lowest_flight['total_cash_usd']:,.2f} for {query['travelers']} traveler(s); {detail}.")
    if lowest_hotel:
        label = "Selected hotel cost" if selected else "Lowest modeled hotel cost" if lowest_hotel["price_complete"] else "Lowest known hotel estimate"
        detail = "including modeled mandatory fees" if lowest_hotel["price_complete"] else "required fees remain unknown"
        recommendations.append(f"{label}: ${lowest_hotel['total_cash_usd']:,.2f} for the full stay; {detail}.")
    if best_award and best_award["economic_savings_usd"] > 0:
        recommendations.append(f"Scenario only: {best_award['kind']} award {best_award['offer_id']} uses {best_award['points']:,} points + ${best_award['fees_usd']:,.2f} cash fees. Its economic cost is ${best_award['award_economic_cost_usd']:,.2f}, versus ${best_award['cash_alternative_usd']:,.2f} for cash option {best_award['cash_alternative_offer_id']}. Estimated economic savings: ${best_award['economic_savings_usd']:,.2f}. With the other trip component paid in cash, trip cash outlay is ${best_award['trip_cash_outlay_usd']:,.2f} and economic cost is ${best_award['trip_economic_cost_usd']:,.2f}. Compare fare/room conditions; verify inventory and program eligibility. Earned points are excluded from this comparison.")
    elif complete:
        recommendations.append("No affordable award scenario beats this cash combination at your point valuation.")
    if not flights or not hotels:
        recommendations.append("Incomplete trip results: no flight or hotel match for part of this search. Do not describe the total as a complete trip quote.")
    all_warnings = list(warnings or [])
    if flights and hotels and not complete:
        all_warnings.append("Required fees are unknown. The known trip estimate is not a complete all-in price; award recommendations are withheld.")
    if best_award:
        all_warnings.append("Only one redemption is modeled. The entered balance is a scenario, not a verified program balance or proof of transfer eligibility. Fare and room conditions may differ.")
    if query["mode"] == "demo":
        all_warnings.insert(0, "DEMO MODE: all fares, hotels, carriers, points and rewards examples are fictional and cannot be booked.")
    else:
        all_warnings.insert(0, "LIVE SEARCH RESULTS are preliminary. Taxes, bag fees, room inclusions, fare rules, booking links, and checkout availability require independent verification.")
    return {"query": query, "flights": flights, "hotels": hotels, "transfer_rules": RULES,
            "summary": {"flight_offer_id": lowest_flight["id"] if lowest_flight else None,
                        "selection_mode": "manual" if selected else "cheapest",
                        "hotel_offer_id": lowest_hotel["id"] if lowest_hotel else None,
                        "price_complete": complete,
                        "known_trip_cash_usd": total if flights and hotels else None,
                        "modeled_trip_cash_usd": total if complete else None,
                        "best_illustrative_award": best_award,
                        "comparison_illustrative_award": comparison_award,
                        "modeled_points_earned_if_cash": (lowest_flight["reward_points_earned"] if lowest_flight else 0) + (lowest_hotel["reward_points_earned"] if lowest_hotel else 0),
                        "recommendations": recommendations},
            "warnings": all_warnings}
