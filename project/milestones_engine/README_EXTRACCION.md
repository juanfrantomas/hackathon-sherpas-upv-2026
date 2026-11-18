# Motor de hitos (Milestones) — extraído de `origin/main` (commit 5f60933)

Origen: PR #1 `juanfran/custom-milestones` ("Build Financial Milestones backend with AI-powered planning").
Paquete Python `app.*` (FastAPI + SQLAlchemy + Pydantic v2). Python ≥ 3.11 (`StrEnum`, `datetime.UTC`).

## Flujo de creación de hitos

```
MCP / casos locales ──> normalizer.normalize_plan() ──> PlanDigest (resumen acotado del plan)
                                                           │
                       prompts.build_system/user_prompt() ◄┘
                                                           │
            AIService.generate_milestones()  (LLM con JSON schema estricto)
              ├─ GenerationResult.model_validate()      (schemas/generation.py)
              ├─ _apply_rules(): descarta hitos con citas/anchors/cifras inventadas
              ├─ _deduplicate(): fusiona hitos repetidos
              └─ _repair(): 1 reintento explicando al LLM qué falló
                                                           │
            generation_service.generate_milestones()       ▼
              ├─ stable_key_for()  -> "categoria:kind:valor" (p.ej. "debt:concern:O2")
              ├─ reconcile_milestones()  (domain/reconciliation.py)
              │     1) stable_key exacta  2) mismo anchor  3) similitud ponderada
              ├─ nuevos  -> _create_milestone() + check-in inicial + observación MCP
              ├─ emparejados -> _apply_to_existing() (NO toca estado/tareas completadas)
              └─ huérfanos -> is_stale = True (nunca se borran)
```

Disparadores: `GET /api/cases/{id}/milestones` (autogenera en el primer acceso),
`POST /api/cases/{id}/milestones/generate` y `sync_service.sync_case()` (solo si cambia el fingerprint del plan).

## Archivos clave (núcleo)

| Archivo | Rol |
|---|---|
| `app/services/generation_service.py` | Orquestación: IA → reconciliación → persistencia |
| `app/integration/ai/ai_service.py` | Llamada al LLM, validación, reglas anti-alucinación, dedupe, repair |
| `app/integration/ai/prompts.py` | System/user prompt (taxonomía, reglas del plan, formato) |
| `app/schemas/generation.py` | Contrato Pydantic + JSON schema enviado al LLM |
| `app/integration/mcp/normalizer.py` + `digest.py` | Plan crudo → `PlanDigest` (concerns O1.., tensions T1.., métricas) |
| `app/domain/reconciliation.py` | Emparejado estable entre generaciones (hitos y tareas) |
| `app/domain/enums.py` | Categorías, secciones, estados, transiciones válidas |
| `app/domain/progress.py`, `completion.py` | % de tareas, % financiero, autocompletado |
| `app/models/milestone.py`, `task.py`, ... | Tablas SQLAlchemy |
| `app/api/routers/milestones.py` | Endpoints REST |

## Dependencias de soporte incluidas
config, db/session, errors, logging, repositories, task/checkin/notification/case services,
proveedor OpenAI-compatible + `FakeProvider` (para demo sin API key), cliente MCP y fuente de casos.
`app/api/deps.py` arrastra mentor/tts/voice_profiles (solo cableado de la API; no intervienen en la generación).

**No incluido** (y no necesario): alembic/migraciones, resto de routers, frontend React.
Para crear las tablas sin alembic: `Base.metadata.create_all(engine)` (ver `app/models/base.py`).

## Dependencias pip (pyproject.toml)
fastapi, uvicorn, pydantic>=2.8, pydantic-settings, sqlalchemy>=2.0.30, httpx, mcp>=1.2, openai>=1.40, python-dotenv
(+ pytest/pytest-asyncio para `tests/unit`). Variables de entorno en `.env.example`.

## Ejemplos
- `docs/examples/milestones-generate.json` — respuesta real de la generación.
- `docs/milestones.types.ts` — tipos TypeScript del contrato para el frontend.
