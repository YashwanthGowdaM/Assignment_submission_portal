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
.
├── alembic.ini                              # Alembic configuration file (tells Alembic where migrations are and how to run them)

├── backend
│   ├── Dockerfile                           # Builds the backend Docker image
│   ├── app
│   │   ├── __init__.py                      # Creates and initializes the Flask application
│   │   ├── extensions.py                    # Initializes shared extensions (SQLAlchemy, LoginManager, etc.)
│   │   ├── forms
│   │   │   ├── __init__.py                  # Makes forms a Python package
│   │   │   ├── assignment_forms.py          # Assignment create/edit form definitions
│   │   │   ├── auth_forms.py                # Login, registration and authentication forms
│   │   │   └── submission_forms.py          # Assignment submission forms
│   │   ├── models
│   │   │   ├── __init__.py                  # Imports and registers all database models
│   │   │   ├── assignment.py                # Assignment database table/model
│   │   │   ├── audit_log.py                 # Stores user activity logs
│   │   │   ├── group.py                     # Student group database model
│   │   │   ├── submission.py                # Assignment submission database model
│   │   │   └── user.py                      # User database model
│   │   ├── routes
│   │   │   ├── __init__.py                  # Registers all route blueprints
│   │   │   ├── admin.py                     # Admin URLs and request handling
│   │   │   ├── auth.py                      # Authentication URLs
│   │   │   ├── main.py                      # Common/Home page routes
│   │   │   └── student.py                   # Student-related routes
│   │   ├── services
│   │   │   ├── __init__.py                  # Makes services a Python package
│   │   │   ├── assignment_service.py        # Business logic for assignments
│   │   │   ├── auth_service.py              # Authentication business logic
│   │   │   ├── cache_service.py             # Cache management functions
│   │   │   ├── stats_service.py             # Dashboard and statistics calculations
│   │   │   └── submission_service.py        # Submission business logic
│   │   └── utilities
│   │       ├── __init__.py                  # Makes utilities a Python package
│   │       ├── decorators.py                # Custom decorators (login required, admin only, etc.)
│   │       ├── errors.py                    # Custom exception handling
│   │       └── helpers.py                   # Reusable helper functions
│   ├── config.py                            # Application configuration (DB, Secret Key, etc.)
│   ├── requirements.txt                     # Python package dependencies
│   └── run.py                               # Starts the Flask application

├── database
│   └── migrations
│       ├── README                           # Explains how migrations work
│       ├── alembic.ini                      # Alembic configuration specific to migration folder
│       ├── env.py                           # Loads database settings for Alembic
│       ├── script.py.mako                   # Template used when generating new migrations
│       └── versions
│           └── d69f3b0037d6_initial_schema.py   # Creates the initial database schema

├── docker-install.sh                        # Installs Docker on a Linux server
├── docs
│   └── README.md                            # Project documentation

├── entrypoint.sh                            # Container startup script

├── frontend
│   ├── Dockerfile                           # Builds frontend Docker image
│   ├── nginx.conf                           # Nginx configuration to serve frontend
│   ├── static
│   │   ├── css
│   │   │   └── custom.css                   # Custom styling
│   │   └── js
│   │       ├── dashboard.js                 # Dashboard JavaScript
│   │       └── main.js                      # Common frontend JavaScript
│   └── templates
│       ├── admin
│       │   ├── assignments
│       │   │   ├── create.html              # Create assignment page
│       │   │   ├── detail.html              # View assignment details
│       │   │   ├── edit.html                # Edit assignment page
│       │   │   └── list.html                # Assignment listing page
│       │   ├── dashboard.html               # Admin dashboard
│       │   ├── groups
│       │   │   └── list.html                # Group management page
│       │   ├── statistics.html              # Statistics page
│       │   ├── students
│       │   │   └── list.html                # Student management page
│       │   └── submissions
│       │       ├── list.html                # Submission listing
│       │       └── review.html              # Review submissions page
│       ├── auth
│       │   ├── forgot_password.html         # Forgot password page
│       │   ├── login.html                   # Login page
│       │   ├── profile.html                 # User profile page
│       │   ├── register.html                # Registration page
│       │   └── reset_password.html          # Reset password page
│       ├── base.html                        # Master HTML template used by all pages
│       ├── errors
│       │   ├── 400.html                     # Bad Request error page
│       │   ├── 403.html                     # Forbidden error page
│       │   ├── 404.html                     # Not Found error page
│       │   └── 500.html                     # Internal Server Error page
│       └── student
│           ├── assignments
│           │   ├── detail.html              # Assignment details for students
│           │   └── list.html                # Student assignment list
│           ├── dashboard.html               # Student dashboard
│           └── submissions
│               ├── list.html                # Student submission history
│               └── submit.html              # Submit assignment page

