# Architecture and Data Flow

```text
Traveler (browser)
      | origin / destination / dates / bags / card rewards
      v
web/index.html + web/app.js
      | POST /api/search
      v
server.py  ---> validate inputs, dispatch mode
      |
      +---- demo mode: data/sample_offers.json (fictional)
      |
      +---- live mode: travel/providers.py --> authorized SerpApi
      |                                         Google Flights + Hotels search
      v
travel/engine.py
      | normalize price and award assumptions
      | rank flight and hotel separately
      | calculate basic illustrative cash-vs-points economics
      v
Result JSON: flights, hotels, summary, warnings, source status
      |
      v
Browser: visible results, warnings, recommendations
```

## Components
- `server.py`: small HTTP server; uses `127.0.0.1` binding; handles GET and POST.
- `travel/engine.py`: pure comparison functions, validation, airport aliases, mock filtering.
- `travel/providers.py`: optional external search adapter and unverified offer mapping.
- `web/`: progressive enhancement and responsive accessible UI.
- `tests/`: deterministic quality gate; no external API calls required.

## Data contracts
An offer must not just be `{name, price}`. For production, define explicit fields for: quote ID, provider, precise flight segments / fare class / room ID, party size, currency, base fare, taxes, mandatory fees, luggage, booking channel, cancellation policy, timestamp, deep booking link, verification level, evidence and exceptions.

The demo models use `base_per_traveler_usd`, `mandatory_per_traveler_usd`, and baggage costs for flights, and `stay_rate_usd`, `mandatory_fees_usd` for hotels. `travel/evidence.py` produces a shared price breakdown for calculation and display. Missing fees are null; legacy zero fee placeholders flagged incomplete are shown as unknown. Known totals are partial estimates until every required amount is known. Source panels and JSON exports preserve the provider's observation time and unverified status; they do not establish checkout verification.

## Recommended future improvements
- Quote expiry and re-query; provider-specific booking and award adapters.
- Structured offer identity for comparing **exactly equivalent** flights and rooms.
- Audit log recording inputs, search outputs, source URLs and UTC collection time.
- Separate loyalty balance stores, authorized read-only connectors, valid transfer matrices.
- Backend secret store, rate limiting and provider caching.
- Optimization across multi-leg itineraries + hotels subject to traveler constraints.

## Scope
No agent can make a guaranteed booking simply by generating a link. Confirmation, inventory and final price must be verified through the provider at checkout. Do not use the prototype to collect payment details or full credit card numbers.
