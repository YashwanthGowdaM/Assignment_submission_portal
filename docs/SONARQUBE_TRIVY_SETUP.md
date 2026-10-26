# SonarQube + Trivy Setup Guide (Demo)

Adds a **code scan (SonarQube)** and a **container image scan (Trivy)** to the existing
GitHub Actions pipeline. Demo mode: both scans only *report*. Nothing blocks a deploy.

> Note: the image scanner is called **Trivy** (not "Trivia").

## What you get

```
push to K8s-deployment
   |
   +--> Job 1: sonarqube        run tests -> send code to SonarQube server -> report in its web UI
   |
   +--> Job 2: build-and-deploy build both images -> Trivy scans them -> push to ECR -> update manifests (ArgoCD deploys)
```

| Tool | What it checks | Where you see results |
|---|---|---|
| SonarQube | Your source code: bugs, security hotspots, code smells, test coverage | SonarQube web UI (`http://<server>:9000`) |
| Trivy | Built Docker images: known CVEs in OS packages and Python libraries | GitHub run page: *Summary* tab + `trivy-reports` artifact |

---

## Part 1 - Set up the SonarQube server (one time, ~20 min)

SonarQube is a server you host. The GitHub runner sends results to it, so it must be reachable from the internet.

### 1.1 Launch an EC2 instance
Use a **separate instance** (do not share it with Splunk; both want a lot of memory).

| Setting | Value |
|---|---|
| AMI | Ubuntu 24.04 LTS |
| Instance type | `t3.medium` (4 GB RAM) minimum. Use `t3.large` if it feels slow |
| Storage | 30 GB gp3 |
| Elastic IP | Attach one, so the address does not change after a restart |
| Security group | Inbound **22** (SSH) from *your IP only*; inbound **9000** (see warning below) |

> **Port 9000 warning:** GitHub-hosted runners use a very large, changing IP range, so for a demo you must open 9000 to `0.0.0.0/0`.
> That is acceptable for a short-lived demo **only** with a strong admin password and no real data.
> Safer options later: put HTTPS in front (nginx + domain) or use a self-hosted GitHub runner inside your VPC.

### 1.2 Install Docker
SSH in, then use the script you already have in this repo (`.essential/docker-install.sh`):

```bash
bash docker-install.sh
newgrp docker        # or log out/in so the docker group applies
```

### 1.3 Kernel settings required by SonarQube
SonarQube embeds Elasticsearch, which needs these (otherwise the container keeps crashing):

```bash
sudo sysctl -w vm.max_map_count=524288
sudo sysctl -w fs.file-max=131072
printf "vm.max_map_count=524288\nfs.file-max=131072\n" | sudo tee /etc/sysctl.d/99-sonarqube.conf
```

### 1.4 Start SonarQube

```bash
mkdir ~/sonarqube && cd ~/sonarqube
# copy .essential/sonarqube/docker-compose.yml here, then:
echo "SONAR_DB_PASSWORD=$(openssl rand -hex 16)" > .env
docker compose up -d
docker compose logs -f sonarqube      # wait for: "SonarQube is operational"  (1-3 min)
```

### 1.5 First login
1. Open `http://<elastic-ip>:9000`
2. Login `admin` / `admin`, then it forces you to **set a new password**. Do it.

---

## Part 2 - Connect SonarQube to GitHub

### 2.1 Create the project
1. SonarQube UI -> **Create a local project** (or *Create project -> Manually*)
2. Project display name: `Assignment Submission Portal`
3. Project key: `assignment-portal` (must match `sonar-project.properties`)
4. Main branch: `K8s-deployment` (Community Build analyses only the main branch, so set this to the branch your pipeline runs on)
5. New code: **Use the global setting** (fine for a demo)
6. Analysis method: choose **With GitHub Actions** -> it shows you a token step; or generate manually below

### 2.2 Create a token
*My Account (top-right avatar) -> Security -> Generate Token*
- Name: `github-actions`, Type: **Project Analysis Token** (or User token), copy it now. It is shown only once.

### 2.3 Add GitHub secrets
Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**

| Secret | Value |
|---|---|
| `SONAR_TOKEN` | the token from 2.2 |
| `SONAR_HOST_URL` | `http://<elastic-ip>:9000` (no trailing slash) |

(`AWS_ROLE_ARN` and `K8S_REPO_PAT` already exist.)

---

## Part 2B - Trivy setup (nothing to install on a server)

Unlike SonarQube, Trivy needs **no server, no account, no token and no GitHub secret**.
The workflow downloads the pinned Trivy container on the GitHub runner, scans the freshly built image, and throws the container away.
So the Trivy "setup" is only the two steps already inside `.github/workflows/ocid_deployment.yml`:
**Trivy Scan - Backend Image** and **Trivy Scan - Frontend Image**.

### Try Trivy on your own machine first (optional, 5 min)
Requires Docker. Run from the repo root:

```bash
# 1. Build the backend image
docker build -f backend/Dockerfile -t assignment-portal-backend:local .

# 2. Scan it
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  public.ecr.aws/aquasecurity/trivy:0.74.0 image \
  --severity HIGH,CRITICAL --ignore-unfixed \
  assignment-portal-backend:local
```

