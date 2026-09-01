# Repository structure

## Phase 0 filesystem

```text
razorshield/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── risk/
│   │   ├── schemas/
│   │   └── services/
│   ├── alembic/
│   │   └── versions/
│   ├── scripts/
│   └── tests/
├── frontend/
│   ├── public/
│   └── src/
├── data/
├── artifacts/
├── docs/
├── .gitignore
└── README.md
```

Empty directories contain `.gitkeep` only. This is intentional: Phase 0 defines
boundaries but does not create pretend executables or configuration that has not
yet been tested.

## Planned completed structure

```text
razorshield/
├── backend/
│   ├── app/
│   │   ├── api/             # versioned HTTP routes and dependencies
│   │   ├── core/            # settings, logging, errors, security, request IDs
│   │   ├── db/              # engine, sessions, unit of work
│   │   ├── models/          # SQLAlchemy mappings
│   │   ├── repositories/    # persistence queries and commands
│   │   ├── schemas/         # Pydantic API contracts
│   │   ├── services/        # scoring/case/metrics use cases
│   │   ├── risk/            # features, graph, rules, ML, policy, evaluation
│   │   └── main.py          # application factory entry point
│   ├── alembic/             # migration environment and revisions
│   ├── scripts/             # generate, train, evaluate, and seed entry points
│   ├── tests/               # unit, API, persistence, ML/leakage tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/                 # pages, components, typed API, state and styles
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── data/                    # manifests/small fixtures; bulk generation ignored
├── artifacts/               # metadata/reports; model binaries ignored by default
├── docs/
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

Generated source data, split manifests, models, policies, and reports will have
explicit version identifiers. Frontend data access will be centralized rather
than embedded in individual visual components.

