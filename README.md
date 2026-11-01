# MediCare+ Hospital Management System — DevOps Lab

A full-stack healthcare web application (Flask + PostgreSQL) used for three DevOps experiments:

| # | Experiment | Pipeline |
|---|------------|----------|
| 1 | CI/CD pipeline deploying a Dockerized app to Kubernetes using Jenkins | `Jenkinsfile` |
| 2 | Automated blue-green deployment with Jenkins, Kubernetes and Docker | `Jenkinsfile.bluegreen` |
| 3 | DevSecOps implementation for a healthcare system | `Jenkinsfile.devsecops` |

## Application features
- Patient registration and login (scrypt password hashing, lockout after 5 failures, rate limiting)
- Doctor directory with search and department filters
- Appointment booking with double-booking protection, cancellation
- Doctor consultation: vitals, diagnosis, e-prescriptions
- Medical records encrypted at rest (Fernet / AES-128-CBC + HMAC)
- Billing: invoices and payments
- Admin dashboard: KPIs, revenue, doctor management, appointment list, security audit log
- REST API: `/api/health`, `/api/version`, `/api/doctors`
- CSRF protection, strict Content-Security-Policy and other security headers, role-based access control

## Architecture
GitHub → (webhook) → Jenkins → Docker build → local registry (`localhost:5000`) → k3s Kubernetes
(namespace `medicare`: PostgreSQL StatefulSet + web Deployment, NetworkPolicy, Pod Security "restricted").

| Service | Port |
|---------|------|
| Jenkins | 8080 |
| App (Exp 1, rolling) | 30080 |
| App live (Exp 2, blue-green) | 30090 |
| App preview (idle colour) | 30091 |

## Run locally
```bash
pip install -r requirements.txt pytest
pytest -q tests
python wsgi.py   # http://localhost:5000 (SQLite)
```
Secrets are generated in the cluster by `scripts/create-secrets.sh`; none are stored in Git.