The first run downloads the vulnerability database (about a minute), then prints a table of findings.
Do the same for the frontend: `docker build -f frontend/Dockerfile -t assignment-portal-frontend:local ./frontend`, then repeat step 2 with that image name.

### The settings used in the pipeline

| Setting | Meaning |
|---|---|
| `--severity HIGH,CRITICAL` | Hide the low and medium noise |
| `--ignore-unfixed` | Only show problems that have a fix available |
| `--exit-code 0` | Report only; never fail the build (change to `1` to make it strict) |
| `--scanners vuln` | Check for known CVEs only (fastest) |
| `TRIVY_VERSION` (top of workflow) | The pinned Trivy version; update it occasionally |

---

## Part 3 - Add the files to your repo

Copy these (paths are relative to the repo root) and commit to the `K8s-deployment` branch:

| File | Purpose |
|---|---|
| `sonar-project.properties` | Tells SonarQube what to scan |
| `.github/workflows/ocid_deployment.yml` | Replaces the old workflow (adds Sonar + Trivy) |
| `.essential/sonarqube/docker-compose.yml` | SonarQube server compose file (reference, not used by CI) |
| `docs/SONARQUBE_TRIVY_SETUP.md` | This guide |

What changed in the workflow:
1. New **`sonarqube` job**: runs tests with coverage, then the SonarQube scan. `continue-on-error: true` keeps it non-blocking.
2. **Build order changed**: both images are now built first, **scanned**, and only then pushed to ECR. Before, images were pushed before any check could happen.
3. **Trivy steps** with `--exit-code 0` (report only) and `--severity HIGH,CRITICAL --ignore-unfixed` to keep the output readable.
4. Added `tests/**` and `sonar-project.properties` to the `paths:` trigger.

---

## Part 4 - Run it and read the results

1. Push the commit (or *Actions -> workflow -> Run workflow*).
2. **Actions** tab -> open the run. You should see both jobs.

### Reading Trivy results
- Open the run -> **Summary** page: the tables are shown at the bottom.
- Or download the `trivy-reports` artifact (`backend.txt`, `frontend.txt`).
- Columns: *Library*, *Vulnerability* (CVE id), *Severity*, *Installed Version*, *Fixed Version*.
- The usual fix is simple: **bump the version** in `backend/requirements.txt`, or use a newer base image tag in a Dockerfile (e.g. a newer `python:3.12-slim`).
- Expect findings in the old pinned libraries (Flask/Werkzeug/gunicorn in `requirements.txt`) and in OS packages of the base images. That is normal for a first scan.

### Reading SonarQube results
Open `http://<elastic-ip>:9000` -> project **Assignment Submission Portal**. Tabs:
- **Issues**: bugs, vulnerabilities, code smells, with file and line, and a "Why is this an issue?" explanation
- **Security Hotspots**: places to review manually (for example, the hardcoded default `SECRET_KEY` in `backend/config.py` is a typical one)
- **Measures / Overview**: coverage, duplication, ratings (A-E)
- **Quality Gate**: pass/fail summary. The default gate only judges *new* code. In this demo a failing gate does **not** fail the pipeline.

---

## Part 5 - Making it stricter later (optional)

| Goal | Change |
|---|---|
| Fail the build on critical image CVEs | In the Trivy steps set `--exit-code 1` and `--severity CRITICAL` |
| Fail the build when Sonar's quality gate fails | Add `-Dsonar.qualitygate.wait=true` as `args:` to the scan step, and remove `continue-on-error: true` from the `sonarqube` job |
| Stop deploying when the scan job fails | Same: remove `continue-on-error: true` (the deploy job already has `needs: sonarqube`) |
| Hide known/accepted CVEs | Create a `.trivyignore` file with one CVE id per line and add `--ignorefile .trivyignore` |
| Scan the Kubernetes manifests | Trivy can scan the other repo too: `trivy config manifest_files/` |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| SonarQube container restarts, log mentions `max virtual memory areas` | Redo step 1.3 |
| Scan step: `Failed to query server version` / timeout | Security group does not allow 9000, wrong `SONAR_HOST_URL`, or server is down (`docker compose ps`) |
| Scan step: `Not authorized` / 401 | `SONAR_TOKEN` is wrong or expired. Create a new one |
| Sonar shows 0% coverage | The test step failed or the coverage paths did not map. Check the test step log. Coverage is optional for the demo |
| Trivy: `TOOMANYREQUESTS` when downloading the database | Already mitigated by using the AWS public mirror in the workflow. Just re-run |
| Trivy report is empty | Good news: no HIGH/CRITICAL fixable vulnerabilities were found |
| Pipeline deploys even though the scan failed | That is intentional in demo mode (see Part 5 to change it) |

## Security notes
- Trivy runs from its **official container image, pinned to an exact version**, instead of the `aquasecurity/trivy-action` GitHub Action. In March 2026 that action's version tags were hijacked to steal CI secrets. The SonarQube action is from SonarSource and referenced by tag; for production, pin third-party actions to a full commit SHA.
- Keep `TRIVY_VERSION` current; check the Trivy releases page every so often.
- SonarQube Community Build is released monthly and has no long-term-support line; pull a new image occasionally: `docker compose pull && docker compose up -d`.
