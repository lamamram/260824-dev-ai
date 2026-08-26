# AGENTS.md

Formation project: FastAPI "API Catalogue" (French) + SQLAlchemy 2.0 ORM + PostgreSQL. No tests, no linter, no git.

## Stack

- FastAPI, SQLAlchemy (DeclarativeBase style, `Mapped`/`mapped_column`), Pydantic v2, psycopg2, bcrypt, python-dotenv
- Entry point: `main.py` (`app`), run with `uvicorn main:app --reload`
- Install: `pip install -r requirements.txt`

## Structure (unusual split)

- `database.py` — **both** the engine/session config (`get_db`, `SessionLocal`) **and** all ORM models (`Utilisateur`, `Article`, `Tag`, `ProfilUtilisateur`). There is no separate `models.py`.
- `routers/` — FastAPI endpoints; `cruds/` — isolated SQL access (keep new queries there, not in routers); `schemas/` — Pydantic request/response models; `dependencies.py` — shared query-param dependency; `exceptions.py` — `RessourceNonTrouveException` (globally handled in `main.py` → 404 JSON, raise it instead of `HTTPException(404)`)
- tests/ — pytest tests (one per router, one per CRUD, one for auth)

## Database setup (required order)

1. `docker compose up -d` — starts `postgres:17` (5432, user `postgres`/`roottoor`) and pgAdmin (http://localhost:15080, `me@example.com`/`roottoor`)
2. Create the database `formation` (pgAdmin or `psql`) — it is not created automatically
3. `python init_db.py` — idempotent `create_all` + seed data (users `admin`/`gars`, articles, profiles, tags)
   - `python init_db.py --force-delete` **drops all tables then reseeds** — destructive, only run deliberately
- Connection comes from `.env` (`PG_USER`, `PG_PASS`, `PG_HOST`, `PG_PORT`, `PG_DB`) loaded via `load_dotenv()` in `database.py`; do not hardcode credentials

## install packets (unusal)

1. verify if packets are installed else then `pip install --break-system-packages -r requirements.txt` to create it globally without venv because the sandbox is has both windows and linux filesystem and the venv is not working properly
2. finally run `uvicorn main:app --reload` to start the server

## Conventions

- Code, identifiers, comments and docstrings are all in **French** — follow this style
- `Article.auteur` is `lazy="joined"` and `Article.tags` is `lazy="selectin"` (database.py), so relationships load eagerly by default when returning an `Article`
- `Auteur` = `Utilisateur` model: routers/cruds called `auteurs` map to the `utilisateurs` table
