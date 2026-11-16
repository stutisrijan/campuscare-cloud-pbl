# 6-8 minute demonstration plan

0:00-0:45 Problem: campus complaints get lost across informal messages. CampusCare provides a tracking ID, routing and an audit timeline.
0:45-1:30 Architecture: explain browser, Python API, database, queue and worker. Explicitly say whether demonstrating LOCAL simulation or verified AWS deployment.
1:30-2:30 Submit a synthetic Network complaint. Save its ID and tracking secret. Explain why ID alone is not enough.
2:30-3:30 Track the complaint and show automatic routing to IT Helpdesk.
3:30-5:00 Open admin workspace, enter the configured demo admin token, filter complaints and change status to In Progress, then Resolved with a note.
5:00-6:00 Show the timeline and dashboard totals. Try an invalid request or missing admin token to demonstrate authorization.
6:00-7:00 Explain free-usage boundaries, retries, failure case and production limitations.
7:00-8:00 Show code/tests and summarize extensions: SSO, attachments, per-team permissions and pagination, only after validating their cost.

## Questions
Why SQS? Separates request acceptance from background routing and supports retries without making the student wait.
Why DynamoDB? Managed key-value persistence fits lookups by complaint ID; small provisioned capacity is a candidate for recurring free allowances.
Why Lambda? Event-triggered execution without running a VM continuously.
Why not S3/API Gateway? Not required by this design and their current free eligibility may depend on account age or credits.
Does a local test prove AWS works? No. The cloud queue, IAM, table and endpoint require separate deployment and end-to-end verification.
Is this production-ready? No. It is a teaching prototype with a shared admin token and deliberately limited dashboard.
