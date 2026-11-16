# Architecture and design decisions

## Request flow
1. A student opens the page and submits synthetic issue details.
2. The API validates field types and lengths and creates a random complaint ID.
3. A distinct tracking secret is returned once, while only its hash is persisted.
4. The API stores a Submitted record and sends a complaint ID to the routing queue.
5. A worker reads the queue message and assigns the appropriate campus team.
6. The student fetches the timeline using ID + tracking secret.
7. An admin loads the dashboard and updates progress with a note.

## AWS components, subject to account checks
- Lambda Event Functions: Python HTTP handler and SQS message consumer. Standard on-demand execution, not provisioned concurrency.
- Lambda Function URL: same-origin HTML + API, no API Gateway service needed.
- DynamoDB: one Standard table with string partition key `id`, PROVISIONED read/write capacity. Default on-demand mode is not the free-capacity design.
- SQS: Standard queue + dead-letter queue, modest batch size, bounded retries and partial batch failure responses.
- IAM: least-privilege Lambda execution role scoped to the new table and queue. No root credentials or account keys in code.

## API
- GET /api/health
- POST /api/complaints
- GET /api/complaints/{id}, header X-Tracking-Token
- GET /api/complaints, admin Authorization: Bearer <token>
- PATCH /api/complaints/{id}, admin body {status, note}
- POST /api/complaints/{id}/route, admin retry

## Data
id, name, title, description, category, priority, status, assigned_to, created_at, updated_at, tracking_hash, history.
History is embedded for the small demo. A production system should use separate audit records and strong user authentication, pagination, atomic conditional updates, rate limits, retention rules and monitoring.

## Security
- No credentials embedded in JavaScript or committed to Git.
- HTML interpolation escapes untrusted complaint content.
- Tracking secrets are separate from predictable titles and names.
- Admin authorization is checked on every admin operation; empty token disables admin access.
- Do not use real personal/sensitive complaints for this demonstration.

## Reliability and prototype boundary
SQS may deliver a message more than once. The worker ignores records that have already left Submitted. This is sequential retry protection, not a complete exactly-once guarantee under concurrent writers. Prototype read-modify-write updates need conditional version checks before production use. If a queue send fails after persistence, the response includes a warning and the admin can requeue. Local mode uses a timer instead of a durable queue and therefore is not resilient to a process crash.
