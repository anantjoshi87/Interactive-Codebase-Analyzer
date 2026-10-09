# Main Engine

The main engine is the Python backend for the Interactive Codebase Analyzer. It is a FastAPI application with a repository-ingestion service layer that turns source code, project configuration, and documentation into typed units suitable for semantic search and a Neo4j code graph.

The ingestion code lives under [`app/services/ingestion`](app/services/ingestion). The intended flow is:

```text
Git repository
    ↓
RepoFetcher
    ↓
RepoParser
    ├─ TreeSitterParser + language extractor → CodeUnit
    ├─ ConfigParser                         → ConfigUnit
    └─ DocumentParser                       → DocumentUnit
    ↓
RepoResolver + optional SCIP index
    ↓
CodeEnricher (LLM summaries + embeddings)
    ↓
GraphSync → Neo4j
```

> The orchestration class is not wired yet. `IngestionPipeline` currently contains only the planned interface, and the `/api/analyze` endpoint is still a placeholder.

## Requirements

- Python 3.12 or newer
- A PostgreSQL-compatible database for the FastAPI/LangGraph checkpointer
- Neo4j for the code graph
- Groq and Mistral credentials for enrichment
- Git access to repositories that should be indexed

Install the locked environment with `uv`:

```bash
uv sync
```

