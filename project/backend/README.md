# Financial Milestones — backend

Turns a Sherpas financial plan into personalised milestones a household can
work through, keeps them in step with the plan and measures the progress.

FastAPI · SQLAlchemy · Alembic · SQLite · MCP · provider-agnostic AI.

---

## What it does

1. Reads the financial plan of a case (Sherpas MCP, or the offline case files).
2. Normalises it into a bounded **digest** and asks an AI provider for
   personalised milestones with their tasks, priorities, categories and dates.
3. Validates every figure the AI quotes against the plan, and stores the
   result.
4. Lets the household work on the milestones: complete tasks, close
   milestones, declare financial values, register reviews.
5. Keeps the milestones in step with the plan through a **synchronisation**
   that never loses the progress of the client.

## Requirements

* Python 3.11 or later (3.12 recommended)
* `uv` (or `pip`) for the dependencies

## Getting started

```bash
cd project/backend
make install                 # creates .venv and installs the dependencies
cp .env.example .env         # then fill in the values below
make migrate                 # creates the SQLite schema
make dev                     # http://127.0.0.1:8001/docs
```

### Configuration

| Variable | Meaning | Default |
|---|---|---|
| `DATABASE_URL` | SQLite file | `sqlite:///./data/app.db` |
| `CASE_SOURCE` | `auto`, `mcp` or `local` | `auto` |
| `CASES_DIR` | The offline case files | `../../cases` |
| `MCP_URL` / `MCP_TOKEN` | The Sherpas MCP | — |
| `AI_PROVIDER` | `openai_compatible` or `fake` | `openai_compatible` |
| `AI_BASE_URL` / `TEAM_KEY` | The AI proxy | `https://llm-hackathon.sherpaswealth.com/v1` |
| `AI_MODEL` | The model used to generate the milestones | `gpt-5-mini` |
| `AI_COPY_MODEL` | The model that writes the copy of the pillars | `gemini-3.5-flash-lite` |
| `MENTOR_MODEL` | The model that answers the mentor | `gemini-3.5-flash-lite` |
| `DIGEST_MAX_CHARS` | Context budget of one generation | `60000` |
| `SYNC_MIN_INTERVAL_MINUTES` | Minimum gap between automatic syncs | `1440` |
| `ALLOWED_CASE_IDS` | Comma separated allowlist | empty (denies everything) |
| `CORS_ORIGINS` | Comma separated origins | `http://localhost:5173` |

`AI_API_KEY` is the name of the variable that holds the team key in this
backend; copy it from `TEAM_KEY` in the `.env`:

```
AI_API_KEY=sk-...
```

> **The MCP token lasts 72 hours.** When it expires the MCP answers `401`;
> with `CASE_SOURCE=auto` the backend falls back to the offline case files in
> `cases/` (the very same payloads the MCP serves) and marks the response as
> `stale`. It never invents financial data.

## The pillars

Four views of the same plan, on top of the milestones:

- **The decision laboratory** — the steps of the plan (`top_moves`) and what
  the plan says they achieve together (`combined_moves`). The score it shows
  comes from the plan, never from a table of hard coded numbers.
- **The proactive mentor** — one nudge and a few jargon pills, written by the
  model from the plan.
- **The couple mode** — the portrait of each partner, the bridge towards a
  joint decision and the wall of high fives. The high fives are the only
  state the household writes, and they live in the database.
- **The financial story** — the four scenes that open the application.

Their words are written by the model with `AI_COPY_MODEL` (a model without
reasoning, so the answer never runs out of tokens). When the model is not
reachable the pillars still answer with the figures of the plan and report
`"generated": false`.

The interactive console that exercises all of them lives at `/dev/console` and
is only registered while developing.

## Architecture

```
app/
  api/          HTTP layer: routers, dependencies, the error envelope
  services/     use cases: generation, synchronisation, tasks, progress…
  domain/       pure rules: progress, completion, recurrence, reconciliation
  models/       SQLAlchemy ORM
  repositories/ queries only
  integration/  adapters: mcp/ (case data) and ai/ (generation)
  notifications/ the deterministic notice generator and its scheduler
```

