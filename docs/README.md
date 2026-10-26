# Assignment Submission Portal — Source Code & CI (GitHub Actions)

Application source code for the **Assignment Group Portal** plus the **Continuous Integration** pipeline that builds its container images, pushes them to Amazon ECR, and updates the image tags in the separate Kubernetes manifest repository.

> **Repository role:** CI (source code + image build)
> **Companion repository (CD):** [`YashwanthGowdaM/assignment-portal-k8s`](https://github.com/YashwanthGowdaM/assignment-portal-k8s) — Kubernetes manifests deployed by ArgoCD

---

## Table of Contents

1. [What the Application Does](#1-what-the-application-does)
2. [Tech Stack](#2-tech-stack)
3. [Repository Structure](#3-repository-structure)
4. [Application Architecture](#4-application-architecture)
5. [Container Images](#5-container-images)
6. [CI Pipeline (GitHub Actions)](#6-ci-pipeline-github-actions)
7. [AWS Authentication (OIDC)](#7-aws-authentication-oidc)
8. [Configuration & Environment Variables](#8-configuration--environment-variables)
9. [Database, Migrations & Seed Data](#9-database-migrations--seed-data)
10. [Caching (Redis)](#10-caching-redis)
11. [Monitoring Endpoints](#11-monitoring-endpoints)
12. [Tests](#12-tests)
13. [How CI Hands Over to CD](#13-how-ci-hands-over-to-cd)
14. [Other Files in This Repository](#14-other-files-in-this-repository)
15. [Observations From the Code](#15-observations-from-the-code)

---

## 1. What the Application Does

A web portal with two roles, enforced by the `@admin_required` / `@student_required` decorators:

| Role | Capabilities (from `routes/admin.py` and `routes/student.py`) |
|---|---|
| **Admin** | Dashboard, statistics, create/edit/delete/close/reopen assignments, list students, list groups, list submissions, review a submission (approve/reject with feedback) |
| **Student** | Register/login, dashboard, browse assignments (search, status/type filter, sort, pagination), join/leave a group, submit repo/docs links, view own submissions |
| **Common** | Login, logout, register, forgot/reset password, profile, `GET /health` |

Behaviour taken from the code:

- Creating an **INDIVIDUAL** assignment automatically creates one group per existing student.
- Every admin/group/submission action writes an `AuditLog` entry.
- Allowed group sizes are `[1, 2, 3, 4, 5]` (`config.py`).

---

## 2. Tech Stack

| Layer | Technology (source: `requirements.txt`, Dockerfiles, `package.json`) |
|---|---|
| Backend | Flask 3.0.3, Gunicorn 22.0.0, Python 3.12 (image `python:3.12-slim`) |
| ORM / migrations | Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.30, Flask-Migrate 4.0.7 (Alembic) |
| Auth / forms | Flask-Login 0.6.3, Flask-WTF 1.2.1 (CSRF), WTForms 3.1.2 |
| Database driver | psycopg2-binary 2.9.10 (PostgreSQL) |
| Cache | redis 5.0.4 client |
| Metrics | prometheus-flask-exporter 0.23.2 |
| Tests | pytest 8.2.0, pytest-flask 1.3.0 |
| Web server (frontend image) | `nginx:1.27-alpine` |
| CI | GitHub Actions, Amazon ECR, AWS OIDC |
| React/Vite sources | `src/` + `package.json` (React 19, Vite 6, TypeScript, Tailwind 4) — see [Observations](#15-observations-from-the-code) |

---

## 3. Repository Structure

```text
.
├── .github/workflows/ocid_deployment.yml   # CI pipeline (build → push to ECR → update manifest repo)
├── .essential/                             # AWS notes: IAM role/policies, ECS setup guide, docker-install.sh
├── backend/
│   ├── Dockerfile                          # Backend image (Flask + Gunicorn)
│   ├── app/
│   │   ├── __init__.py                     # create_app(): config, Prometheus, extensions, blueprints
│   │   ├── extensions.py                   # db, migrate, login_manager, csrf, Redis init (+ fallback)
│   │   ├── forms/                          # assignment_forms, auth_forms, submission_forms
│   │   ├── models/                         # user, assignment, group (+GroupMember), submission, audit_log
│   │   ├── routes/                         # main, auth, admin, student blueprints
│   │   ├── services/                       # assignment, auth, cache, stats, submission services
│   │   └── utilities/                      # decorators, errors, helpers
│   ├── config.py                           # Development / Testing / Production configs
│   ├── requirements.txt
│   └── run.py                              # app = create_app(FLASK_ENV)
├── database/migrations/                    # Alembic env + versions/d69f3b0037d6_initial_schema.py
├── frontend/
│   ├── Dockerfile                          # Nginx image (static files + nginx.conf)
│   ├── nginx.conf
│   ├── static/ (css, js)
│   └── templates/ (admin, auth, errors, student, base.html)   # Jinja2 templates
├── src/                                    # React + TypeScript (Vite) components
├── tests/                                  # pytest suites
├── docs/README.md                          # Pre-existing project documentation (see §15)
├── media/                                  # Screenshots + project-design.png
├── alembic.ini
├── entrypoint.sh                           # migrate → seed → gunicorn
├── seed.py                                 # Demo data
├── .env.example
├── .dockerignore / .gitignore
├── metadata.json, package.json, tsconfig.json, vite.config.ts, index.html
```

---

## 4. Application Architecture

Layered design (routes → services → models), as implemented in `backend/app/`:

```text
Browser
   │
   ▼
Nginx container (frontend image, port 80)
   ├── /static/*  → served directly from /usr/share/nginx/html/static/  (expires 30d)
   └── /          → proxy_pass http://backend-service:5000
                         │
                         ▼
               Flask + Gunicorn (backend image, port 5000)
                  Blueprints: main · auth · admin · student
                         │
              ┌──────────┴───────────┐
              ▼                      ▼
        PostgreSQL               Redis (cache)
   (SQLAlchemy / Alembic)    (CacheService, key prefix "portal:")
```

- Flask loads Jinja templates and static files from **`/frontend/templates`** and **`/frontend/static`** inside the backend container (`create_app`). The backend image therefore copies the whole `frontend/` folder to `/frontend`.
- The Nginx image contains only `static/` and `nginx.conf`.

### Data model (`backend/app/models`)

| Table | Purpose |
|---|---|
| `users` | Admins and students (role, student_id, bio, password hash) |
| `assignments` | Type (INDIVIDUAL/GROUP), max group size, max groups, status, due date |
| `groups` | Groups per assignment (group number, capacity/full flag, status) |
| `group_members` | Student ↔ group membership |
| `submissions` | Repo URL, docs URL, remarks, status, feedback |
| `audit_logs` | Action trail |

---

## 5. Container Images

Two images are built from this repository.

| Image | Dockerfile | Build context | Base | Port | Startup |
|---|---|---|---|---|---|
| `assignment-portal-backend` | `backend/Dockerfile` | repository root (`.`) | `public.ecr.aws/docker/library/python:3.12-slim` | 5000 | `ENTRYPOINT /entrypoint.sh` |
| `assignment-portal-frontend` | `frontend/Dockerfile` | `./frontend` | `nginx:1.27-alpine` | 80 | `nginx -g "daemon off;"` |

**Backend image contents:** `gcc` + `libpq-dev`, Python requirements, `backend/` → `/app/`, `alembic.ini`, `database/`, `seed.py`, `entrypoint.sh` → `/entrypoint.sh`, and `frontend/` → `/frontend/`.

**`entrypoint.sh` sequence:**

1. `flask db upgrade`
2. `python /app/seed.py`
3. `gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 run:app`

---

## 6. CI Pipeline (GitHub Actions)

File: `.github/workflows/ocid_deployment.yml` — workflow name **"Build Images & Update K8s Manifests"**.

### Triggers

| Trigger | Detail |
|---|---|
| `push` | Branch **`K8s-deployment`**, only when changes touch: `backend/**`, `frontend/**`, `database/**`, `migrations/**`, `requirements.txt`, `alembic.ini`, `entrypoint.sh`, `seed.py` |
| `workflow_dispatch` | Manual run |

### Permissions & environment

| Item | Value |
|---|---|
| `permissions` | `id-token: write`, `contents: read` |
| `AWS_REGION` | `us-east-1` |
| `BACKEND_ECR_REPOSITORY` | `assignment-portal-backend` |
| `FRONTEND_ECR_REPOSITORY` | `assignment-portal-frontend` |
| `MANIFEST_REPO` | `YashwanthGowdaM/assignment-portal-k8s` |
| `MANIFEST_BRANCH` | `main` |
| Runner | `ubuntu-latest` (single job: `build-and-deploy`) |

### Steps (in order)

| # | Step | What it does |
|---|---|---|
| 1 | Checkout Source Repository | `actions/checkout@v4` |
| 2 | Configure AWS Credentials | `aws-actions/configure-aws-credentials@v6`, assumes `secrets.AWS_ROLE_ARN_SNQ` via OIDC |
| 3 | Login to Amazon ECR | `aws-actions/amazon-ecr-login@v2` |
| 4–6 | Backend build / tag / push | `docker build -f backend/Dockerfile .` → tag `<registry>/assignment-portal-backend:${{ github.sha }}` → push |
| 7–9 | Frontend build / tag / push | `docker build -f frontend/Dockerfile ./frontend` → tag `<registry>/assignment-portal-frontend:${{ github.sha }}` → push |
| 10 | Clone Manifest Repository | `git clone` of the manifest repo using `secrets.K8S_REPO_PAT` |
| 11 | Update Backend Deployment Image | `sed` rewrites the `image:` line in `manifest_files/backend/deployment.yaml` |
| 12 | Update Frontend Deployment Image | `sed` rewrites the `image:` line in `manifest_files/frontend/deployment.yaml` |
| 13 | Commit Manifest Changes | Commits as `github-actions[bot]` with message `Update images to <sha>`; exits without committing if nothing changed |
| 14 | Push Manifest Changes | `git push origin main` on the manifest repo |

### Image tagging

- Both images are tagged with the **full commit SHA** (`github.sha`).
- The workflow does not push a `latest` tag.

### Required GitHub secrets

| Secret | Used for |
|---|---|
| `AWS_ROLE_ARN_SNQ` | IAM role assumed through GitHub OIDC |
| `K8S_REPO_PAT` | Personal access token to clone/push the manifest repository |

---

## 7. AWS Authentication (OIDC)

The workflow uses **GitHub OIDC** (no static AWS keys). `.essential/IamRole&Policies.txt` documents:

- Identity provider: `token.actions.githubusercontent.com`
- Role: `GitHub_Role_New_Created` (its ARN is stored in the `AWS_ROLE_ARN_SNQ` secret)
- Permission attached to that role: `AdministratorAccess`
- Trust policy: `sts:AssumeRoleWithWebIdentity` for the GitHub OIDC provider (see [Observations](#15-observations-from-the-code))

---

## 8. Configuration & Environment Variables

From `backend/config.py` and `.env.example`:

| Variable | Default in `config.py` | Notes |
|---|---|---|
| `FLASK_ENV` | `development` | Selects `development` / `testing` / `production` config |
| `SECRET_KEY` | built-in insecure dev key | Override in every real deployment |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/assignment_portal_db` | `postgres://` prefix is rewritten to `postgresql://` |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `REDIS_DEFAULT_TIMEOUT` | `300` | seconds |
| `PERMANENT_SESSION_LIFETIME` | `86400` | seconds |
| `PORT` | `5000` | Used only by `run.py` when started directly |

`.env.example` also lists `FLASK_APP`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `GEMINI_API_KEY`, and `APP_URL`.

Config classes: `DevelopmentConfig` (DEBUG on), `TestingConfig` (SQLite in-memory by default, CSRF off, Redis DB 1), `ProductionConfig` (DEBUG off, secure session cookie, strict CSRF SSL).

---

## 9. Database, Migrations & Seed Data

- Alembic config: `alembic.ini` → `script_location = database/migrations`.
- One migration: `d69f3b0037d6_initial_schema.py`.
- `seed.py` calls `db.create_all()`, exits early if `admin@gmail.com` already exists, and otherwise creates:
  - 1 admin: `admin@gmail.com` / `Admin@123`
  - 5 students (`alex@portal.edu`, `beatrice@portal.edu`, `charles@portal.edu`, `david@portal.edu`, `elena@portal.edu`) with password `Student@12345`
  - sample assignments, groups, submissions and audit entries

> These are demo credentials hard-coded in `seed.py`; the seed runs on every container start (it skips if the admin already exists).

---

## 10. Caching (Redis)

`CacheService` (`services/cache_service.py`), key prefix `portal:`, default TTL 300 s.

| Cached item | Key | TTL |
|---|---|---|
| Admin dashboard | `dashboard:admin:global` | 180 s |
| Student dashboard | `dashboard:student:<user_id>` | 120 s |
| Admin statistics | `statistics:admin` | 300 s |
| Assignment detail | `assignment:<id>` | 300 s |

**Invalidation:** assignment changes call `invalidate_all_assignment_caches` (assignment detail/listing, dashboards, statistics); submission and review actions also call `invalidate_submission_caches`.

**Fallback:** if Redis is unreachable at startup (2 s timeouts), `extensions.py` logs a warning and switches to an in-memory `MockRedisClient`, so the app still starts.

---

## 11. Monitoring Endpoints

| Endpoint | Source |
|---|---|
| `GET /health` | `routes/main.py` → `{"status": "healthy", "service": "Assignment Portal v2"}` |
| `/metrics` | `PrometheusMetrics(app)` in `create_app`, with info metric `assignment_portal` (version `1.0.0`) |

The Prometheus scraping and alert rules are defined in the CD repository.

---

## 12. Tests

`tests/` (pytest + pytest-flask) — 12 test functions across:

| File | Tests |
|---|---|
| `test_auth.py` | 4 |
| `test_assignments.py` | 3 |
| `test_groups_and_locking.py` | 3 |
| `test_submissions.py` | 2 |

Run locally from the repository root with your Python environment set up:

```bash
pip install -r backend/requirements.txt
pytest tests/
```

The CI workflow does **not** include a test step.

---

## 13. How CI Hands Over to CD

```text
git push (branch K8s-deployment)
        │
        ▼
GitHub Actions ──OIDC──► AWS (role from AWS_ROLE_ARN_SNQ)
        │
        ├─► build + push  assignment-portal-backend:<sha>   ─┐
        └─► build + push  assignment-portal-frontend:<sha>  ─┤► Amazon ECR (us-east-1)
        │
        ▼
clone YashwanthGowdaM/assignment-portal-k8s (main) using K8S_REPO_PAT
        │
        ▼
sed → manifest_files/backend/deployment.yaml   (image tag = <sha>)
sed → manifest_files/frontend/deployment.yaml  (image tag = <sha>)
        │
        ▼
commit "Update images to <sha>"  →  push to main
        │
        ▼
ArgoCD (in the CD repo's cluster) detects the commit and syncs
```

CI never talks to the Kubernetes cluster directly — its only output is the Git commit in the manifest repository.

---

## 14. Other Files in This Repository

| Path | Content |
|---|---|
| `.essential/Setup_guide.txt` | Manual ECS setup steps (cluster, task definition with `assignment-redis` and `backend` containers, service, ALB) |
| `.essential/docker-install.sh` | Installs Docker + Compose plugin on Ubuntu |
| `docs/README.md` | Pre-existing documentation: app overview, structure, API table, and an **AWS ECS Fargate + ALB** deployment description |
| `media/` | Screenshots (`login-page`, `student-dashboard`, `admin-dashboard`) and `project-design.png` |

---

## 15. Observations From the Code

Facts noticed while reading the repository (listed so they can be reviewed; no change has been made):

1. **Two deployment descriptions coexist.** `docs/README.md` and `.essential/` describe an ECS Fargate/ALB setup; the active workflow in `.github/workflows/` targets the Kubernetes manifest repo.
2. **Trust-policy branch mismatch.** The documented trust policy's `sub` condition references branch `AWS-OCID`, while the workflow triggers on `K8s-deployment`. The live IAM configuration was not available to verify.
3. **Account ID is hard-coded** (`003344631245`) in the two `sed` commands of the workflow.
4. **No automated tests in CI** (see §12).
5. **React/Vite sources are not part of any image.** Neither Dockerfile references `src/`, `package.json`, or a Vite build; the running UI is the Jinja2 templates + static assets.
6. **`FLASK_ENV` default is `development`**, and `DATABASE_URL`/`SECRET_KEY` have insecure defaults in `config.py`.
7. **`.dockerignore` excludes `tests/`, `README.md`, `.env`, and `.git`.**
8. The `paths` filter lists `migrations/**` and `requirements.txt` at the repository root; the actual files live at `database/migrations/` and `backend/requirements.txt` (the latter is covered by `backend/**`).
