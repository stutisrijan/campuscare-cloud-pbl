# CampusCare - cloud complaint management

A Cloud Technology Lab PBL prototype with a Python serverless backend, a dependency-free responsive web UI, private complaint tracking, an admin dashboard, and asynchronous routing.

## Verified status
- Local demo: automated API tests and browser workflow passed on 16 November 2026.
- AWS deployment: NOT YET VERIFIED. Cloud adapters are included, but do not claim that screenshots from the local demo show an AWS deployment.
- GitHub publication: tracked separately from this package.

## Run the local demo
Python 3.10+ is required. No package install or AWS access is needed for local mode.

```bash
# macOS / Linux (set a unique token of your own)
export ADMIN_TOKEN='replace-with-your-own-demo-token'
python3 backend/app.py
```

```powershell
# Windows PowerShell
$env:ADMIN_TOKEN='replace-with-your-own-demo-token'
python backend/app.py
```

Open http://127.0.0.1:8000. The process listens only on localhost. Use synthetic complaints, not real personal information. The admin token is an application secret, never an AWS key.

Tests:
```bash
python3 -m unittest discover -s tests -v
```

## Features
- Validate and submit campus complaints in Hostel, Classroom, Lab, Network or Other categories.
- Generate a random complaint ID and separate high-entropy private tracking secret.
- Store only a SHA-256 hash of the tracking secret; the browser does not put it in URLs or persistent storage.
- Route the complaint to a category-specific team in a background worker.
- Show timestamped history, priority, team and status.
- Token-protected admin workspace with status filtering and totals.
- Update status and notes; backwards status changes are rejected.
- Retry routing after a queue failure.

## Architecture
Local: Browser -> Python HTTP adapter -> SQLite -> delayed local worker.
AWS candidate: Browser -> Lambda Function URL -> Lambda API -> DynamoDB; API -> SQS -> Lambda worker -> DynamoDB.
The Lambda can return the UI as HTML, so no S3 static hosting or separate API Gateway is required. This is not a GitHub-to-AWS connection by itself. GitHub stores code; deployment needs a verified AWS environment and permissions.

See docs/ARCHITECTURE.md, docs/DEMO.md and docs/AWS-CHECKLIST.md.

## Scope and limits
This is a small teaching prototype, not a production campus helpdesk. No email/SMS, file attachments, student SSO, payments, or AI classification are included. Admin uses a single shared bearer token. Protect it as a secret. Dashboard scan is capped to 200 items. Local background processing is a simulation; only a deployed SQS configuration demonstrates a real cloud queue. Never expose a public unauthenticated endpoint at scale under a no-spend constraint. Quotas and alerts do not guarantee a zero bill.
