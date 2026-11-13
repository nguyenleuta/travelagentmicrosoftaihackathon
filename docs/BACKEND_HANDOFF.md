# Backend handoff for Nguyen

## Portal versus transfer quotes

Expanded routes: Chase to Southwest, United, JetBlue, Aeroplan, British Airways and Flying Blue; Amex to Delta, JetBlue, Aeroplan, British Airways, Flying Blue, plus Hilton. US base rates only. Amex to JetBlue uses 250:200 blocks; other airline routes use 1,000:1,000. The search/selection response now includes `transfer_rules` so the frontend renders the same supported route catalog as the calculator. No direct Chase-to-Delta, Amex-to-United/Southwest, or AA/Frontier route is invented.

User-entered comparisons accumulate in a table for the current selection; submitting the same route/offer replaces its prior result. Each quote must have its own program-specific award and portal inputs. Changing selected offers or running a new search clears the table. This is a comparison of alternatives, not a combined-wallet purchase.

Amex US airline transfers (Delta and JetBlue) automatically include the excise offset fee of $0.0006 per bank point transferred, capped at $99. The manual fee input is for additional fees only. No transfer means no excise fee. Official fee source: https://www.americanexpress.com/content/dam/amex/us/rewards/membership-rewards/mr-terms-conditions-november-2026.pdf . Aeroplan US ratio/increments: https://www.aircanada.com/ca/en/ado/home/aeroplan/your-aeroplan/conversion-programs.html . Other Amex routes: https://global.americanexpress.com/rewards/transfer . Chase partner list/increments: https://www.chase.com/personal/credit-cards/education/basics/how-to-transfer-chase-ultimate-rewards-points . Chase ratio corroboration: https://thepointsguy.com/loyalty-programs/chase-ultimate-rewards-transfer-partners . Rules checked November 13, 2026; reconfirm account-specific terms before transferring.

The comparison panel now has an expandable quote calculator. `/api/rewards-quote` compares user-entered bank portal and partner award quotes using Chase → Southwest (1:1) or Amex → Hilton (1:2), with minimum 1,000-bank-point blocks. No quote is derived from a cash fare or subjective valuation. Chase issuer source: https://www.chase.com/personal/credit-cards/education/basics/how-to-transfer-chase-ultimate-rewards-points . Southwest ratio corroboration: https://thepointsguy.com/loyalty-programs/transfer-chase-ultimate-rewards-southwest . Rules checked November 13, 2026. These are maintained base rules, not a live account-specific feed.

The form takes the selected offer ID, portal points, award points, portal and award cash fees, transfer fees, existing partner balance and its personal valuation. Bank balance and valuation come from the last search. It shows bank points spent, cash paid, economic costs, balance shortfalls, transfer rounding and leftovers. Existing partner points are valued separately and are not treated as free. Fee fields require explicit input; blank does not mean zero. No promotional bonus is assumed.

Quotes remain user-entered and unverified even when the user checks matching-trip and eligibility confirmations. A different selection or search clears the calculator and its result to avoid attaching an old quote to a new offer. The form is independent of the main automatic cash/scenario summary. It performs no bookings or point transfers.

Automatic prices still require authorized bank portal and airline/hotel award data sources. The existing live cash adapter does not supply those quotes. Future connectors can populate the same calculator inputs with precise matching itinerary/room evidence.

## Chase and Amex wallet placeholders

Search and compare accept `chase_balance`, `amex_balance` (nonnegative integers), `chase_value_cents`, `amex_value_cents` (0.1–10). Defaults: zero balances and example valuations of 1 cent. These values are separate from the existing generic award scenario balance.

Offers expose `points_payment.cash_equivalents`: cash USD × 100 / subjective cents per point, rounded up. These are value equivalents, never portal redemption rates or award booking prices. Incomplete cash prices produce incomplete value estimates. The UI displays this distinction on each card and in the selected-offer comparison. Each balance is evaluated separately, and card coverage does not claim enough balance for the whole trip.

`points_payment.award_points` requires an actual normalized award field. No award is inferred from carrier name, hotel name, or cash price. `award_program` must identify the loyalty currency explicitly.

First supported transfer scenario: Amex Membership Rewards to Hilton Honors, US base ratio 1,000:2,000, rounded to 1,000-bank-point increments; no promotional bonus. Official reference: https://global.americanexpress.com/rewards/transfer?partner=5629f189e4b0b3d3bd79cc4f (checked November 13, 2026). Account eligibility and fees still require confirmation. Rule data lives in `travel/rewards.py`. No Chase routes or AA/Frontier transfer routes are assumed. Unsupported routes show unavailable rather than 1:1.

For actual transfer display, supply `award_program="Hilton Honors"`, `award_points_total` and `award_taxes_usd` for a hotel quote. Fees/availability remain subject to existing evidence rules. Synthetic Demo Hotel Points are a different currency and do not use real Hilton rules. Existing provider files were not changed.

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