The layers point inwards: `app/domain` imports nothing from the
infrastructure and `app/api` never touches the database directly. The rules
are enforced by `tests/unit/test_architecture.py`.

## The API

Base path `/api`. The full documentation is served at `/docs`.

> **Building a client? Start with [`docs/api-contract.md`](docs/api-contract.md).**
> It is the complete contract: every endpoint with its parameters and its
> answers, the rules of the domain, the real responses captured from a running
> instance, the TypeScript types to copy and a step by step integration recipe.
> The machine readable contract is [`openapi.json`](openapi.json).

| Method | Path | What it does |
|---|---|---|
| `GET` | `/api/cases/{case_id}/milestones` | The milestones of a case |
| `GET` | `/api/cases/{case_id}/milestones/{id}` | One milestone |
| `PATCH` | `/api/cases/{case_id}/milestones/{id}/status` | Change the status |
| `POST` | `/api/cases/{case_id}/milestones/{id}/complete` | Confirm the completion |
| `GET` | `/api/cases/{case_id}/milestones/{id}/progress` | The operational progress |
| `POST` | `/api/cases/{case_id}/milestones/generate` | Generate the milestones |
| `GET` | `/api/cases/{case_id}/milestones/{id}/tasks` | The tasks |
| `POST` | `/api/cases/{case_id}/milestones/{id}/tasks` | Add a task |
| `PATCH` | `/api/cases/{case_id}/milestones/{id}/tasks/{task_id}` | Complete or edit a task |
| `DELETE` | `/api/cases/{case_id}/milestones/{id}/tasks/{task_id}` | Remove a task |
| `POST` | `/api/cases/{case_id}/milestones/{id}/observations` | Declare a financial value |
| `GET` | `/api/cases/{case_id}/milestones/{id}/observations` | The values and their origin |
| `GET` | `/api/cases/{case_id}/milestones/{id}/financial-progress` | The financial progress |
| `GET` | `/api/cases/{case_id}/checkins` | The reviews |
| `GET` | `/api/cases/{case_id}/milestones/{id}/checkins` | The schedule of a milestone |
| `POST` | `/api/cases/{case_id}/milestones/{id}/checkins/complete` | Register a review |
| `GET` | `/api/cases/{case_id}/notifications` | The internal notices |
| `POST` | `/api/cases/{case_id}/notifications/{id}/read` | Mark a notice as read |
| `POST` | `/api/cases/{case_id}/notifications/read-all` | Mark every notice as read |
| `GET` | `/api/cases/{case_id}/sync` | The synchronisation state |
| `POST` | `/api/cases/{case_id}/sync` | Synchronise with the plan |
| `GET` | `/api/cases/{case_id}/progress` | The aggregated progress |
| `GET` | `/api/cases` | The households, with the voice of each one |
| `POST` | `/api/voice/ask` | The mentor, in writing and with a voice |
| `WS` | `/api/voice/ws/{case_id}` | The live voice of the mentor |
| `GET`/`POST` | `/api/cases/{case_id}/simulator` | The decision laboratory |
| `GET` | `/api/cases/{case_id}/mentor/insights` | The proactive mentor and the jargon pills |
| `GET` | `/api/cases/{case_id}/couple` | The couple mode |
| `POST` | `/api/cases/{case_id}/couple/high-five` | A high five between the two |
| `GET` | `/api/cases/{case_id}/story` | The financial story |
| `GET` | `/api/categories`, `/api/sections`, `/api/health`, `/api/environment` | The catalogues |
| `GET` | `/dev/console` | The interactive console, **only while developing** |

### The milestone contract

The listing keeps the shape the React client already consumes and adds the
new fields after it:

