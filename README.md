# FareForge AI — Hackathon 03 Student Kit

FareForge won **1st place in the Travel Agent track** and **3rd place overall** at the **Microsoft AI Agent Hackathon 2026**.

## Team plans

- [Johnny: backend and integration](JOHNNY_PLAN.md)
- [Nguyen: frontend and live search](NGUYEN_PLAN.md)

The starter app is included in this repository. Both teammates can start from their implementation tasks and skip the initial copy step in the plans.

A transferable, offline-first starter for a travel-price-and-rewards hackathon. Unzip, follow `00_START_HERE.md`, and modify the code as your team builds.

## Folder overview

| Folder / file | Purpose |
|---|---|
| `00_START_HERE.md` | 5-minute setup and reading order |
| `docs/` | Student challenge, schedule, rubric, architecture, integrations, portability and QA |
| `starter_app/server.py` | Local HTTP server; search API (`POST /api/search`) |
| `starter_app/travel/` | Comparison logic and optional live provider adapter |
| `starter_app/web/` | Responsive interactive HTML/CSS/JS app |
| `starter_app/data/` | **Fictional test fixtures** — not bookable offers |
| `starter_app/tests/` | Unit tests for pricing, validation, demo and live parsing |
| `skills/travel-deal-auditor/` | Transferable Agent Skill with `SKILL.md` |
| `prompts/` | Reusable prompts for AI coding assistants |
| `evaluation/` | Judges' scorecard, price verification template and sample scenario inputs |
| `submission_templates/` | Team delivery checklist and evidence template |
| `scripts/` | Automated portability checks; launch helpers |

## Technical choices
- Python 3.10+ **standard library only** for the runnable starter.
- Native HTML/CSS/JS (no CDN or package manager required).
- Demo fixture adapter + optional authorized SerpApi lookup (`SERPAPI_KEY`).
- Testable logic independent from the UI.
- No actual payments, point transfers, credit card applications or stored traveler credentials.

## Running the local server
```bash
cd starter_app
python server.py
# Open http://127.0.0.1:8000
```
On Windows use `py server.py` if `python` is unavailable. Change port with `PORT=8080` (or `.env`).

If Windows blocks port 8000, run this from `starter_app/`:

```powershell
$env:PORT = "8080"
python server.py
# Open http://127.0.0.1:8080
```

## Optional live search
The live adapter is **not an official Google API** and can incur API fees/quotas. Create `starter_app/.env` based on `.env.example`, insert your own authorized `SERPAPI_KEY` and select **Live** in the UI. Never share `.env`. The starter combines separate outbound and return one-way searches and retrieves hotel search listings. Those numbers are **not checkout-verified round-trip prices** and may omit taxes/fees and baggage. Read `docs/PROVIDER_INTEGRATION.md` first.

## Test
```bash
cd starter_app
python -m unittest discover -s tests -v
```
From the project root: `python scripts/portability_check.py`.

## Evidence standard
Source URL, exact itinerary/room conditions, traveler count, full fee breakdown, capture time (UTC), currency and checkout confirmation status. If unavailable, show **unknown** instead of assuming zero.

## Sources / references
- [Agent Skills specification](https://agentskills.io/specification)
- [SerpApi Google Flights documentation](https://serpapi.com/google-flights-api)
- [SerpApi Google Hotels documentation](https://serpapi.com/google-hotels-api)

These external APIs change; verify current terms and schemas before the event.
