# CampusCare - cloud complaint management

A Cloud Technology Lab PBL prototype with a Python serverless backend, a dependency-free responsive web UI, private complaint tracking, an admin dashboard, and asynchronous routing.

## Verified status
- Local demo: automated API tests and browser workflow passed on 16 November 2026.
- AWS deployment verified16November2026: real Lambda API, DynamoDB persistence, SQS worker, private tracking and browser admin status update passed.
- Live demo: https://sub4i36modmgfnc4eajyz5qony0xkjbk.lambda-url.ap-south-1.on.aws/
- Scheduled stop:17November2026 at18:00IST (12:30UTC). Execution stops; data/resources are not deleted. Use sample details only.
- Repository and current downloadable source package use a flat layout for simple cloning and running.

## Run the local demo
Python 3.10+ is required. No package install or AWS access is needed for local mode.

```bash
# macOS / Linux (set a unique token of your own)
export ADMIN_TOKEN='replace-with-your-own-demo-token'
python3 app.py
```

```powershell
# Windows PowerShell
$env:ADMIN_TOKEN='replace-with-your-own-demo-token'
python app.py
```

Open http://127.0.0.1:8000. The process listens only on localhost. Use synthetic complaints, not real personal information. The admin token is an application secret, never an AWS key.

Tests:
```bash
python3 -m unittest -v test_app
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
Verified AWS deployment: Browser -> Lambda Function URL -> Lambda API -> DynamoDB; API -> SQS -> Lambda worker -> DynamoDB.
Lambda returns the UI as HTML; no S3 static hosting or separate API Gateway is required. GitHub stores source. Deployment was executed in the selected AWS account, not through an automatic GitHub deployment connection.

Spending scope: at most$100 existing AWS credits, no personal-money charges and no paid-plan upgrade. Current Free Plan remains unchanged. Timed stop/concurrency limits are not a hard dollar cap. Ordinary classroom traffic is estimated far below$1; actual usage is metered later. Residual DynamoDB capacity at Mumbai list rates is about$0.0213/day before free allowances, plus tiny storage/log/queue charges. Do not rerun deploy_aws.py blindly: its default resets expiry to24hours from execution.

See ARCHITECTURE.md, DEMO.md and AWS-CHECKLIST.md.

## Scope and limits
This is a small teaching prototype, not a production campus helpdesk. No email/SMS, file attachments, student SSO, payments, or AI classification are included. Admin uses a single shared bearer token. Protect it as a secret. Dashboard scan is capped to 200 items. Local background processing is a simulation; only a deployed SQS configuration demonstrates a real cloud queue. The public submission endpoint is for this short classroom demo only; do not run a load test or expose it at scale. Quotas and alerts do not guarantee a zero bill.
