# AWS deployment record and checks - do not redeploy blindly

Updated user-approved scope: at most$100 existing AWS credits; no personal-money charges, paid-plan upgrade or EC2. Current Free Plan retained. This is not an enforced$100 monetary cap.

Verified16November2026 in account573705805509, ap-south-1: API health, real persistence/queue routing, secret-protected tracking and actual browser admin resolution passed. Stop schedule campuscare-pbl-stop24h is enabled for17November2026 18:00IST /12:30UTC. Tested stop sets API and worker reserved concurrency0; execution was restored for demonstration. Stop preserves data/resources. Do not rerun deploy_aws.py without reviewing expiry.

Configuration checks for any future deployment:
1. Verify intended account 22803011@mail.jiit.ac.in and actual account ID.
2. Inspect account plan, account expiry, service access and current Free Tier usage. Check whether quotas are shared with existing workloads.
3. Verify current regional pricing for every component, including logs, data transfer and encryption options. Do not equate no cash invoice with no credits consumed.
4. Prefer one region, no VPC/NAT, no EC2, no S3 hosting, no API Gateway, no paid KMS key, no provisioned Lambda concurrency or paid monitoring add-ons.
5. DynamoDB Standard, provisioned 1 read + 1 write capacity unit initially; no auto scaling beyond checked limits, backups/PITR/streams/global tables/indexes unless separately checked.
6. Lambda: small memory, short timeout, bounded concurrency, 512 MB temporary storage, no secrets in source. Concurrency throttles limit rate but are not a money cap.
7. SQS: standard queue, AWS-owned encryption if verified free, finite retention, bounded retries/DLQ, no provisioned pollers. Empty receives count towards usage. Disable event mapping after demonstration when no longer needed.
8. Choose endpoint exposure deliberately. A public Function URL can be invoked by outsiders. IAM-authenticated URL is safer but needs signed requests. A public lab demo is not a permanent zero-bill guarantee.
9. Set an application admin token through a secure process, not a committed literal.
10. Verify the final resource configuration against permission before creating it. Cost alerts are only alerts, not hard caps.

After deployment, test submission, real SQS processing, DynamoDB persistence, secret-protected tracking and admin updates. Capture actual AWS evidence. Verify cost/credit usage after metering catches up. Do not create resources beyond the approved scope. Current deployed table1RCU/1WCU has about$0.0213/day capacity list cost before allowances; tiny storage/log/queue costs may remain after execution stops.

Cleanup must target only the newly created project resources. Never delete unrelated resources or a table containing the user's data without permission.

Official references retrieved 16 November 2026:
https://aws.amazon.com/free/serverless/
https://aws.amazon.com/lambda/pricing/
https://aws.amazon.com/dynamodb/pricing/
https://aws.amazon.com/sqs/pricing/
https://aws.amazon.com/about-aws/whats-new/2022/04/aws-lambda-function-urls-built-in-https-endpoints/
