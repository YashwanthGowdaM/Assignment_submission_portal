# 🎓 Assignment Submission Portal

**A full-stack, containerized platform for managing group assignments, submissions, and academic review workflows.**

Built with **Flask**, **PostgreSQL**, **Redis**, **Docker**, and a **React + TypeScript** front-end layer.

[![Flask](https://img.shields.io/badge/Backend-Flask%203.0-000000?logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Cache-Redis-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![License](https://img.shields.io/badge/License-Educational-lightgrey)]()

🌐 **Live Demo:** http://129.159.237.133/

</div>

---
## 📖 Table of Contents

- [Overview](#-overview)
- [Live Preview](#-live-preview)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure — File-by-File Breakdown](#-project-structure--file-by-file-breakdown)
- [Data Model](#-data-model)
- [API Surface](#-api-surface)
- [Prerequisites](#-prerequisites)
- [Getting Started — Step by Step](#-getting-started--step-by-step)
- [Environment Variables](#-environment-variables)
- [Database Seeding & Demo Accounts](#-database-seeding--demo-accounts)
- [Redis Caching Strategy](#-redis-caching-strategy)
- [Running Tests](#-running-tests)
- [Deployment on a Cloud VM (Production)](#-deployment-on-a-cloud-vm-production)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Credits](#-credits)

---

## 🧭 Overview

The **Assignment Submission Portal** is an enterprise-style academic workflow tool that lets an **Administrator** (instructor) create assignments, define group sizes, monitor student enrollment, and review submitted work — while **Students** browse open assignments, form or join teams, submit their GitHub repository and documentation links, and track feedback in real time.

The system was designed to demonstrate **production-grade infrastructure practices** on a relatively simple domain problem, including:

- A clean **service-layer architecture** (routes → services → models) instead of fat controllers.
- **Role-based access control** (Admin vs. Student) enforced through decorators.
- **Redis-backed caching** for expensive dashboard/statistics queries, with automatic invalidation hooks.
- A **fully containerized** deployment story — Nginx reverse proxy, Flask/Gunicorn API, Redis cache, PostgreSQL (Supabase-hosted) — all wired together over a private Docker network.
- **Audit logging** for every administrative and group-lifecycle action, for traceability.

---

## 🖥️ Live Preview

<table align="center">
<tr>
<th>Sign-In</th>
<th>Student Dashboard</th>
<th>Admin Dashboard</th>
</tr>

<tr>
<td align="center">
<img src="../media/login-page.png" width="300">
</td>

<td align="center">
<img src="../media/student-dashboard.png" width="300">
</td>

<td align="center">
<img src="../media/admin-dashboard.png" width="300">
</td>
</tr>
</table>

> 🔗 Try it live: **[http://129.159.237.133/](http://129.159.237.133/)**

**What each screen shows:**

- **Sign-In (`Login Page.png`)** — The public entry point. Students self-register with an institutional email; both roles authenticate through the same form, and Flask-Login redirects them to the correct dashboard based on `role`.
- **Student Dashboard (`student_landing_pages.png`)** — A student's active teams, open assignments they can still join, submission history, and approved-project count — each card backed by a Redis-cached query.
- **Admin Dashboard (`admin_landing_page.png`)** — Cohort-wide KPIs (total assignments, pending reviews, active groups, registered students), a submissions-pending-review queue, recent assignments, and a live **audit activity trail**.

---

## 🏗️ System Architecture

The diagram below (`media/project_Design.png`) is the single source of truth for how every layer of this system fits together — request flow, authentication flow, database schema, Redis caching, and deployment workflow are all mapped out visually.

<p align="center">
  <img src="../media/project-design.png"
       alt="Assignment Submission Portal Architecture"
       width="100%">
</p>

**Request lifecycle, in short:**

1. A browser (student or admin) hits the **Nginx** reverse proxy on port `80`.
2. Nginx serves static assets directly (`/static/*`) and proxies everything else to the **Flask** backend container (`assignment-backend:5000`) over the internal Docker network `assignment-net`.
3. Flask checks the current user's session (Flask-Login) and role (via `@admin_required` / `@student_required` decorators).
4. For read-heavy endpoints (dashboards, statistics), Flask first checks **Redis**. On a cache miss, it queries **PostgreSQL**, serializes the result, and writes it back to Redis with a TTL.
5. Writes (submissions, group joins, assignment edits) go straight to PostgreSQL and then **invalidate** the relevant Redis cache keys so the next read is fresh.
6. Every meaningful mutation (submission approved/rejected, assignment created, group locked) is written to the `audit_logs` table for traceability.

---

## 🧰 Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Backend Framework** | Flask 3.0 (Python 3.12) | Application-factory pattern (`create_app`) |
| **ORM / Migrations** | SQLAlchemy 2.0 + Flask-Migrate (Alembic) | Declarative models, versioned schema migrations |
| **Database** | PostgreSQL (Supabase-hosted, pooled connection) | Enforced via `CHECK` / `UNIQUE` constraints at the DB layer |
| **Cache** | Redis 7 | Dashboard stats, assignment detail, admin statistics |
| **Auth** | Flask-Login + Werkzeug password hashing | Session-based auth, CSRF protection via Flask-WTF |
| **Forms & Validation** | Flask-WTF / WTForms | Server-side validation for every form |
| **Frontend (server-rendered)** | Jinja2 templates + static CSS/JS | `frontend/templates`, `frontend/static` |
| **Frontend (SPA variant)** | React 19 + TypeScript + Vite | `src/` — component-driven admin/analytics views |
| **Reverse Proxy / Static host** | Nginx (Alpine) | Serves static files, proxies API traffic |
| **WSGI Server** | Gunicorn (4 workers, 2 threads) | Production application server |
| **Containerization** | Docker + Docker network | One image per service, no docker-compose dependency required |
| **Testing** | Pytest + pytest-flask | Auth, assignments, groups/locking, submissions |

---

## 🗂️ Project Structure — File-by-File Breakdown

```text
Assignment_submission_portal-main/
├── backend/                          # Flask API service
│   ├── app/
│   │   ├── __init__.py               # create_app() factory: registers extensions, blueprints, filters
│   │   ├── extensions.py             # db, migrate, login_manager, csrf, Redis client initialization
│   │   ├── forms/                    # WTForms definitions (server-side validated forms)
│   │   │   ├── auth_forms.py         # Login, Register, ForgotPassword, ResetPassword, Profile forms
│   │   │   ├── assignment_forms.py   # Create/Edit assignment forms (title, type, group size, due date)
│   │   │   └── submission_forms.py   # Repo URL / Docs URL / remarks submission form
│   │   ├── models/                   # SQLAlchemy ORM models (see Data Model section below)
│   │   │   ├── user.py               # User model — admin & student roles, password hashing
│   │   │   ├── assignment.py         # Assignment model — type, capacity, status lifecycle
│   │   │   ├── group.py              # Group + GroupMember — team formation & capacity logic
│   │   │   ├── submission.py         # Submission model — review workflow (pending/approved/rejected)
│   │   │   └── audit_log.py          # AuditLog — immutable trail of admin/system actions
│   │   ├── routes/                   # Flask Blueprints (HTTP layer only — no business logic)
│   │   │   ├── main.py               # `/` landing redirect, `/health` health-check endpoint
│   │   │   ├── auth.py                # login, register, logout, forgot/reset password, profile
│   │   │   ├── admin.py               # dashboard, assignments CRUD, students, groups, submissions review, statistics
│   │   │   └── student.py             # dashboard, browse assignments, join/leave group, submit work, my submissions
│   │   ├── services/                  # Business logic layer — keeps routes thin
│   │   │   ├── auth_service.py        # Registration, password-reset token generation/verification
│   │   │   ├── assignment_service.py  # Assignment lifecycle (open/full/closed transitions)
│   │   │   ├── submission_service.py  # Submission creation & review logic
│   │   │   ├── stats_service.py       # Aggregation queries for dashboards & analytics
│   │   │   └── cache_service.py       # Redis get/set/delete helpers + cache-key namespacing
│   │   └── utilities/
│   │       ├── decorators.py          # @admin_required / @student_required route guards
│   │       ├── errors.py              # Centralized error handlers (400/403/404/500)
│   │       └── helpers.py             # Jinja filters (datetime formatting, status badges), safe-URL check
│   ├── config.py                      # Development / Testing / Production config classes
│   ├── run.py                         # WSGI entry point used by Gunicorn (`run:app`)
│   ├── requirements.txt               # Pinned Python dependencies
│   └── Dockerfile                     # Backend container image (Python 3.12-slim + Gunicorn)
│
├── frontend/                           # Server-rendered UI + static assets
│   ├── templates/
│   │   ├── base.html                   # Shared layout, nav bar, flash messages
│   │   ├── auth/                       # login.html, register.html, forgot/reset password, profile.html
│   │   ├── admin/                      # dashboard, assignment CRUD, students, groups, submissions, statistics
│   │   ├── student/                    # dashboard, assignments list/detail, submissions list/submit
│   │   └── errors/                     # 400.html, 403.html, 404.html, 500.html
│   ├── static/                         # CSS / JS / images served directly by Nginx
│   ├── nginx.conf                      # Reverse-proxy rules: /static/* served locally, everything else → backend
│   └── Dockerfile                      # Frontend container image (Nginx-Alpine)
│
├── src/                                 # React + TypeScript SPA variant (analytics-heavy admin views)
│   ├── App.tsx                          # Root component & view router
│   ├── components/                      # DashboardView, AssignmentsView, GroupsView, SubmissionsView,
│   │                                     #   AnalyticsView, Header, Sidebar, modals, etc.
│   ├── data.ts / types.ts               # Mock data & shared TypeScript interfaces
│   └── main.tsx / index.css             # Vite entry point & global styles
│
├── database/
│   └── migrations/                      # Alembic migration environment (env.py, versions/, script.py.mako)
│
├── tests/                               # Pytest suite
│   ├── conftest.py                      # Test app factory, fixtures (client, sample users, sample data)
│   ├── test_auth.py                     # Registration, login, duplicate-email rejection
│   ├── test_assignments.py              # Assignment CRUD & status transitions
│   ├── test_groups_and_locking.py       # Group capacity, locking, and concurrency edge cases
│   └── test_submissions.py              # Submission creation & admin review flow
│
├── docs/
│   └── README.md                        # Original infra quick-reference (kept for history)
│
├── media/                                # Screenshots & architecture diagram used in this README
│   ├── project_Design.png
│   ├── Login Page.png
│   ├── admin_landing_page.png
│   └── student_landing_pages.png
│
├── seed.py                               # Populates demo admin/students/assignments/groups/submissions
├── alembic.ini                           # Alembic configuration (points at database/migrations)
├── docker-install.sh                     # One-shot script: installs Docker + Docker Compose on Ubuntu
├── .env.example                          # Template for all required environment variables
├── package.json / vite.config.ts / tsconfig.json   # React SPA build tooling
└── metadata.json                         # App metadata (name, description, capabilities)
```

### Backend layer responsibilities, in plain English

| Layer | File(s) | Responsibility |
|---|---|---|
| **Routes** | `routes/*.py` | Parse the HTTP request, call a service, render a template or redirect. No SQL here. |
| **Services** | `services/*.py` | All business rules: "can this student join this group?", "should this assignment flip to FULL?", "what goes in the cache?" |
| **Models** | `models/*.py` | Table definitions, relationships, DB-level constraints, and small computed properties (`is_open`, `has_space`, `to_dict()`). |
| **Forms** | `forms/*.py` | Input validation (required fields, email format, password confirmation) before a request ever reaches a service. |
| **Utilities** | `utilities/*.py` | Cross-cutting concerns: access control decorators, error pages, template filters. |

---

## 🧩 Data Model

| Table | Purpose | Key Fields |
|---|---|---|
| **users** | Admins & students | `email`, `password_hash`, `role`, `student_id`, `bio` |
| **assignments** | Assignment definitions | `assignment_type` (INDIVIDUAL/GROUP), `max_group_size`, `max_groups`, `status` (OPEN/FULL/CLOSED), `due_date` |
| **groups** | Teams formed per assignment | `group_number`, `is_full`, `status` (FORMING/FULL/SUBMITTED/APPROVED/REJECTED) |
| **group_members** | Student ↔ Group mapping | Unique constraint: **one student, one group, per assignment** |
| **submissions** | Deliverables per group | `repo_url`, `docs_url`, `remarks`, `status` (PENDING/APPROVED/REJECTED), `feedback` |
| **audit_logs** | Immutable action trail | `action`, `entity_type`, `entity_id`, `details`, `ip_address` |

Key integrity rules enforced **at the database level** (not just in application code):

- `assignments.max_group_size` must be between 1 and 5 (`ck_assignment_group_size`).
- `assignments.assignment_type` must be `INDIVIDUAL` or `GROUP`.
- A student cannot belong to two groups on the same assignment (`uq_student_assignment_membership`).
- A group's `(assignment_id, group_number)` pair must be unique.

---

## 🔌 API Surface

| Area | Method & Path | Description |
|---|---|---|
| **Health** | `GET /health` | Container/orchestrator health-check |
| **Auth** | `POST /auth/login` · `POST /auth/register` · `GET /auth/logout` | Session-based authentication |
| **Auth** | `POST /auth/forgot-password` · `POST /auth/reset-password/<token>` | Token-based password recovery |
| **Auth** | `GET/POST /auth/profile` | View/update profile, change password |
| **Admin** | `GET /admin/dashboard` · `GET /admin/statistics` | Cached KPI dashboards |
| **Admin** | `GET/POST /admin/assignments`, `/create`, `/<id>/edit`, `/<id>/delete` | Assignment CRUD |
| **Admin** | `POST /admin/assignments/<id>/close`, `/reopen` | Manual status override |
| **Admin** | `GET /admin/students` · `GET /admin/groups` | Roster & team views |
| **Admin** | `GET /admin/submissions` · `GET/POST /admin/submissions/<id>/review` | Review queue & approve/reject |
| **Student** | `GET /student/dashboard` · `GET /student/assignments` · `GET /student/assignments/<id>` | Browse & inspect assignments |
| **Student** | `POST /student/assignments/<id>/join`, `/leave` | Team formation |
| **Student** | `GET/POST /student/assignments/<id>/submit` | Submit repo/docs links |
| **Student** | `GET /student/submissions` | Submission history & feedback |

---

## ✅ Prerequisites

Before you begin, make sure you have:

- **Ubuntu 22.04 / 24.04** (or any Linux distro with `apt`) — for the provided install script. macOS/Windows users can install Docker Desktop manually instead.
- **Git**
- **A Supabase account** (free tier is enough) — used as the managed PostgreSQL database.
- An open internet connection to pull base images (`python:3.12-slim`, `nginx:1.27-alpine`, `redis:7-alpine`).

---

## 🚀 Getting Started — Step by Step

### Step 1 — Clone the repository
Clone the repository in target ec2 instance [Recommended: atleast ### t2.medium ]

```bash
git clone https://github.com/YashwanthGowdaM/Assignment_submission_portal.git
cd Assignment_submission_portal
```

### Step 2 — Install Docker & Docker Compose

The repo ships a helper script that detects whether Docker is already installed and, if not, installs Docker Engine + the Compose plugin using Docker's official APT repository.

```bash
chmod +x docker-install.sh
./docker-install.sh
```

Re-login (or run `newgrp docker`) so your user picks up Docker group permissions, then verify:

```bash
docker --version
docker compose version
docker run hello-world
```

### Step 3 — Provision a PostgreSQL database on Supabase

1. Sign in at supabase.com and create a new project.
2. Wait for provisioning to finish.
3. Go to Project Settings → Database → Connection String and choose the Direct Connection (or Session Pooler) string.
4. Copy it and substitute your password:

   ```text
   postgresql://postgres.<project-id>:PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require
   ```

4. Replace `PASSWORD` with your actual database password. Keep this string handy for Step 6.

### Step 4 — Create an isolated Docker network

All three containers (frontend, backend, Redis) need to talk to each other by name — a user-defined bridge network makes that possible.

```bash
docker network create assignment-net
docker network ls
```

### Step 5 — Build the images

From the project root (where both `backend/` and `frontend/` live):

```bash
docker build -t assignment-backend:v1 -f backend/Dockerfile .
docker build -t assignment-frontend:v1 -f frontend/Dockerfile ./frontend
```

### Step 6 — Start Redis

```bash
docker run -d \
  --name assignment-redis \
  --network assignment-net \
  redis:7-alpine
```

### Step 7 — Start the backend

Use your own Supabase connection string from Step 3.

```bash
docker run -d \
  --name assignment-backend \
  --network assignment-net \
  -p 5000:5000 \
  -e SECRET_KEY="change-this-to-a-random-hex-string" \
  -e DATABASE_URL="postgresql://postgres.<project-id>:PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require" \
  -e REDIS_URL="redis://assignment-redis:6379/0" \
  assignment-backend:v1
```

### Step 8 — Run migrations & seed demo data (first run only)

```bash
docker exec -it assignment-backend flask db upgrade
docker exec -it assignment-backend python seed.py
```

### Step 9 — Start the frontend (Nginx)

```bash
docker run -d \
  --name assignment-frontend \
  --network assignment-net \
  -p 80:80 \
  assignment-frontend:v1
```

### Step 10 — Verify everything is running

```bash
docker images
docker ps 
docker network inspect assignment-net
docker exec -it assignment-redis redis-cli PING
docker logs assignment-backend
docker logs assignment-frontend
docker logs assignment-redis
```

Then open your browser to:

| Service | URL |
|---|---|
| Frontend (Nginx) | `http://localhost` or `http://<your-server-ip>` |
| Backend API (direct) | `http://localhost:5000` |
| Health check | `http://localhost:5000/health` |

> 🌐 A live instance of this exact setup is running at **[http://129.159.237.133/](http://129.159.237.133/)** — use it to see the finished product before you deploy your own.

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and fill in real values for local (non-Docker) development:

| Variable | Description | Example |
|---|---|---|
| `FLASK_APP` | Entry-point module | `run.py` |
| `FLASK_ENV` | `development` / `testing` / `production` | `development` |
| `SECRET_KEY` | Flask session/CSRF signing key | *(generate with `python -c "import secrets; print(secrets.token_hex(32))"`)* |
| `DATABASE_URL` | Full PostgreSQL connection string (Supabase) | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `REDIS_DEFAULT_TIMEOUT` | Default cache TTL in seconds | `300` |
| `SESSION_COOKIE_SECURE` | Set `True` behind HTTPS in production | `False` (local) |
| `PERMANENT_SESSION_LIFETIME` | Session lifetime in seconds | `86400` |

---

## 🌱 Database Seeding & Demo Accounts

Running `python seed.py` (or the Dockerized equivalent in Step 8) creates a ready-to-explore dataset: one administrator, five students, several assignments in different lifecycle states (open, full, closed), pre-formed groups, and sample submissions with review feedback — so the dashboards aren't empty on first login.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@portal.edu` | `Admin@12345` |
| Student | `alex@portal.edu` | `Student@12345` |
| Student | `beatrice@portal.edu` | `Student@12345` |

> ⚠️ These are **demo credentials only**. Change or remove them before exposing any deployment publicly.

---

## ⚡ Redis Caching Strategy

`CacheService` (in `backend/app/services/cache_service.py`) wraps every Redis interaction behind a namespaced key scheme (`portal:*`) so that cache and application data never collide, and so cache failures **never crash the app** — every method fails soft and falls back to a live database query.

| What's cached | Cache key pattern | TTL | Invalidated when |
|---|---|---|---|
| Admin dashboard stats | `portal:dashboard:admin:global` | 180s | Any assignment or submission changes |
| Student dashboard stats | `portal:dashboard:student:<user_id>` | 180s | That student joins/leaves a group or submits work |
| Assignment detail | `portal:assignment:<id>` | 300s | The assignment is edited, closed, or reopened |
| Admin-wide statistics | `portal:statistics:admin` | 300s | Any assignment or submission changes |

Inspect the cache live:

```bash
docker exec -it assignment-redis redis-cli
> MONITOR
> GET portal:dashboard:admin:global
```

---

## 🧪 Running Tests

The suite covers authentication, assignment CRUD, group capacity/locking edge cases, and the submission review flow, using an in-memory SQLite database (see `TestingConfig` in `config.py`) so tests never touch your real Supabase instance.

```bash
cd backend
pip install -r requirements.txt
pytest ../tests -v
```

---

## ☁️ Deployment on a Cloud VM (Production)

To reproduce the live demo (`http://129.159.237.133/`) on your own VM (Oracle Cloud, AWS EC2, DigitalOcean, etc.):

1. Provision an Ubuntu VM and open **port 80** (and 443 if you plan to add TLS) in its firewall/security group.
2. SSH in, then repeat **Steps 1–9** above on the VM itself.
3. Point a domain's DNS `A` record at the VM's public IP, or simply share the raw IP as shown in this project.
4. (Recommended) Put the Nginx container behind **Certbot / Let's Encrypt** or a managed load balancer for HTTPS.
5. Set `FLASK_ENV=production` and `SESSION_COOKIE_SECURE=True` on the backend container for hardened cookie settings.

---

## 🛠️ Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `502 Bad Gateway` from Nginx | Backend container not on `assignment-net`, or not yet ready | `docker network connect assignment-net assignment-backend`, check `docker logs assignment-backend` |
| Login always fails | Database not migrated/seeded yet | Run `flask db upgrade` then `python seed.py` |
| Dashboard stats look stale | Redis cache serving old data after a manual DB edit | `docker exec -it assignment-redis redis-cli FLUSHDB` |
| `sslmode` connection error to Supabase | Missing `?sslmode=require` on `DATABASE_URL` | Append it to the connection string |
| Containers can't resolve each other by name | Not attached to the same custom network | Confirm all three containers were started with `--network assignment-net` |

---

## 🗺️ Roadmap

- [ ] JWT-based API authentication for the React SPA variant
- [ ] Email delivery for password-reset tokens (currently shown in-app for local dev)
- [ ] File-upload submissions in addition to repo/docs links
- [ ] Docker Compose file for one-command local spin-up
- [ ] CI pipeline running the Pytest suite on every push

---

## 🙌 Credits

This project was built and refined with the help of the following AI tools:

| Tool | Contribution |
|---|---|
| **ChatGPT** | Prompt optimization & error handling strategy |
| **Google AI Studio** | Application coding |
| **Claude AI** | Report writing & error fixes |
| **Author** | https://github.com/YashwanthGowdaM |
---

<div align="center">

**"From Code to Classroom — Empowering Learning with Technology"**

🔗 **Live Demo:** [http://129.159.237.133/](http://129.159.237.133/)

</div>