```jsonc
{
  "id": "ms_9f2c1a7b4d5e6f70",
  "title": "Understand your credit card debt",
  "why": "Credit card debt at 18% interest is expensive to carry.",
  "action": "Read the debt section and ask your mentor any question.",
  "section": "debt",
  "status": "in_progress",
  "checkin": "Dec 14",

  "case_id": "timothy-melanie-weah",
  "category": "Debt",
  "type": "educational",
  "priority": "high",
  "tasks": [ ... ],
  "task_progress": 50,
  "financial_progress": null,
  "due_date": null,
  "checkin_pending": false,
  "checkin_date": "2026-12-14",
  "overdue": false,
  "source": [ ... ],
  "created_at": "2026-11-16T10:00:00Z",
  "updated_at": "2026-11-16T10:00:00Z",
  "completed_at": null,
  "last_reviewed_at": null
}
```

### Errors

Every error uses the same envelope:

```json
{ "error": { "code": "MCP_UNAVAILABLE", "message": "...", "details": {} } }
```

`MCP_UNAVAILABLE`, `MCP_AUTH_ERROR`, `INVALID_CASE_ID`, `CASE_NOT_ALLOWED`,
`FINANCIAL_PLAN_NOT_FOUND`, `AI_PROVIDER_UNAVAILABLE`, `AI_INVALID_RESPONSE`,
`AI_RESPONSE_TOO_LARGE`, `DATABASE_ERROR`, `MILESTONE_NOT_FOUND`,
`TASK_NOT_FOUND`, `INVALID_STATUS_TRANSITION`, `INVALID_FINANCIAL_OBSERVATION`,
`SYNC_CONFLICT`, `VALIDATION_ERROR`.

When the MCP or the AI is down and the milestones are already stored, they are
still returned with `"meta": {"stale": true, "stale_reason": "..."}`.

## The rules that matter

* **The client owns the status.** The AI and the synchronisation never change
  it, and only the allowed transitions are accepted.
* **Educational milestones close themselves** when their required tasks are
  done. **Financial milestones always need an explicit confirmation.**
* **`task_progress`** is the share of the required tasks that are done, or
  `null` when the milestone has no required tasks.
* **`financial_progress`** is `null` when the milestone has no metric, when
  the figures cannot be compared or when the MCP and the client disagree. A
  percentage is never invented.
* **The two sources of financial data are kept apart.** A conflict is
  reported, not resolved silently.
* **A check-in is a review, not a deadline.** `checkin` and `due_date` are
  independent. The reviews after the first one follow a deterministic monthly
  rule and never need an AI call.
* **A synchronisation never deletes a milestone** and never loses a completed
  task, even when the AI rewrites it.

## Security

The MVP has no authentication. That is a prototyping decision, not a
production answer.

* `ALLOWED_CASE_IDS` is a guard rail: an empty list denies every request
  (fail closed) and a case outside the list is refused **before** any call to
  the MCP or the AI.
* The MCP token and the team key never reach a log or a response.
* The server binds to `127.0.0.1` and the CORS origins are explicit.

**Do not expose this service publicly.** The architecture leaves room for a
real authentication layer: the allowlist is checked in one place
(`app/api/deps.py: authorize_case`), which is where a token check would go.

## Tests

```bash
make test        # the whole suite
make coverage    # with coverage
```

The suite never touches the network: the MCP is replaced by the offline case
files and the AI by a deterministic fake provider.

## Migrations

```bash
make migrate                 # alembic upgrade head
make revision m="add something"
```

`alembic check` must report no drift between the models and the migrations;
`tests/integration/test_migrations.py` enforces it.

## Documentation

| Artefact | What it is | How to refresh it |
|---|---|---|
| [`docs/api-contract.md`](docs/api-contract.md) | The guide for anyone building a client | by hand |
| [`docs/milestones.types.ts`](docs/milestones.types.ts) | The TypeScript types, ready to copy | by hand |
| [`docs/examples/`](docs/examples/) | Real answers captured from a running instance | `make examples` |
| [`openapi.json`](openapi.json) | The machine readable contract | `make openapi` |

`tests/integration/test_openapi_spec.py` fails when the specification, the
examples or the guide drift away from the application, so the documentation
cannot go stale without anybody noticing.