├── index.html                               # Main HTML entry point for Vite frontend

├── media
│   ├── admin-dashboard.png                  # Admin dashboard screenshot
│   ├── login-page.png                       # Login page screenshot
│   ├── project-design.png                   # Architecture/design image
│   └── student-dashboard.png                # Student dashboard screenshot

├── metadata.json                            # Project metadata/configuration

├── package.json                             # Node.js dependencies and project scripts

├── seed.py                                  # Populates database with sample/demo data

├── src
│   ├── App.tsx                              # Root React component
│   ├── components
│   │   ├── AnalyticsView.tsx                # Analytics page component
│   │   ├── AssignmentDetailModal.tsx        # Assignment details popup
│   │   ├── AssignmentsView.tsx              # Assignment management UI
│   │   ├── CreateAssignmentModal.tsx        # Create assignment popup
│   │   ├── DashboardView.tsx                # Dashboard component
│   │   ├── GroupsView.tsx                   # Group management component
│   │   ├── Header.tsx                       # Application header
│   │   ├── Sidebar.tsx                      # Navigation sidebar
│   │   └── SubmissionsView.tsx              # Submission management UI
│   ├── data.ts                              # Sample/mock data
│   ├── index.css                            # Global CSS styles
│   ├── main.tsx                             # React application entry point
│   └── types.ts                             # TypeScript type definitions

├── tests
│   ├── conftest.py                          # Common pytest fixtures and test setup
│   ├── test_assignments.py                  # Tests assignment functionality
│   ├── test_auth.py                         # Tests authentication
│   ├── test_groups_and_locking.py           # Tests groups and record locking
│   └── test_submissions.py                  # Tests submission functionality

├── tsconfig.json                            # TypeScript compiler configuration

└── vite.config.ts                           # Vite build and development server configuration
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

# AWS Deployment Architecture

