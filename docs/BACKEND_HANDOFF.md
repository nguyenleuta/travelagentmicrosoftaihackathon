# Backend handoff for Nguyen

Implemented in Johnny's backend branch. Existing request fields and response sections stay in place.

## Price fields

Each offer also contains `price_breakdown` (USD, party/stay basis, component amounts and known total) and `verification` (source, observed time, links, status and remaining checks). Missing amounts are null; unselected bags have `not_selected` status and zero cost; included bags have `included` status. Legacy zero placeholders under `fees_incomplete=true` display as unknown. Totals are calculated from the same components shown in the UI.

The frontend has expandable price/source panels and a JSON evidence download. The download captures the search result, not proof of checkout verification. `verification.status` stays synthetic or unverified; this version has no trusted checkout evidence ingestion. Provider observation time is never replaced with export time. Safe provider-supplied web links are shown; missing links stay missing.

- Each offer now has `price_complete` and `unknown_fee_categories`.
- `fees_incomplete` is set when required amounts are missing or the provider flags incomplete coverage.
- `total_cash_usd` remains the known modeled amount. It is not a confirmed all-in amount when `price_complete` is false.
- Summary `known_trip_cash_usd` contains the known flight + hotel estimate, or null if either component is missing.
- Summary `modeled_trip_cash_usd` is null when either selected component has unknown fees or is missing.
- Summary `price_complete` describes modeled price coverage, never booking availability.

Frontend now distinguishes unknown fees from missing results. When the known total exists but the complete total is null, it shows the known estimate and lists unknown fees. Cards show dates and bag inclusion status. A cash-versus-points panel displays the single-award trip comparison. Search clears old results and ignores stale responses.

## Awards

The UI always shows both payment boxes. `comparison_illustrative_award` returns the best eligible scenario even when it loses to cash or ties. `best_illustrative_award` remains null unless points win. If there is no eligible scenario, the points box explains why comparison is unavailable. Both fields respect balance and complete-fee checks.

`best_illustrative_award` is null unless one affordable, fully modeled award beats the lowest known cash combination with complete fees. Savings compare against the cheapest cash option in that category, rather than the award offer's own cash price.

The candidate retains existing fields and adds `cash_alternative_offer_id`, `cash_alternative_usd`, `award_economic_cost_usd`, `trip_cash_outlay_usd`, `trip_economic_cost_usd`, and `scenario_only`.

Only one redemption is recommended. The other component is paid in cash. No combined program balance or transfer eligibility is assumed. Missing award taxes exclude a candidate. Earned points remain separate and are excluded from the award savings comparison.

Fare/room conditions can differ between alternatives; the explanation flags that limitation. These are scenario comparisons, not verified equivalent booking quotes.

## Provider expectations

Keep `fees_incomplete=true` when the provider has unknown fees, even if legacy numeric fields contain zero. Prefer null for genuinely missing prices. Keep real zero only for a confirmed zero charge. Set bag inclusion flags to true only when confirmed.

Johnny has also updated `starter_app/web/app.js` and `styles.css` while Nguyen handles the API. Provider files are unchanged. Pull these frontend changes before editing those files.

## Verification

Run `python scripts/portability_check.py` from the repo root. Regression cases cover missing fees, selected baggage, missing trip components, award baseline errors, missing award taxes, and insufficient points.

Optional frontend checks (Node.js needed only for these tests): `node starter_app/tests/frontend.test.cjs`. These check rendered unknown amounts, unsafe source text/links, losing award comparisons, and the JSON download. Python checks also cover breakdown arithmetic and verification status.

## Click-to-select update

The download button and export feature were removed. Search selects the cheapest known flight and hotel by default. Clicking another card or its keyboard-accessible Choose button posts the existing offers and selected IDs to `/api/compare`; no provider search is repeated. Totals, rewards, and award comparisons use the selected pair. Opening details or source links does not change selection. A new search restores the default cheapest pair.
