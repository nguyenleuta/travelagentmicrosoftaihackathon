"""Price components and source evidence; never upgrades listing verification."""
import math
from urllib.parse import urlsplit


def amount(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) and parsed >= 0 else None
    except (ValueError, TypeError):
        return None


def source_link(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return None


def evidence(offer, query, hotel=False):
    rows = []
    multiplier = 1 if hotel else query["travelers"]
    incomplete = bool(offer.get("fees_incomplete") or offer.get("price_complete") is False)

    def add(label, key, status=None, extra=False):
        value = amount(offer.get(key))
        if status in ("included", "not_selected"):
            value = 0
        elif extra and incomplete and value == 0:
            # Legacy adapters use zero for unknown charges; do not display it as free.
            value = None
        rows.append({"label": label, "amount_usd": round(value * multiplier, 2) if value is not None else None,
                     "status": status or ("unknown" if value is None else "known")})

    if hotel:
        add("Stay rate", "stay_rate_usd")
        add("Mandatory hotel taxes and fees", "mandatory_fees_usd", extra=True)
    else:
        add("Flight fare", "base_per_traveler_usd")
        add("Mandatory flight taxes and fees", "mandatory_per_traveler_usd", extra=True)
        for flag, label in (("carry_on", "Carry-on bags"), ("checked_bag", "Checked bags")):
            status = "not_selected" if not query[flag] else "included" if offer.get(flag + "_included") is True else None
            add(label, flag + "_per_traveler_usd", status, extra=True)
    unknown = list(offer.get("unknown_fee_categories") or [])
    unknown += [row["label"] for row in rows if row["status"] == "unknown"]
    if incomplete:
        unknown.append("Other unconfirmed mandatory charges")
    unknown = list(dict.fromkeys(unknown))
    synthetic = query["mode"] == "demo" or "fictional" in str(offer.get("data_status", "")).lower() or offer.get("data_status") == "synthetic_demo"
    return {
        "price_breakdown": {"currency": "USD", "basis": "full stay" if hotel else "all travelers",
                            "traveler_count": query["travelers"], "components": rows,
                            "known_total_usd": round(sum(row["amount_usd"] or 0 for row in rows), 2)},
        "price_complete": not unknown, "fees_incomplete": bool(unknown), "unknown_fee_categories": unknown,
        "verification": {"status": "synthetic_demo" if synthetic else "live_search_unverified",
                         "label": "Fictional demo — cannot be booked" if synthetic else "Live listing — checkout not verified",
                         "provider": str(offer.get("source") or "Source unknown"),
                         "observed_utc": None if synthetic else offer.get("observed_utc"),
                         "source_url": None if synthetic else source_link(offer.get("source_url")),
                         "booking_url": None if synthetic else source_link(offer.get("booking_url")),
                         "checkout_verified": False,
                         "checks_needed": ["Confirm exact flight or room, dates and traveler count",
                                           "Confirm taxes, selected bags and mandatory charges",
                                           "Check cancellation rules and final checkout price",
                                           "Confirm award inventory and program eligibility if using points"]},
    }
