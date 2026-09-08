# Assignment Submission Portal

A full-stack Assignment Submission Portal built with **Flask**, **React**, **PostgreSQL (Supabase)**, **Redis**, and **Docker**. The application supports role-based authentication, assignment management, submissions, dashboard statistics, Redis caching, and containerized deployment.

---

## Features

- User Authentication (JWT)
- Role-Based Access Control (Admin & Student)
- Assignment Management
- Assignment Submission
- Dashboard & Statistics
- Redis Caching
- PostgreSQL (Supabase)
- Dockerized Deployment
- Production-ready Container Images

---

# Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask |
| Frontend | React + Vite |
| Database | PostgreSQL (Supabase) |
| Cache | Redis |
| Containerization | Docker |
| Authentication | JWT |

---

# Project Structure

```
Assignment_submission_portal/
├── backend/
│   ├── app/
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── nginx.conf
│
├── database/
├── docs/
├── tests/
├── src/
├── seed.py
├── alembic.ini
├── package.json
├── metadata.json
├── vite.config.ts
├── tsconfig.json
└── docker-install.sh
```

# Prerequisites

- Ubuntu 22.04 / 24.04
- Git
- Internet connection
- Docker (installed using the provided script)

---

# Step 1 - Clone Repository

```bash
git clone https://github.com/YashwanthGowdaM/Assignment_submission_portal.git

cd Assignment_submission_portal
```

---

# Step 2 - Install Docker

The repository includes a helper script to install Docker and Docker Compose.

Make the script executable.

```bash
chmod +x docker-install.sh
```

Run the installation.

```bash
./docker-install.sh
```

After installation, either log out and log back in, or run:

```bash
newgrp docker
```

Verify the installation.

```bash
docker --version
docker compose version
```

Test Docker.

```bash
docker run hello-world
```

---

# Step 3 - Create a Supabase Database

1. Sign in to https://supabase.com
2. Create a new project.
3. Wait for provisioning to complete.
4. Navigate to:

```
Project Settings
    ↓
Database
```

5. Under **Connection String**, choose **Direct Connection**.

6. Copy the PostgreSQL connection string.

Example:

```text
postgresql://postgres.<project-id>:PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require
```

Replace `PASSWORD` with your database password.

---

# Step 4 - Build Docker Images

```bash
docker network create assignment-net
```

---

# Step 5 - Start Redis

```bash
docker run -d \
  --name assignment-redis \
  --network assignment-net \
  redis:7-alpine
```

---

# Step 6 - Start Backend

Replace the database URL with your own Supabase connection string.

```bash
docker run -d \
  --name assignment-backend \
  --network assignment-net \
  -p 5000:5000 \
  -e DATABASE_URL="postgresql://postgres.<project-id>:PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require" \
  -e REDIS_URL="redis://assignment-redis:6379/0" \
  assignment-backend:v1
```

---

# Step 7 - Start Frontend

```bash
docker run -d \
  --name assignment-frontend \
  --network assignment-net \
  -p 80:80 \
  assignment-frontend:v1
```

---

# Step 8 - Verify Containers

Backend

```bash
docker logs assignment-backend
```

Frontend

```bash
docker logs assignment-frontend
```

Redis

```bash
docker logs assignment-redis
```

---

# Step 9 - Monitor Redis Cache

Open the Redis CLI

```bash
docker exec -it assignment-redis redis-cli
```

Monitor all Redis operations

```redis
MONITOR
```

Example cached key

```redis
GET portal:dashboard:admin:global
```

---

# Application URLs

| Service | URL |
|----------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:5000 |

---

# Redis Cache

The application automatically caches dashboard statistics.

Example Redis keys

```
portal:dashboard:admin:global

portal:dashboard:student:<user_id>

portal:statistics:admin
```

---

# Stop Containers

```bash
docker stop assignment-frontend assignment-backend assignment-redis
```

---

# Remove Containers

```bash
docker rm assignment-frontend assignment-backend assignment-redis
```

---

# Remove Network

```bash
docker network rm assignment-net
```

---

# License

This project is created for learning and demonstration purposes.