This document describes the AWS infrastructure and CI/CD pipeline used to deploy the application, covering the complete flow from source code to production traffic: **GitHub Actions → OIDC → ECR → ECS Fargate → ALB**.

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [AWS Resources](#aws-resources)
- [External Services](#external-services)
- [Deployment Flow](#deployment-flow)

## Overview

The application is deployed as a containerized service on **Amazon ECS (Fargate)**, fronted by an **Application Load Balancer**. Continuous deployment is handled through **GitHub Actions**, which authenticates to AWS securely via **OIDC** (no long-lived access keys), builds and pushes Docker images to **ECR**, and triggers rolling deployments on ECS.

## Architecture Diagram

```
GitHub Repository
        │
        ▼
GitHub Actions
        │
        ▼
IAM OIDC Provider
        │
        ▼
AWS STS
        │
        ▼
IAM Role
        │
        ▼
Amazon ECR
        │
        ▼
Amazon ECS Cluster
        │
        ▼
ECS Service
        │
        ▼
ECS Task Definition
        │
   ┌────┴────┐
   │         │
Backend   Redis
   │
   ▼
Application Load Balancer
   │
   ▼
Target Group
   │
   ▼
End Users
```

## AWS Resources

| AWS Resource | Purpose | Major Configuration |
|---|---|---|
| **IAM** | Authentication and authorization | Created GitHub OIDC IAM role, attached ECS/ECR permissions, configured IAM policies and trust relationship |
| **IAM OIDC Identity Provider** | Allows GitHub Actions to authenticate without AWS access keys | Added `token.actions.githubusercontent.com` as the OIDC provider with audience `sts.amazonaws.com` |
| **AWS STS** | Provides temporary credentials | GitHub Actions assumes the IAM role via `AssumeRoleWithWebIdentity` |
| **Amazon ECR** | Stores Docker container images | Created private repository; pushes images tagged `latest` and by commit SHA |
| **Amazon ECS** | Container orchestration | Created ECS cluster, service, and task definitions; configured rolling deployments |
| **AWS Fargate** | Serverless compute for ECS | Used as the launch type to run containers without managing EC2 instances |
| **ECS Cluster** | Logical grouping of services | Created `assignment-portal-cluster` |
| **ECS Service** | Maintains desired running task count | Configured desired count, attached ALB target group, enabled rolling deployments |
| **ECS Task Definition** | Blueprint for running containers | Configured Backend and Redis containers, CPU/memory, port mappings, environment variables, health checks, CloudWatch logging |
| **Application Load Balancer (ALB)** | Distributes incoming HTTP traffic | Internet-facing ALB, listener on port 80, forwards to target group |
| **Target Group** | Routes requests to healthy ECS tasks | IP target type, port 5000, health check path `/health`, success code 200 |
| **Amazon VPC** | Isolated networking environment | Used existing VPC to host ECS tasks and ALB |
| **Subnets** | Network segments within the VPC | Public subnets used for ALB and Fargate networking |
| **Security Groups** | Virtual firewall | Configured ALB and ECS task security groups; allowed HTTP (80) and backend (5000) traffic |
| **Elastic Network Interface (ENI)** | Network interface for Fargate tasks | Automatically created per ECS task under `awsvpc` networking mode |
| **Internet Gateway** | Enables internet connectivity | Used by the VPC for ALB and ECS outbound access |
| **AWS Systems Manager Parameter Store** | Secure configuration storage | Stored `DATABASE_URL` and `REDIS_URL`, injected into ECS tasks as secrets |
| **Amazon CloudWatch Logs** | Centralized logging | Configured `awslogs` driver for ECS container application and deployment logs |
| **Amazon CloudWatch** | Monitoring and troubleshooting | Used to review ECS task logs, startup logs, application logs, and deployment events |

## External Services

| Service | Purpose |
|---|---|
| **GitHub** | Source code repository |
| **GitHub Actions** | CI/CD pipeline automation |
| **GitHub OIDC** | Secure, keyless authentication with AWS |
| **Docker** | Containerization of the backend application |
| **Supabase PostgreSQL** | External PostgreSQL database |
| **Redis** | In-memory cache, running as an ECS container |

## Deployment Flow

1. Code is pushed to the **GitHub repository**, triggering a **GitHub Actions** workflow.
2. GitHub Actions authenticates to AWS using the **OIDC provider**, exchanging a GitHub-issued token for temporary credentials via **AWS STS** and an **IAM role** — no static AWS access keys are stored in GitHub.
3. The workflow builds a Docker image and pushes it to **Amazon ECR**, tagged with both `latest` and the commit SHA.
4. A new **ECS task definition** revision is registered, referencing the updated image, along with the Backend and Redis containers, environment variables, and secrets pulled from **Parameter Store**.
5. The **ECS service** performs a rolling deployment onto the **assignment-portal-cluster**, running tasks on **Fargate**.
6. The **Application Load Balancer** routes incoming traffic on port 80 to the **target group**, which performs health checks against `/health` on port 5000 and forwards traffic only to healthy tasks.
7. Application and deployment logs are streamed to **CloudWatch Logs** for monitoring and troubleshooting.