Or install the pinned packages from `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from [`.env.example`](.env.example). The most important settings are:

```dotenv
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
```

`app/core/config.py` also supports model overrides (`GROQ_MODEL`, `MISTRAL_LLM_MODEL`, and `MISTRAL_EMBEDDING_MODEL`) plus optional Tavily, Jina, Redis, Pinecone, and LangSmith settings.

## Running the API

From `main-engine/`:

```bash
uvicorn app.main:app --reload --port 8000
```

The application starts a PostgreSQL connection pool and initializes the LangGraph checkpoint tables during startup. It exposes:

- `GET /health` — returns `503` until the PostgreSQL pool is ready, then reports the service as active.
- `POST /api/analyze` — currently returns a readiness message; it does not run ingestion yet.

Swagger, ReDoc, and the OpenAPI document are available at `/docs`, `/redoc`, and `/openapi.json`.

## Services

### Repository fetching

`RepoFetcher.clone_to_temp(repo_url)` in [`fetcher.py`](app/services/ingestion/fetcher.py) is a context manager that:

1. creates a temporary directory;
2. performs a shallow Git clone (`depth=1`);
3. yields the local checkout path; and
4. removes the temporary directory on exit, including when parsing fails.

It is not currently called by `IngestionPipeline`.

### Repository parsing

`RepoParser.parse_repository(repo_path)` walks a repository using paths relative to the repository root. It skips common generated or vendor directories (`.git`, virtual environments, caches, `node_modules`, `dist`, and similar) and binary/log extensions.

Each file is dispatched in this order:

1. a registered Tree-sitter language;
2. a recognized configuration filename;
3. a supported documentation filename;
4. otherwise, nothing is emitted. `FallbackChunker` exists, but its fallback branch is currently disabled in `RepoParser`.

Parser errors are printed per file and do not abort the complete repository walk.

### Source extraction

`TreeSitterParser` creates a module unit for each parsed source file and extracts structural symbols. It records source spans, qualified names, parent/child scope, imports, module globals, calls, decorators, and class inheritance. Parent units are skeletonized by replacing child bodies with an omission marker, which keeps structural context while reducing duplicated code.

The active `LanguageRegistry` currently registers Python (`.py`) with `PythonExtractor`. The repository also contains Tree-sitter queries and grammar dependencies for JavaScript, TypeScript, HTML, and CSS, but those languages are not registered in the current implementation.

`PythonExtractor` recognizes:

- functions, async functions, classes, and methods;
- regular, aliased, relative, wildcard, and `from ... import ...` imports;
- module-level assignments;
- function calls and method calls, including `self`/`cls` and chained calls.

Common Python built-ins are filtered from extracted call references.

### Configuration extraction

`ConfigParser` emits one `ConfigUnit` for supported project files:

| File | Extracted metadata |
| --- | --- |
| `package.json` | dependencies, devDependencies, scripts |
| `pyproject.toml` | parsed TOML document |
| `requirements.txt` | non-comment package lines |
| `Dockerfile` | raw content |
| `docker-compose.yml` / `.yaml` | parsed YAML |
| `.env.example` | key/value pairs |

`.env` itself is intentionally not enabled in the dispatcher. Invalid JSON returns no unit; the other format parsers currently allow their parsing exceptions to propagate to the repository parser’s per-file error handler.

### Documentation extraction

`DocumentParser` emits a `DocumentUnit` for Markdown, MDX, reStructuredText, AsciiDoc, text files, README files, licenses, changelogs, and contributing guides. It preserves the decoded document content, classifies the document type, and uses the first Markdown heading as its title when available.

### SCIP resolution

`RepoResolver` optionally enriches parsed units with a SCIP index. `ScipIndexReader` reads the protobuf index and normalizes SCIP ranges. The resolver performs two passes:

1. map SCIP definition symbols to the closest parsed unit in the matching file;
2. attach reference occurrences to calls and imports.

Resolved internal calls receive a target unit ID and `RESOLVED` status. References that are present in SCIP but do not map to a parsed unit are marked `EXTERNAL`. If the index file is missing, the resolver logs the condition and returns the units unchanged.

The index path is supplied when constructing `RepoResolver`; there is currently no CLI or API command that generates a SCIP index.

### LLM enrichment and embeddings

`CodeEnricher.enrich_units(units)` processes code, config, and document units asynchronously:

- generates a dense 2–4 sentence technical summary;
- limits concurrent LLM requests with a semaphore;
- uses Groq as the primary summary model and Mistral as the fallback;
- retries failed summary calls with exponential backoff;
- creates Mistral embeddings for enriched semantic text; and
- returns Neo4j-ready dictionaries containing summaries, embeddings, metadata, and resolved relationships.

If both summary models fail, the service falls back to a minimal unit description. Embedding failures are not swallowed and will fail the enrichment call.

### Neo4j graph synchronization

`GraphSync.sync_batch(payloads)` groups enriched payloads by type, upserts nodes with Cypher `UNWIND` batches, and creates relationships for code units:

- `CONTAINS` — AST parent/child structure
- `CALLS` — resolved internal function or method calls
- `IMPORTS` — resolved module/symbol imports
- `INHERITS` — local or imported class inheritance

`Neo4jClient` owns the lazy `Neo4jGraph` connection and provides `init_schema()` for uniqueness constraints and lookup indexes. Schema initialization is available as a method but is not automatically called by the current API startup path.

## Unit model

The service boundary uses Pydantic models from [`app/schemas`](app/schemas):

- `CodeUnit` — a module, class, function, or method plus AST metadata;
- `ConfigUnit` — structured project/deployment configuration;
- `DocumentUnit` — repository documentation; and
- `AnyUnit` — the union consumed by enrichment.

Paths and symbol IDs are repository-relative. Code line and column positions are zero-based to align with SCIP definitions.

## Current integration status

The service components can be used independently, but the complete path still needs orchestration. In particular:

- `IngestionPipeline` is currently `pass`;
- `RepoFetcher`, `RepoParser`, `RepoResolver`, `CodeEnricher`, and `GraphSync` are not connected by an application workflow;
- `/api/analyze` returns a placeholder response;
- the API router in `app/api/endpoints.py` is not included in `app.main`; and
- JavaScript, TypeScript, HTML, and CSS grammar definitions are present but not registered.

For a future end-to-end implementation, the pipeline should clone or receive a repository, parse it, optionally resolve a SCIP index, enrich the units, initialize the Neo4j schema, and sync the resulting payloads in batches.

## Project layout

```text
app/
├── api/                  FastAPI route modules
├── core/                 settings and authentication helpers
├── db/                   PostgreSQL and Neo4j clients
├── models/               SQLAlchemy models
├── schemas/              ingestion unit and metadata models
└── services/ingestion/   repository analysis pipeline
    ├── extraction/       Tree-sitter, config, and document parsing
    ├── grammars/         language registry and query definitions
    ├── graph/            LLM enrichment and Neo4j synchronization
    └── resolution/       SCIP reading and symbol binding
```
